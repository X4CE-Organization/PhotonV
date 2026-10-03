"""邮件：验证码、找回密码与后台测试。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import mailer, models, settings_store as site
from ..database import get_db
from ..security import hash_password, require_admin, require_user
from ..utils import audit, fail, iso

router = APIRouter(prefix="/api", tags=["mail"])

EMAIL_RE = None


def _valid_email(value: str) -> bool:
    import re

    return bool(re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", value))


@router.post("/auth/mail-code")
def send_code(payload: dict, db: Session = Depends(get_db)):
    """注册验证码 / 找回密码验证码（对未注册邮箱不暴露账号是否存在）。"""
    if not mailer.enabled():
        raise fail(403, "本站暂未开启邮件服务")
    account = str(payload.get("account") or "").strip()
    purpose = "verify" if payload.get("purpose") == "verify" else "reset"
    if not account:
        raise fail(400, "请填写邮箱或用户名")

    interval = site.get_int("mail_code_interval_seconds", 60)
    if purpose == "verify":
        email = account.lower()
        if not _valid_email(email):
            raise fail(400, "邮箱格式不正确")
        if db.scalar(select(models.User.id).where(models.User.email == email)):
            raise fail(400, "该邮箱已被注册")
        if mailer.recent_codes(db, email, "verify", interval) > 0:
            raise fail(429, f"验证码发送过于频繁，请 {interval} 秒后再试")
        code = mailer.issue_code(db, email, "verify")
        result = mailer.send(
            db, email, f"[{site.get_str('site_name', 'PhotonV')}] 注册验证码", "注册验证码",
            intro="请在注册页面输入下面的验证码完成注册：", code=code,
            footnote="如果这不是你本人的操作，忽略本邮件即可。", skip_throttle=True,
        )
        if not result.get("ok"):
            raise fail(400, f"邮件发送失败：{result.get('error')}")
        return {"ok": True, "masked": email.replace(email.split("@")[0], "***")}

    user = db.scalar(
        select(models.User).where((models.User.username == account) | (models.User.email == account.lower()))
    )
    email = (user.email if user and user.email else account.lower())
    if not _valid_email(email):
        return {"ok": True, "masked": ""}
    if mailer.recent_codes(db, email, "reset", interval) > 0:
        raise fail(429, f"验证码发送过于频繁，请 {interval} 秒后再试")
    code = mailer.issue_code(db, email, "reset", user.id if user else None)
    result = mailer.send(
        db, email, f"[{site.get_str('site_name', 'PhotonV')}] 找回密码验证码", "找回密码",
        intro="请在页面输入下面的验证码来重置密码：", code=code,
        footnote="如果不是你本人操作，忽略本邮件即可，密码不会改变。", skip_throttle=True,
    )
    if not result.get("ok") and not result.get("skipped"):
        raise fail(400, f"邮件发送失败：{result.get('error')}")
    masked = email.replace(email.split("@")[0], "***") if result.get("ok") else ""
    return {"ok": True, "masked": masked}


@router.post("/auth/reset-password")
def reset_password(payload: dict, db: Session = Depends(get_db)):
    if not site.get_bool("mail_reset_enabled", True):
        raise fail(403, "本站已关闭邮箱找回密码")
    account = str(payload.get("account") or "").strip()
    code = str(payload.get("code") or "").strip()
    password = str(payload.get("password") or "")
    if not account or not code:
        raise fail(400, "请填写账号与验证码")
    if len(password) < site.get_int("password_min_length", 8):
        raise fail(400, "新密码太短")
    if payload.get("password2") not in (None, password):
        raise fail(400, "两次输入的密码不一致")

    user = db.scalar(
        select(models.User).where((models.User.username == account) | (models.User.email == account.lower()))
    )
    if not user or not user.email:
        raise fail(400, "验证码不正确或已过期")
    if not mailer.consume_code(db, user.email, "reset", code):
        raise fail(400, "验证码不正确或已过期")
    user.password_hash = hash_password(password)
    db.commit()
    return {"ok": True}


@router.get("/me/mail-preference")
def mail_preference(user: models.User = Depends(require_user)):
    return {"email": user.email or "", "optout": bool(user.mail_optout), "enabled": mailer.enabled()}


@router.put("/me/mail-preference")
def set_mail_preference(payload: dict, user: models.User = Depends(require_user), db: Session = Depends(get_db)):
    user.mail_optout = bool(payload.get("optout"))
    db.commit()
    return {"ok": True, "optout": user.mail_optout}


@router.get("/me/mail-logs")
def my_mail_logs(user: models.User = Depends(require_user), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(models.MailLog)
        .where(models.MailLog.user_id == user.id)
        .order_by(models.MailLog.id.desc())
        .limit(20)
    ).all()
    return {
        "items": [
            {"id": item.id, "subject": item.subject, "status": item.status, "createdAt": iso(item.created_at)}
            for item in rows
        ]
    }


@router.get("/admin/mail/status")
def mail_status(admin: models.User = Depends(require_admin), db: Session = Depends(get_db)):
    rows = db.scalars(select(models.MailLog).order_by(models.MailLog.id.desc()).limit(20)).all()
    return {
        "configured": mailer.configured(),
        "enabled": mailer.enabled(),
        "logs": [
            {
                "id": item.id,
                "to": item.to_email,
                "subject": item.subject,
                "status": item.status,
                "error": item.error,
                "createdAt": iso(item.created_at),
            }
            for item in rows
        ],
    }


@router.post("/admin/mail/verify")
def mail_verify(admin: models.User = Depends(require_admin), db: Session = Depends(get_db)):
    return mailer.verify_connection(db)


@router.post("/admin/mail/test")
def mail_test(
    payload: dict,
    request: Request,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    to = str(payload.get("to") or "").strip()
    if not _valid_email(to):
        raise fail(400, "请填写正确的收件邮箱")
    if not mailer.enabled():
        raise fail(400, "请先启用邮件服务并配置 SMTP")
    result = mailer.send(
        db, to, f"[{site.get_str('site_name', 'PhotonV')}] SMTP 测试邮件", "SMTP 配置成功",
        intro="收到这封邮件说明 PhotonV 的邮件服务已经可以正常发信了。",
        footnote="本邮件由管理后台的「发送测试邮件」触发。",
        skip_throttle=True, user_id=admin.id,
    )
    if not result.get("ok"):
        raise fail(400, result.get("error") or "发送失败")
    audit(db, request, admin, "admin.mail_test", detail=to)
    return {"ok": True}
