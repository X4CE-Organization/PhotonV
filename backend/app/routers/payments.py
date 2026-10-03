"""在线支付：下单、二维码、状态轮询与网关异步回调。"""
from __future__ import annotations

import io

import qrcode
import qrcode.image.svg
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, settings_store as site
from ..database import get_db
from ..payments import alipay, methods, notify_url, wechat
from ..security import require_user
from ..utils import audit, fail, now
from .orders import apply_order, order_payload

router = APIRouter(prefix="/api/payments", tags=["payments"])


@router.get("/methods")
def payment_methods():
    return {"items": methods()}


def _find_order(db: Session, order_id: int) -> models.Order:
    order = db.get(models.Order, order_id)
    if not order:
        raise fail(404, "订单不存在")
    return order


@router.post("/{order_id}/create")
def create_payment(
    order_id: int,
    payload: dict,
    request: Request,
    user: models.User = Depends(require_user),
    db: Session = Depends(get_db),
):
    order = _find_order(db, order_id)
    if order.user_id != user.id:
        raise fail(403, "没有权限操作该订单")
    if order.status != "pending":
        raise fail(400, "订单状态不允许支付")

    method = str(payload.get("method") or order.pay_method or "manual")
    order.pay_method = method
    amount_yuan = f"{order.amount_cents / 100:.2f}"

    if method == "manual":
        order.pay_payload = site.get_str("pay_manual_note", "")
        db.commit()
        return {
            "ok": True,
            "method": "manual",
            "status": order.status,
            "message": order.pay_payload,
            "order": order_payload(order, db),
        }

    if method == "alipay":
        if not alipay.configured():
            raise fail(400, "支付宝未配置或未启用，请在后台「支付渠道」里填写参数")
        try:
            if alipay.mode() == "qr":
                result = alipay.precreate(order.order_no, amount_yuan, order.title)
                if not result.get("ok"):
                    raise fail(400, f"支付宝下单失败：{result.get('error')}")
                order.pay_payload = result["qrCode"]
                db.commit()
                return {
                    "ok": True,
                    "method": "alipay",
                    "mode": "qr",
                    "qrCode": result["qrCode"],
                    "qrUrl": f"/api/payments/{order.id}/qr.svg",
                    "orderNo": order.order_no,
                }
            url = alipay.page_pay(order.order_no, amount_yuan, order.title)
            order.pay_payload = url
            db.commit()
            return {"ok": True, "method": "alipay", "mode": "page", "payUrl": url, "orderNo": order.order_no}
        except fail:
            raise
        except Exception as exc:  # noqa: BLE001
            raise fail(400, f"支付宝下单失败：{exc}") from exc

    if method == "wechat":
        if not wechat.configured():
            raise fail(400, "微信支付未配置或未启用，请在后台「支付渠道」里填写参数")
        result = wechat.native_order(order.order_no, order.amount_cents, order.title, notify_url("wechat"))
        if not result.get("ok"):
            raise fail(400, f"微信下单失败：{result.get('error')}")
        order.pay_payload = result["codeUrl"]
        db.commit()
        audit(db, request, user, "payment.create", "order", order.id, method)
        return {
            "ok": True,
            "method": "wechat",
            "mode": "native",
            "qrCode": result["codeUrl"],
            "qrUrl": f"/api/payments/{order.id}/qr.svg",
            "orderNo": order.order_no,
        }

    raise fail(400, "不支持的支付方式")


@router.get("/{order_id}/qr.svg")
def payment_qr(order_id: int, db: Session = Depends(get_db)):
    order = _find_order(db, order_id)
    if not order.pay_payload:
        raise fail(404, "该订单还没有支付二维码")
    image = qrcode.make(
        order.pay_payload,
        image_factory=qrcode.image.svg.SvgPathImage,
        box_size=10,
        border=2,
    )
    buffer = io.BytesIO()
    image.save(buffer)
    return Response(
        content=buffer.getvalue(),
        media_type="image/svg+xml",
        headers={"Cache-Control": "no-store"},
    )


@router.get("/{order_id}/status")
def payment_status(
    order_id: int,
    user: models.User = Depends(require_user),
    db: Session = Depends(get_db),
):
    order = _find_order(db, order_id)
    if order.user_id != user.id and not user.is_admin:
        raise fail(403, "没有权限查看该订单")
    if order.status == "pending" and order.pay_method in {"alipay", "wechat"}:
        try:
            if order.pay_method == "alipay" and alipay.configured():
                result = alipay.query(order.order_no)
                if result.get("state") in {"TRADE_SUCCESS", "TRADE_FINISHED"}:
                    order.trade_no = str(result.get("tradeNo") or "")
                    apply_order(db, order)
            elif order.pay_method == "wechat" and wechat.configured():
                result = wechat.query(order.order_no)
                if result.get("state") == "SUCCESS":
                    order.trade_no = str(result.get("tradeNo") or "")
                    apply_order(db, order)
        except Exception:  # noqa: BLE001 - 查询失败不影响返回
            pass
    return {"status": order.status, "payMethod": order.pay_method, "tradeNo": order.trade_no}


@router.post("/alipay/notify")
async def alipay_notify(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    params = {key: str(value) for key, value in form.items()}
    if not alipay.verify_notify(params):
        return Response("failure", media_type="text/plain")
    order = db.scalar(select(models.Order).where(models.Order.order_no == params.get("out_trade_no", "")))
    if not order:
        return Response("failure", media_type="text/plain")
    expected = f"{order.amount_cents / 100:.2f}"
    if params.get("total_amount") and params["total_amount"] != expected:
        return Response("failure", media_type="text/plain")
    if params.get("trade_status") in {"TRADE_SUCCESS", "TRADE_FINISHED"}:
        order.trade_no = params.get("trade_no", "")
        apply_order(db, order)
    return Response("success", media_type="text/plain")


@router.post("/wechat/notify")
async def wechat_notify(request: Request, db: Session = Depends(get_db)):
    body = await request.json()
    resource = body.get("resource") or {}
    try:
        detail = wechat.decrypt_resource(resource)
    except Exception:  # noqa: BLE001
        return {"code": "FAIL", "message": "解密失败"}
    out_trade_no = detail.get("out_trade_no", "")
    order = db.scalar(select(models.Order).where(models.Order.order_no == out_trade_no))
    if not order:
        return {"code": "FAIL", "message": "订单不存在"}
    # 二次校验：主动查单确认金额与状态，避免伪造回调
    try:
        check = wechat.query(out_trade_no)
        if not check.get("ok") or check.get("state") != "SUCCESS":
            return {"code": "FAIL", "message": "订单未支付"}
        if int(check.get("amount") or 0) != int(order.amount_cents):
            return {"code": "FAIL", "message": "金额不匹配"}
    except Exception:  # noqa: BLE001
        return {"code": "FAIL", "message": "查单失败"}
    order.trade_no = str(detail.get("transaction_id") or "")
    order.paid_at = order.paid_at or now()
    apply_order(db, order)
    return {"code": "SUCCESS", "message": "成功"}


@router.get("/alipay/return")
def alipay_return():
    from ..payments import return_url

    return RedirectResponse(return_url(), status_code=302)
