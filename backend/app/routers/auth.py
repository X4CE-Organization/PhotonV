"""注册、登录、个人资料与密码。"""
from __future__ import annotations

from typing import Optional

import re
from datetime import timedelta

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import mailer, models, redis_client as redis, settings_store as site, sms
from ..database import get_db
from ..security import create_token, current_user, hash_password, require_user, verify_password
from ..utils import audit, fail, iso, notify, user_me, now

router = APIRouter(prefix="/api/auth", tags=["auth"])

USERNAME_RE = re.compile(r"^[A-Za-z0-9_\u4e00-\u9fa5-]{1,64}$")
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

COOKIE_NAME = "photonv_token"


def validate_username(username: str) -> None:
    low = site.get_int("username_min_length", 3)
    high = site.get_int("username_max_length", 20)
    if len(username) < low:
        raise fail(400, f"用户名至少 {low} 个字符")
    if len(username) > high:
        raise fail(400, f"用户名最多 {high} 个字符")
    if not USERNAME_RE.match(username):
        raise fail(400, "用户名只能包含中文、字母、数字、下划线和短横线")
    banned = [item.lower() for item in (site.get_json("banned_usernames", []) or [])]
    if username.lower() in banned:
        raise fail(400, "该用户名已被保留，请更换")


def validate_password(password: str) -> None:
    low = site.get_int("password_min_length", 8)
    if len(password) < low:
        raise fail(400, f"密码至少 {low} 位")
    if len(password) > 128:
        raise fail(400, "密码过长")


def username_taken(db: Session, username: str) -> bool:
    return bool(db.scalar(select(models.User.id).where(models.User.username == username)))


def register_requirement() -> str:
    """注册必填项：none | email | phone | both（兼容旧的 register_need_email / phone_required_register）。"""
    mode = (site.get_str("register_require", "") or "").strip()
    if mode in {"none", "email", "phone", "both"}:
        return mode
    email = site.get_bool("register_need_email", False)
    phone = site.get_bool("phone_required_register", False)
    if email and phone:
        return "both"
    if email:
        return "email"
    if phone:
        return "phone"
    return "none"


def set_cookie(response: Response, token: str, days: int) -> None:
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=days * 86400,
        httponly=True,
        samesite="lax",
        path="/",
    )


@router.post("/register")
def register(payload: dict, request: Request, response: Response, db: Session = Depends(get_db)):
    if not site.get_bool("allow_register", True):
        raise fail(403, "本站暂未开放注册")

    username = str(payload.get("username") or "").strip()
    password = str(payload.get("password") or "")
    password2 = str(payload.get("password2") or "")
    email = str(payload.get("email") or "").strip().lower()

    validate_username(username)
    validate_password(password)
    if password2 and password2 != password:
        raise fail(400, "两次输入的密码不一致")
    requirement = register_requirement()
    email_required = requirement in {"email", "both"}
    phone_required = requirement in {"phone", "both"}
    if email_required and not email:
        raise fail(400, "请填写邮箱")

    if site.get_bool("register_need_invite", False):
        expected = site.get_str("invite_code", "")
        if not expected or str(payload.get("invite_code") or "").strip() != expected:
            raise fail(403, "邀请码不正确")

    if email:
        if not EMAIL_RE.match(email):
            raise fail(400, "邮箱格式不正确")
        suffixes = site.get_json("register_email_suffix", []) or []
        if suffixes:
            domain = email.split("@")[-1]
            if not any(domain == item or domain.endswith("." + item) for item in suffixes):
                raise fail(400, f"仅允许使用 {'、'.join(suffixes)} 邮箱注册")
        if db.scalar(select(models.User.id).where(models.User.email == email)):
            raise fail(409, "该邮箱已被注册")

    need_verify = site.get_bool("mail_register_verify", False) and site.get_bool("mail_enabled", False)
    if need_verify:
        if not email:
            raise fail(400, "请填写邮箱")
        code = str(payload.get("email_code") or "").strip()
        if not code:
            raise fail(400, "请填写邮箱验证码")
        if not mailer.consume_code(db, email, "verify", code):
            raise fail(400, "邮箱验证码不正确或已过期")

    # 手机号（可选 / 由设置决定是否必填）
    phone = sms.normalize(str(payload.get("phone") or ""))
    if phone_required and not phone:
        raise fail(400, "请填写手机号")
    if phone:
        if not sms.valid(phone):
            raise fail(400, "手机号格式不正确")
        if sms.by_phone(db, phone):
            raise fail(409, "该手机号已被注册")
        code = str(payload.get("phone_code") or "").strip()
        # 只有开启「注册时手机号需要验证码」才强制校验；关闭则只记录号码
        if site.get_bool("phone_register_verify", True):
            if not code:
                raise fail(400, "请填写手机验证码")
            if not sms.consume(db, phone, "register", code):
                raise fail(400, "手机验证码不正确或已过期")
        elif code:
            sms.consume(db, phone, "register", code)

    if username_taken(db, username):
        raise fail(409, "该用户名已被注册")

    role = "admin" if site.get_str("default_role", "user") == "admin" else "user"
    user = models.User(
        username=username,
        email=email or None,
        password_hash=hash_password(password),
        role=role,
        display_name=username,
        coins=site.get_int("coins_on_register", 5),
        is_private=site.get_bool("default_private", False),
        email_verified=bool(email),
        phone=phone or None,
        phone_verified=bool(phone),
        last_login_at=now(),
        last_login_ip=request.client.host if request.client else "",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # 新用户默认收藏夹
    db.add(models.FavoriteFolder(user_id=user.id, name="默认收藏夹", is_default=True))
    db.commit()

    audit(db, request, user, "user.register", "user", user.id, username)
    mailer.send(
        db, user.email or "", f"[{site.get_str('site_name', 'PhotonV')}] 欢迎加入",
        f"欢迎加入 {site.get_str('site_name', 'PhotonV')}",
        intro="你的账号已经创建成功，快去发布第一条视频吧！",
        button={"label": "进入首页", "url": site.get_str("site_url", "")},
        category="system", user_id=user.id, skip_throttle=True,
    )
    token = create_token(user, site.get_int("session_days", 14))
    set_cookie(response, token, site.get_int("session_days", 14))
    return {"token": token, "user": user_me(user)}


@router.post("/login")
def login(payload: dict, request: Request, response: Response, db: Session = Depends(get_db)):
    username = str(payload.get("username") or "").strip()
    password = str(payload.get("password") or "")
    if not username or not password:
        raise fail(400, "请填写用户名和密码")

    ip = request.client.host if request.client else ""
    lock_key = f"login:{username}:{ip}"
    limit = site.get_int("login_fail_limit", 10)
    if limit > 0:
        if (redis.counter_get(lock_key) or 0) >= limit:
            raise fail(429, "登录失败次数过多，请稍后再试")
        row = db.get(models.RateLimit, lock_key)
        if row and row.expires_at and row.expires_at > now() and row.count >= limit:
            raise fail(429, "登录失败次数过多，请稍后再试")

    user = db.scalar(select(models.User).where(models.User.username == username))
    if not user or not verify_password(password, user.password_hash):
        db.add(
            models.LoginLog(
                user_id=user.id if user else None, username=username, ip=ip,
                user_agent=request.headers.get("user-agent", "")[:250], success=False,
            )
        )
        if limit > 0:
            minutes = site.get_int("login_lock_minutes", 15)
            counted = redis.counter_incr(lock_key, minutes * 60)
            if counted is None:
                row = db.get(models.RateLimit, lock_key)
                if row and row.expires_at and row.expires_at > now():
                    row.count += 1
                    row.expires_at = now() + timedelta(minutes=minutes)
                else:
                    db.merge(
                        models.RateLimit(key=lock_key, count=1, expires_at=now() + timedelta(minutes=minutes))
                    )
        db.commit()
        raise fail(401, "用户名或密码错误")
    if user.is_banned:
        raise fail(403, f"账号已被封禁：{user.ban_reason or '违反社区规范'}")

    days = site.get_int("session_days", 14)
    if limit > 0:
        redis.counter_reset(lock_key)
        row = db.get(models.RateLimit, lock_key)
        if row:
            db.delete(row)

    # 每日登录赠送硬币
    bonus = site.get_int("coins_per_day", 0)
    today = now().strftime("%Y-%m-%d")
    if bonus > 0 and user.last_bonus_date != today:
        user.coins += bonus
        user.last_bonus_date = today
        notify(
            db, user.id, "system", f"每日登录奖励 +{bonus} 硬币",
            "感谢你每天来看看，继续创作吧！",
        )
    user.last_login_at = now()
    user.last_login_ip = ip
    db.add(
        models.LoginLog(
            user_id=user.id, username=user.username, ip=ip,
            user_agent=request.headers.get("user-agent", "")[:250], success=True,
        )
    )
    db.commit()

    token = create_token(user, days)
    set_cookie(response, token, days)
    audit(db, request, user, "user.login", "user", user.id)
    return {"token": token, "user": user_me(user)}


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"ok": True}


@router.get("/me")
def me(user: Optional[models.User] = Depends(current_user), db: Session = Depends(get_db)):
    if not user:
        return {"user": None, "unread": 0}
    unread = db.scalar(
        select(func.count(models.Notification.id)).where(
            models.Notification.user_id == user.id, models.Notification.is_read.is_(False)
        )
    )
    return {"user": user_me(user), "unread": int(unread or 0)}


@router.put("/profile")
def update_profile(payload: dict, request: Request, user: models.User = Depends(require_user), db: Session = Depends(get_db)):
    if isinstance(payload.get("display_name"), str) and payload["display_name"].strip():
        user.display_name = payload["display_name"].strip()[:32]
    if isinstance(payload.get("bio"), str):
        user.bio = payload["bio"][:500]
    if isinstance(payload.get("avatar"), str):
        user.avatar = payload["avatar"][:500]
    if isinstance(payload.get("banner"), str):
        user.banner = payload["banner"][:500]
    if isinstance(payload.get("gender"), (int, float)):
        user.gender = max(0, min(2, int(payload["gender"])))
    if isinstance(payload.get("birthday"), str):
        user.birthday = payload["birthday"][:32]
    if isinstance(payload.get("theme"), str) and payload["theme"] in {"light", "dark"}:
        user.theme = payload["theme"]
    if isinstance(payload.get("is_private"), bool):
        user.is_private = payload["is_private"]
    if isinstance(payload.get("allow_message"), bool):
        user.allow_message = payload["allow_message"]
    if isinstance(payload.get("show_email"), bool):
        user.show_email = payload["show_email"]
    if isinstance(payload.get("email"), str):
        email = payload["email"].strip().lower()
        if email and not EMAIL_RE.match(email):
            raise fail(400, "邮箱格式不正确")
        if email:
            taken = db.scalar(
                select(models.User.id).where(models.User.email == email, models.User.id != user.id)
            )
            if taken:
                raise fail(409, "该邮箱已被其他账号使用")
        user.email = email or None

    if isinstance(payload.get("username"), str) and payload["username"].strip():
        next_name = payload["username"].strip()
        if next_name != user.username:
            if not site.get_bool("allow_change_username", False):
                raise fail(403, "本站未开放修改用户名")
            validate_username(next_name)
            if username_taken(db, next_name):
                raise fail(409, "该用户名已被占用")
            user.username = next_name

    db.commit()
    db.refresh(user)
    audit(db, request, user, "user.update_profile", "user", user.id)
    return {"ok": True, "user": user_me(user)}


@router.put("/password")
def change_password(payload: dict, request: Request, user: models.User = Depends(require_user), db: Session = Depends(get_db)):
    old = str(payload.get("old_password") or "")
    new = str(payload.get("new_password") or "")
    new2 = str(payload.get("new_password2") or "")
    if new2 and new2 != new:
        raise fail(400, "两次输入的新密码不一致")
    validate_password(new)
    if not verify_password(old, user.password_hash):
        raise fail(400, "原密码不正确")
    user.password_hash = hash_password(new)
    db.commit()
    audit(db, request, user, "user.change_password", "user", user.id)
    return {"ok": True}


@router.get("/check-username")
def check_username(username: str, db: Session = Depends(get_db)):
    name = (username or "").strip()
    if not name:
        return {"available": False, "reason": "请输入用户名"}
    try:
        validate_username(name)
    except Exception as exc:  # noqa: BLE001 - HTTPException.message 在 detail 里
        detail = getattr(exc, "detail", {})
        return {"available": False, "reason": detail.get("message", "用户名不可用")}
    taken = username_taken(db, name)
    return {"available": not taken, "reason": "该用户名已被注册" if taken else ""}
