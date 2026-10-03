"""会员、硬币充值与充电（含管理端审核）。"""
from __future__ import annotations

import secrets
from datetime import timedelta

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import models, settings_store as site
from ..database import get_db
from ..security import current_user, require_admin, require_superadmin, require_user
from ..utils import audit, fail, iso, notify, now, pagination, user_brief

router = APIRouter(prefix="/api", tags=["orders"])


def order_payload(item: models.Order, db: Session) -> dict:
    target = db.get(models.User, item.target_user_id) if item.target_user_id else None
    return {
        "id": item.id,
        "orderNo": item.order_no,
        "type": item.type,
        "title": item.title,
        "amountCents": item.amount_cents,
        "coins": item.coins,
        "payMethod": item.pay_method,
        "status": item.status,
        "note": item.note,
        "createdAt": iso(item.created_at),
        "paidAt": iso(item.paid_at),
        "target": user_brief(target),
    }


def plan_payload(item: models.MembershipPlan) -> dict:
    return {
        "id": item.id,
        "name": item.name,
        "days": item.days,
        "priceCents": item.price_cents,
        "priceYuan": round(item.price_cents / 100, 2),
        "description": item.description,
        "badge": item.badge,
        "isActive": bool(item.is_active),
        "sort": item.sort,
    }


def apply_order(db: Session, order: models.Order) -> None:
    """订单支付成功后的权益发放。"""
    if order.status == "paid":
        return
    order.status = "paid"
    order.paid_at = now()
    buyer = db.get(models.User, order.user_id)
    if order.type == "membership" and order.plan_id:
        plan = db.get(models.MembershipPlan, order.plan_id)
        if buyer and plan:
            base = buyer.membership_expires if (buyer.membership_expires and buyer.membership_expires > now()) else now()
            buyer.membership_expires = base + timedelta(days=plan.days)
            buyer.membership_level = max(1, buyer.membership_level)
    elif order.type == "coins" and buyer:
        buyer.coins += order.coins
    elif order.type == "charge":
        target = db.get(models.User, order.target_user_id) if order.target_user_id else None
        if target:
            share = max(0, min(100, site.get_int("creator_share_percent", 70)))
            gained = int(order.coins * share / 100)
            target.coins += gained
            target.total_earned += gained
    db.commit()
    if buyer:
        notify(
            db, buyer.id, "system", "订单已支付",
            f"「{order.title}」已支付成功，订单号 {order.order_no}。",
            ref_type="order", ref_id=order.id, setting_key="notify_mail_order",
        )


@router.get("/plans")
def plans(db: Session = Depends(get_db)):
    rows = db.scalars(
        select(models.MembershipPlan)
        .where(models.MembershipPlan.is_active.is_(True))
        .order_by(models.MembershipPlan.sort.asc(), models.MembershipPlan.id.asc())
    ).all()
    return {
        "membershipEnabled": site.get_bool("membership_enabled", True),
        "rechargeEnabled": site.get_bool("recharge_enabled", True),
        "chargeEnabled": site.get_bool("charge_enabled", True),
        "coinsPerYuan": site.get_int("coins_per_yuan", 100),
        "chargeRatio": site.get_int("charge_ratio", 100),
        "badgeText": site.get_str("membership_badge_text", "大会员"),
        "note": site.get_str("membership_note", ""),
        "payManualNote": site.get_str("pay_manual_note", ""),
        "payMethods": site.get_json("pay_methods", []),
        "items": [plan_payload(item) for item in rows],
    }


@router.post("/orders")
def create_order(
    payload: dict,
    request: Request,
    user: models.User = Depends(require_user),
    db: Session = Depends(get_db),
):
    type_ = str(payload.get("type") or "membership")
    if type_ not in {"membership", "coins", "charge"}:
        raise fail(400, "订单类型不正确")
    pay_method = str(payload.get("pay_method") or "manual")
    order = models.Order(
        order_no=f"PV{now().strftime('%Y%m%d%H%M%S')}{secrets.randbelow(9000) + 1000}",
        user_id=user.id,
        type=type_,
        pay_method=pay_method,
    )

    if type_ == "membership":
        if not site.get_bool("membership_enabled", True):
            raise fail(403, "本站未开启会员")
        plan = db.get(models.MembershipPlan, int(payload.get("plan_id") or 0))
        if not plan or not plan.is_active:
            raise fail(404, "会员套餐不存在")
        order.plan_id = plan.id
        order.title = f"开通{plan.name}"
        order.amount_cents = plan.price_cents
    elif type_ == "coins":
        if not site.get_bool("recharge_enabled", True):
            raise fail(403, "本站未开启充值")
        amount_cents = int(payload.get("amount_cents") or 0)
        if amount_cents <= 0:
            raise fail(400, "请填写充值金额")
        order.amount_cents = amount_cents
        order.coins = int(amount_cents / 100 * site.get_int("coins_per_yuan", 100))
        order.title = f"充值 {order.coins} 硬币"
    else:
        if not site.get_bool("charge_enabled", True):
            raise fail(403, "本站未开启充电")
        target = None
        if payload.get("target_user_id"):
            target = db.get(models.User, int(payload["target_user_id"]))
        elif payload.get("username"):
            target = db.scalar(select(models.User).where(models.User.username == str(payload["username"])))
        if not target:
            raise fail(404, "充电对象不存在")
        if target.id == user.id:
            raise fail(400, "不能给自己充电")
        coins = int(payload.get("coins") or 0)
        if coins <= 0:
            raise fail(400, "请填写充电硬币数")
        if user.coins < coins:
            raise fail(400, "硬币不足")
        user.coins -= coins  # 硬币立刻扣除
        order.target_user_id = target.id
        order.coins = coins
        order.amount_cents = int(coins / max(1, site.get_int("charge_ratio", 100)) * 100)
        order.title = f"给 {target.display_name or target.username} 充电 {coins} 硬币"
        order.status = "paid"
        order.paid_at = now()

    db.add(order)
    db.commit()
    db.refresh(order)
    if type_ == "charge":
        share = max(0, min(100, site.get_int("creator_share_percent", 70)))
        gained = int(order.coins * share / 100)
        target = db.get(models.User, order.target_user_id)
        if target:
            target.coins += gained
            target.total_earned += gained
            db.commit()
            notify(
                db, target.id, "coin", f"{user.display_name or user.username} 给你充电了",
                f"收到 {gained} 硬币（分成 {share}%），感谢你的创作！",
                from_id=user.id, ref_type="user", ref_id=user.id,
            )
    audit(db, request, user, "order.create", "order", order.id, type_)
    return {"ok": True, "order": order_payload(order, db)}


@router.get("/orders/mine")
def my_orders(
    type: str = Query(""),
    user: models.User = Depends(require_user),
    db: Session = Depends(get_db),
):
    query = select(models.Order).where(models.Order.user_id == user.id)
    if type:
        query = query.where(models.Order.type == type)
    rows = db.scalars(query.order_by(models.Order.id.desc()).limit(100)).all()
    return {"items": [order_payload(item, db) for item in rows], "coins": user.coins}


@router.post("/orders/{order_id}/pay")
def pay_order(
    order_id: int,
    payload: dict,
    request: Request,
    user: models.User = Depends(require_user),
    db: Session = Depends(get_db),
):
    order = db.get(models.Order, order_id)
    if not order or order.user_id != user.id:
        raise fail(404, "订单不存在")
    if order.status != "pending":
        raise fail(400, "订单状态不允许支付")
    method = str(payload.get("pay_method") or order.pay_method)
    order.pay_method = method
    if method == "manual":
        # 人工审核：等待管理员确认收款
        db.commit()
        notify(
            db, user.id, "system", "订单已提交",
            "请按页面说明完成支付，管理员确认后订单会自动生效。",
            ref_type="order", ref_id=order.id,
        )
        return {"ok": True, "status": order.status, "message": site.get_str("pay_manual_note", "")}
    # 演示环境：在线支付直接标记成功（接入真实网关时在这里调用下单接口）
    apply_order(db, order)
    audit(db, request, user, "order.pay", "order", order.id, method)
    return {"ok": True, "status": order.status}


@router.post("/orders/{order_id}/cancel")
def cancel_order(order_id: int, user: models.User = Depends(require_user), db: Session = Depends(get_db)):
    order = db.get(models.Order, order_id)
    if not order or order.user_id != user.id:
        raise fail(404, "订单不存在")
    if order.status != "pending":
        raise fail(400, "订单已支付，无法取消")
    order.status = "cancelled"
    db.commit()
    return {"ok": True}


@router.get("/me/membership")
def my_membership(user: models.User = Depends(require_user)):
    active = bool(user.membership_expires and user.membership_expires > now())
    return {
        "level": user.membership_level if active else 0,
        "expires": iso(user.membership_expires),
        "active": active,
        "coins": user.coins,
        "totalEarned": user.total_earned,
        "canLive": bool(user.can_live or user.is_admin),
    }


# ------------------------------------------------------------------ 管理端


@router.get("/admin/orders")
def admin_orders(
    status: str = Query(""),
    type: str = Query(""),
    page: int = Query(1),
    size: int = Query(0),
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    _, size, limit, offset = pagination(page, size, 30, 200)
    query = select(models.Order)
    if status:
        query = query.where(models.Order.status == status)
    if type:
        query = query.where(models.Order.type == type)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(query.order_by(models.Order.id.desc()).limit(limit).offset(offset)).all()
    items = []
    for item in rows:
        data = order_payload(item, db)
        data["buyer"] = user_brief(db.get(models.User, item.user_id))
        items.append(data)
    stats = {
        "pending": db.scalar(select(func.count(models.Order.id)).where(models.Order.status == "pending")) or 0,
        "paid": db.scalar(select(func.count(models.Order.id)).where(models.Order.status == "paid")) or 0,
        "revenueCents": int(
            db.scalar(select(func.coalesce(func.sum(models.Order.amount_cents), 0)).where(models.Order.status == "paid")) or 0
        ),
    }
    return {"items": items, "total": int(total), "page": page, "size": size, "stats": stats}


@router.post("/admin/orders/{order_id}/review")
def review_order(
    order_id: int,
    payload: dict,
    request: Request,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    order = db.get(models.Order, order_id)
    if not order:
        raise fail(404, "订单不存在")
    action = str(payload.get("action") or "approve")
    note = str(payload.get("note") or "")[:200]
    if action == "approve":
        apply_order(db, order)
    elif action == "reject":
        order.status = "cancelled"
        if order.type == "charge":
            buyer = db.get(models.User, order.user_id)
            if buyer:
                buyer.coins += order.coins
    elif action == "refund":
        order.status = "refunded"
        buyer = db.get(models.User, order.user_id)
        if buyer and order.type == "coins":
            buyer.coins = max(0, buyer.coins - order.coins)
    order.note = note or order.note
    db.commit()
    notify(
        db, order.user_id, "system", "订单状态更新",
        f"订单 {order.order_no} 状态：{order.status}。{note}",
        ref_type="order", ref_id=order.id,
    )
    audit(db, request, admin, "admin.order_review", "order", order.id, action)
    return {"ok": True, "status": order.status}


@router.get("/admin/plans")
def admin_plans(admin: models.User = Depends(require_admin), db: Session = Depends(get_db)):
    rows = db.scalars(select(models.MembershipPlan).order_by(models.MembershipPlan.sort.asc())).all()
    return {"items": [plan_payload(item) for item in rows]}


@router.post("/admin/plans")
def create_plan(
    payload: dict,
    request: Request,
    admin: models.User = Depends(require_superadmin),
    db: Session = Depends(get_db),
):
    name = str(payload.get("name") or "").strip()
    if not name:
        raise fail(400, "请填写套餐名称")
    plan = models.MembershipPlan(
        name=name[:48],
        days=max(1, int(payload.get("days") or 30)),
        price_cents=max(0, int(float(payload.get("priceYuan") or 0) * 100)),
        description=str(payload.get("description") or "")[:255],
        badge=str(payload.get("badge") or "")[:24],
        sort=int(payload.get("sort") or 0),
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    audit(db, request, admin, "admin.plan_create", "plan", plan.id, name)
    return {"ok": True, "id": plan.id}


@router.put("/admin/plans/{plan_id}")
def update_plan(
    plan_id: int,
    payload: dict,
    request: Request,
    admin: models.User = Depends(require_superadmin),
    db: Session = Depends(get_db),
):
    plan = db.get(models.MembershipPlan, plan_id)
    if not plan:
        raise fail(404, "套餐不存在")
    if isinstance(payload.get("name"), str) and payload["name"].strip():
        plan.name = payload["name"].strip()[:48]
    if payload.get("days") is not None:
        plan.days = max(1, int(payload["days"]))
    if payload.get("priceYuan") is not None:
        plan.price_cents = max(0, int(float(payload["priceYuan"]) * 100))
    if isinstance(payload.get("description"), str):
        plan.description = payload["description"][:255]
    if isinstance(payload.get("badge"), str):
        plan.badge = payload["badge"][:24]
    if payload.get("sort") is not None:
        plan.sort = int(payload["sort"])
    if isinstance(payload.get("isActive"), bool):
        plan.is_active = payload["isActive"]
    db.commit()
    audit(db, request, admin, "admin.plan_update", "plan", plan.id)
    return {"ok": True}


@router.delete("/admin/plans/{plan_id}")
def delete_plan(
    plan_id: int,
    request: Request,
    admin: models.User = Depends(require_superadmin),
    db: Session = Depends(get_db),
):
    plan = db.get(models.MembershipPlan, plan_id)
    if plan:
        db.delete(plan)
        db.commit()
        audit(db, request, admin, "admin.plan_delete", "plan", plan_id)
    return {"ok": True}
