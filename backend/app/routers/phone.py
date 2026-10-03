"""手机号：验证码、绑定 / 解绑、手机号登录与后台测试发送。"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from .. import models, settings_store as site, sms
from ..database import get_db
from ..security import create_token, require_admin, require_user
from ..utils import audit, fail, notify, now, user_me

router = APIRouter(prefix="/api", tags=["phone"])

PURPOSES = {"register", "login", "reset", "bind"}


def issue_and_send(db: Session, phone: str, purpose: str, user_id: Optional[int] = None) -> dict:
    interval = site.get_int("sms_code_interval", 60)
    if sms.recent(db, phone, interval, purpose) > 0:
        raise fail(429, f"验证码发送过于频繁，请 {interval} 秒后再试")
    limit = site.get_int("sms_daily_limit", 10)
    if limit > 0 and sms.today_count(db, phone) >= limit:
        raise fail(429, "该手机号今日验证码次数已达上限")
    code = sms.issue(db, phone, purpose, user_id)
    result = sms.send_sms(phone, code)
    if result.get("ok"):
        return {"ok": True, "dev": False}
    if not sms.enabled():
        # 开发模式：验证码写进站内信与日志，方便本地调试
        if user_id:
            notify(
                db,
                user_id,
                "system",
                "手机验证码（开发模式）",
                f"手机号 {phone} 的验证码是 {code}，{site.get_int('sms_code_ttl_minutes', 10)} 分钟内有效。",
            )
        print(f"[photonv] 短信开发模式：{phone} 的验证码是 {code}")
        return {"ok": True, "dev": True, "code": code}
    raise fail(400, f"短信发送失败：{result.get('error')}")


@router.post("/auth/sms-code")
def send_code(payload: dict, db: Session = Depends(get_db)):
    """注册 / 登录 / 找回密码 / 绑定手机号 的验证码。"""
    phone = sms.normalize(str(payload.get("phone") or ""))
    purpose = str(payload.get("purpose") or "bind")
    if purpose not in PURPOSES:
        purpose = "bind"
    if not sms.valid(phone):
        raise fail(400, "手机号格式不正确")

    existing = sms.by_phone(db, phone)
    if purpose == "register" and existing:
        raise fail(409, "该手机号已被注册")
    if purpose == "login" and not existing:
        return {"ok": True, "hidden": True}
    if purpose == "bind" and existing:
        raise fail(409, "该手机号已被其他账号绑定")
    return issue_and_send(db, phone, purpose, existing.id if existing else None)


@router.post("/auth/phone-login")
def phone_login(payload: dict, request: Request, db: Session = Depends(get_db)):
    if not site.get_bool("phone_login_enabled", True):
        raise fail(403, "本站已关闭手机号登录")
    phone = sms.normalize(str(payload.get("phone") or ""))
    code = str(payload.get("code") or "").strip()
    if not sms.valid(phone) or not code:
        raise fail(400, "请填写手机号与验证码")
    if not sms.consume(db, phone, "login", code):
        raise fail(400, "验证码不正确或已过期")
    user = sms.by_phone(db, phone)
    if not user:
        raise fail(404, "该手机号还没有绑定账号，请先用用户名登录后在设置里绑定")
    if user.is_banned:
        raise fail(403, f"账号已被封禁：{user.ban_reason or '违反社区规范'}")
    user.last_login_at = now()
    user.phone_verified = True
    db.commit()
    token = create_token(user, site.get_int("session_days", 14))
    audit(db, request, user, "user.phone_login", "user", user.id)
    return {"token": token, "user": user_me(user)}


@router.get("/me/phone")
def my_phone(user: models.User = Depends(require_user)):
    return {
        "phone": sms.masked(user.phone),
        "verified": bool(user.phone_verified),
        "bound": bool(user.phone),
        "smsEnabled": sms.enabled(),
    }


@router.put("/me/phone")
def bind_phone(
    payload: dict,
    request: Request,
    user: models.User = Depends(require_user),
    db: Session = Depends(get_db),
):
    phone = sms.normalize(str(payload.get("phone") or ""))
    code = str(payload.get("code") or "").strip()
    if not sms.valid(phone):
        raise fail(400, "手机号格式不正确")
    taken = sms.by_phone(db, phone)
    if taken and taken.id != user.id:
        raise fail(409, "该手机号已被其他账号绑定")
    if not sms.consume(db, phone, "bind", code):
        raise fail(400, "验证码不正确或已过期")
    user.phone = phone
    user.phone_verified = True
    db.commit()
    audit(db, request, user, "user.bind_phone", "user", user.id)
    return {"ok": True, "phone": sms.masked(phone)}


@router.delete("/me/phone")
def unbind_phone(request: Request, user: models.User = Depends(require_user), db: Session = Depends(get_db)):
    if site.get_bool("phone_required_bind", False):
        raise fail(400, "本站要求必须绑定手机号，无法解绑")
    user.phone = None
    user.phone_verified = False
    db.commit()
    audit(db, request, user, "user.unbind_phone", "user", user.id)
    return {"ok": True}


@router.post("/admin/sms/test")
def sms_test(
    payload: dict,
    request: Request,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    phone = sms.normalize(str(payload.get("phone") or ""))
    if not sms.valid(phone):
        raise fail(400, "手机号格式不正确")
    code = sms.issue(db, phone, "test", admin.id)
    result = sms.send_sms(phone, code)
    if not result.get("ok") and sms.enabled():
        raise fail(400, result.get("error") or "发送失败")
    audit(db, request, admin, "admin.sms_test", detail=phone)
    return {
        "ok": True,
        "provider": sms.provider(),
        "dev": bool(result.get("dev")),
        "code": code if result.get("dev") else "",
        "message": "短信服务未启用，验证码如下（开发模式）" if result.get("dev") else "已发送",
    }


@router.get("/admin/sms/status")
def sms_status(admin: models.User = Depends(require_admin)):
    return {
        "enabled": sms.enabled(),
        "provider": sms.provider(),
        "configured": bool(
            (sms.provider() == "aliyun" and site.get_str("sms_aliyun_key_id"))
            or (sms.provider() == "tencent" and site.get_str("sms_tencent_secret_id"))
            or (sms.provider() == "custom" and site.get_str("sms_custom_url"))
        ),
    }
