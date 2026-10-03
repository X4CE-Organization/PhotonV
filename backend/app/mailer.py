"""SMTP 邮件：验证码、找回密码与通知邮件（标准库 smtplib，无第三方依赖）。"""
from __future__ import annotations

import smtplib
import ssl
from datetime import datetime, timedelta
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import models, settings_store as site


def configured() -> bool:
    return bool(site.get_str("smtp_host", "").strip())


def enabled() -> bool:
    return site.get_bool("mail_enabled", False) and configured()


def sender() -> str:
    address = site.get_str("smtp_from", "").strip() or site.get_str("smtp_user", "").strip()
    name = site.get_str("mail_from_name", "").strip() or site.get_str("site_name", "PhotonV")
    return formataddr((str(Header(name, "utf-8")), address)) if address else ""


def _render(title: str, intro: str = "", lines: Optional[list[str]] = None, code: str = "",
            button: Optional[dict] = None, footnote: str = "") -> tuple[str, str]:
    name = site.get_str("site_name", "PhotonV")
    color = site.get_str("theme_color", "#7c5cff")
    url = site.get_str("site_url", "")
    lines = lines or []

    text_parts = [title, "", intro, *lines]
    if code:
        text_parts.append(f"验证码：{code}")
    if button:
        text_parts.append(f"{button.get('label')}：{button.get('url')}")
    text_parts.extend(["", f"—— {name}"])
    text = "\n".join(part for part in text_parts if part)

    blocks = [f'<h1 style="margin:0 0 12px;font-size:18px">{title}</h1>']
    if intro:
        blocks.append(f'<p style="margin:0 0 12px;font-size:14px;color:#475569">{intro}</p>')
    for line in lines:
        blocks.append(f'<p style="margin:0 0 8px;font-size:14px;color:#475569">{line}</p>')
    if code:
        blocks.append(
            '<div style="margin:16px 0;padding:14px;text-align:center;background:#f8fafc;'
            'border:1px dashed #cbd5e1;border-radius:10px">'
            '<div style="font-size:12px;color:#64748b">验证码（10 分钟内有效）</div>'
            f'<div style="font-size:26px;font-weight:700;letter-spacing:4px;font-family:monospace">{code}</div>'
            "</div>"
        )
    if button:
        blocks.append(
            f'<div style="margin:18px 0"><a href="{button.get("url")}" '
            f'style="display:inline-block;padding:10px 18px;background:{color};color:#fff;'
            f'border-radius:8px;text-decoration:none;font-size:14px">{button.get("label")}</a></div>'
        )
    if footnote:
        blocks.append(f'<p style="margin:14px 0 0;font-size:12px;color:#94a3b8">{footnote}</p>')

    html = (
        '<!doctype html><html><body style="margin:0;padding:24px;background:#f1f5f9;'
        "font-family:-apple-system,'PingFang SC','Microsoft YaHei',sans-serif;color:#0f172a\">"
        '<div style="max-width:560px;margin:0 auto;background:#fff;border-radius:14px;overflow:hidden;'
        'border:1px solid #e2e8f0">'
        f'<div style="padding:18px 24px;background:{color};color:#fff;font-size:16px;font-weight:600">{name}</div>'
        f'<div style="padding:24px">{"".join(blocks)}</div>'
        f'<div style="padding:14px 24px;background:#f8fafc;font-size:12px;color:#94a3b8">'
        f"本邮件由 {name} 自动发送{(' · ' + url) if url else ''}</div>"
        "</div></body></html>"
    )
    return html, text


def send(db: Session, to: str, subject: str, title: str, intro: str = "",
         lines: Optional[list[str]] = None, code: str = "", button: Optional[dict] = None,
         footnote: str = "", category: str = "system", user_id: Optional[int] = None,
         skip_throttle: bool = False) -> dict:
    """发送邮件；未启用或失败时返回 {ok: False, error}，不会抛异常打断主流程。"""
    address = (to or "").strip()
    if not enabled():
        return {"ok": False, "skipped": True, "error": "未启用邮件服务"}
    if not address:
        return {"ok": False, "skipped": True, "error": "收件人为空"}
    from_addr = sender()
    if not from_addr:
        return {"ok": False, "skipped": True, "error": "未配置发件人"}

    throttle = site.get_int("mail_throttle_seconds", 60)
    if throttle > 0 and not skip_throttle:
        recent = db.scalar(
            select(func.count(models.MailLog.id)).where(
                models.MailLog.to_email == address,
                models.MailLog.status == "sent",
                models.MailLog.created_at >= datetime.utcnow() - timedelta(seconds=throttle),
            )
        )
        if recent:
            return {"ok": False, "skipped": True, "error": "发送过于频繁"}

    html, text = _render(title, intro, lines, code, button, footnote)
    message = MIMEMultipart("alternative")
    message["Subject"] = Header(subject, "utf-8")
    message["From"] = from_addr
    message["To"] = address
    reply_to = site.get_str("mail_reply_to", "").strip()
    if reply_to:
        message["Reply-To"] = reply_to
    message.attach(MIMEText(text, "plain", "utf-8"))
    message.attach(MIMEText(html, "html", "utf-8"))

    host = site.get_str("smtp_host").strip()
    port = site.get_int("smtp_port", 465)
    user = site.get_str("smtp_user").strip()
    password = site.get_str("smtp_password", "")
    try:
        if site.get_bool("smtp_ssl", True):
            context = ssl.create_default_context()
            if site.get_bool("mail_allow_insecure_tls", False):
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
            server = smtplib.SMTP_SSL(host, port, timeout=15, context=context)
        else:
            server = smtplib.SMTP(host, port, timeout=15)
            if site.get_bool("smtp_starttls", True):
                server.starttls(context=ssl.create_default_context())
        if user:
            server.login(user, password)
        server.sendmail(site.get_str("smtp_from").strip() or user, [address], message.as_string())
        server.quit()
        db.add(models.MailLog(to_email=address, subject=subject[:160], category=category, status="sent", user_id=user_id))
        db.commit()
        return {"ok": True}
    except Exception as exc:  # noqa: BLE001
        db.add(
            models.MailLog(
                to_email=address,
                subject=subject[:160],
                category=category,
                status="failed",
                error=str(exc)[:500],
                user_id=user_id,
            )
        )
        db.commit()
        print(f"[photonv] 邮件发送失败（{address}）：{exc}")
        return {"ok": False, "error": str(exc)}


def send_to_user(db: Session, user_id: int, subject: str, title: str, **kwargs: Any) -> dict:
    """给站内用户发邮件，自动尊重退订与分类开关。"""
    if not enabled():
        return {"ok": False, "skipped": True, "error": "未启用邮件服务"}
    category = kwargs.get("category", "system")
    switch = {
        "reply": "notify_mail_reply",
        "like": "notify_mail_like",
        "coin": "notify_mail_coin",
        "order": "notify_mail_order",
        "system": "notify_mail_system",
    }.get(category, "notify_mail_system")
    if not site.get_bool(switch, True):
        return {"ok": False, "skipped": True, "error": "该类型邮件已关闭"}
    user = db.get(models.User, user_id)
    if not user or not user.email:
        return {"ok": False, "skipped": True, "error": "用户未填写邮箱"}
    if getattr(user, "mail_optout", False):
        return {"ok": False, "skipped": True, "error": "用户已退订"}
    return send(db, user.email, subject, title, user_id=user_id, **kwargs)


def verify_connection(db: Session) -> dict:
    if not configured():
        return {"ok": False, "error": "未配置 SMTP 服务器"}
    host = site.get_str("smtp_host").strip()
    port = site.get_int("smtp_port", 465)
    try:
        if site.get_bool("smtp_ssl", True):
            server = smtplib.SMTP_SSL(host, port, timeout=10)
        else:
            server = smtplib.SMTP(host, port, timeout=10)
        server.ehlo()
        user = site.get_str("smtp_user").strip()
        if user:
            server.login(user, site.get_str("smtp_password", ""))
        server.quit()
        return {"ok": True}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}


# ---------------------------------------------------------------- 验证码


def issue_code(db: Session, email: str, purpose: str, user_id: Optional[int] = None, ttl_minutes: int = 10) -> str:
    import secrets

    code = "".join(secrets.choice("0123456789") for _ in range(6))
    db.query(models.MailCode).filter(
        models.MailCode.email == email.lower(), models.MailCode.purpose == purpose, models.MailCode.used.is_(False)
    ).update({"used": True})
    db.add(
        models.MailCode(
            email=email.lower(),
            code=code,
            purpose=purpose,
            user_id=user_id,
            expires_at=datetime.utcnow() + timedelta(minutes=ttl_minutes),
        )
    )
    db.commit()
    return code


def consume_code(db: Session, email: str, purpose: str, code: str) -> bool:
    row = db.scalar(
        select(models.MailCode)
        .where(
            models.MailCode.email == email.lower(),
            models.MailCode.purpose == purpose,
            models.MailCode.used.is_(False),
            models.MailCode.expires_at > datetime.utcnow(),
        )
        .order_by(models.MailCode.id.desc())
    )
    if not row or row.attempts >= 5:
        return False
    if row.code != code.strip():
        row.attempts += 1
        db.commit()
        return False
    row.used = True
    db.commit()
    return True


def recent_codes(db: Session, email: str, purpose: str, seconds: int) -> int:
    return int(
        db.scalar(
            select(func.count(models.MailCode.id)).where(
                models.MailCode.email == email.lower(),
                models.MailCode.purpose == purpose,
                models.MailCode.created_at >= datetime.utcnow() - timedelta(seconds=seconds),
            )
        )
        or 0
    )
