"""第三方登录：跳转授权、回调登录 / 绑定、解绑。"""
from __future__ import annotations

from typing import Optional

import secrets

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, oauth_client as oauth, settings_store as site
from ..database import get_db
from ..security import (
    create_token,
    current_user,
    require_user,
    sign_json,
    verify_json,
)
from ..utils import audit, fail, now, user_me

router = APIRouter(prefix="/api/auth/oauth", tags=["oauth"])


def frontend_redirect(**params: str) -> RedirectResponse:
    base = site.get_str("site_url", "http://localhost:8080").rstrip("/")
    query = "&".join(f"{key}={urllib_quote(value)}" for key, value in params.items() if value)
    return RedirectResponse(f"{base}/oauth/callback{'?' + query if query else ''}", status_code=302)


def urllib_quote(value: str) -> str:
    import urllib.parse

    return urllib.parse.quote(str(value))


def issue_token(db: Session, user: models.User) -> str:
    days = site.get_int("session_days", 14)
    user.last_login_at = now()
    db.commit()
    return create_token(user, days)


@router.get("/providers")
def providers():
    return {
        "showOnLogin": site.get_bool("oauth_show_on_login", True),
        "items": [
            {"id": item["id"], "name": item["name"], "color": item["color"]}
            for item in oauth.enabled_providers()
        ],
    }


@router.get("/{provider}/start")
def start(provider: str, redirect: str = "/", bind: int = 0, db: Session = Depends(get_db), viewer: Optional[models.User] = Depends(current_user)):
    config = oauth.provider_config(provider)
    if not config or not config["enabled"]:
        raise fail(404, "该第三方登录未启用")
    if bind and not site.get_bool("oauth_allow_bind", True):
        raise fail(403, "本站已关闭第三方账号绑定")
    if bind and not viewer:
        return frontend_redirect(error="请先登录后再绑定第三方账号")
    state = sign_json(
        {"p": provider, "r": redirect or "/", "u": viewer.id if (bind and viewer) else 0, "n": secrets.token_hex(4)},
        expires_seconds=600,
    )
    return RedirectResponse(oauth.authorize_url(config, state), status_code=302)


@router.get("/{provider}/callback")
def callback(provider: str, code: str = "", state: str = "", db: Session = Depends(get_db)):
    config = oauth.provider_config(provider)
    if not config or not config["enabled"]:
        return frontend_redirect(error="该第三方登录未启用")
    payload = verify_json(state)
    if not payload or payload.get("p") != provider:
        return frontend_redirect(error="登录状态校验失败，请重试")
    if not code:
        return frontend_redirect(error="缺少授权码")

    token_result = oauth.exchange_code(config, code)
    if "error" in token_result:
        return frontend_redirect(error=token_result["error"])
    profile_result = oauth.fetch_profile(config, token_result["accessToken"])
    if "error" in profile_result:
        return frontend_redirect(error=profile_result["error"])
    profile = profile_result["profile"]

    link = db.scalar(
        select(models.OAuthAccount).where(
            models.OAuthAccount.provider == provider,
            models.OAuthAccount.provider_user_id == profile["providerUserId"],
        )
    )

    # ------------------------------------------------------------ 绑定
    bind_user_id = int(payload.get("u") or 0)
    if bind_user_id:
        user = db.get(models.User, bind_user_id)
        if not user:
            return frontend_redirect(error="账号不存在")
        if link and link.user_id != user.id:
            return frontend_redirect(error="该第三方账号已绑定到其他用户")
        if not link:
            db.add(
                models.OAuthAccount(
                    user_id=user.id,
                    provider=provider,
                    provider_user_id=profile["providerUserId"],
                    provider_username=profile["username"],
                    provider_email=profile["email"],
                    avatar=profile["avatar"][:500],
                )
            )
            db.commit()
        audit(db, None, user, "oauth.bind", "user", user.id, provider)
        return frontend_redirect(bound=config["name"])

    # ------------------------------------------------------------ 登录
    user = db.get(models.User, link.user_id) if link else None
    if not user and profile["email"] and site.get_bool("oauth_bind_by_email", True):
        user = db.scalar(
            select(models.User).where(models.User.email == profile["email"].lower())
        )
        if user and not link:
            db.add(
                models.OAuthAccount(
                    user_id=user.id,
                    provider=provider,
                    provider_user_id=profile["providerUserId"],
                    provider_username=profile["username"],
                    provider_email=profile["email"],
                    avatar=profile["avatar"][:500],
                )
            )
            db.commit()

    if not user:
        if not site.get_bool("oauth_auto_register", True):
            return frontend_redirect(error="该第三方账号尚未绑定账号，请联系管理员")
        base = "".join(ch for ch in profile["username"] if ch.isalnum() or ch == "_")[:16] or "user"
        username = base
        index = 1
        while db.scalar(select(models.User.id).where(models.User.username == username)):
            username = f"{base}{index}"
            index += 1
        role = "admin" if site.get_str("oauth_default_role", "user") == "admin" else "user"
        user = models.User(
            username=username,
            email=profile["email"].lower() or None,
            password_hash="oauth-no-password",
            role=role,
            display_name=(profile["username"] or username)[:32],
            avatar=profile["avatar"][:500] or None,
            email_verified=bool(profile["email"]),
            coins=site.get_int("coins_on_register", 5),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        db.add(models.FavoriteFolder(user_id=user.id, name="默认收藏夹", is_default=True))
        db.add(
            models.OAuthAccount(
                user_id=user.id,
                provider=provider,
                provider_user_id=profile["providerUserId"],
                provider_username=profile["username"],
                provider_email=profile["email"],
                avatar=profile["avatar"][:500],
            )
        )
        db.commit()
        audit(db, None, user, "oauth.register", "user", user.id, provider)

    if user.is_banned:
        return frontend_redirect(error=f"账号已被封禁：{user.ban_reason or '违反社区规范'}")
    if link:
        link.provider_username = profile["username"]
        link.provider_email = profile["email"]
        link.avatar = profile["avatar"][:500]
    db.commit()
    token = issue_token(db, user)
    audit(db, None, user, "oauth.login", "user", user.id, provider)
    return frontend_redirect(token=token, redirect=str(payload.get("r") or "/"))


@router.get("/bindings")
def bindings(user: Optional[models.User] = Depends(current_user), db: Session = Depends(get_db)):
    if not user:
        return {"bindings": [], "providers": []}
    rows = db.scalars(select(models.OAuthAccount).where(models.OAuthAccount.user_id == user.id)).all()
    return {
        "bindings": [
            {
                "provider": item.provider,
                "username": item.provider_username,
                "avatar": item.avatar,
                "boundAt": item.created_at.strftime("%Y-%m-%d %H:%M:%S") if item.created_at else "",
            }
            for item in rows
        ],
        "providers": [
            {"id": item["id"], "name": item["name"], "color": item["color"]}
            for item in oauth.enabled_providers()
        ],
    }


@router.delete("/{provider}")
def unbind(provider: str, request: Request, user: models.User = Depends(require_user), db: Session = Depends(get_db)):
    row = db.scalar(
        select(models.OAuthAccount).where(
            models.OAuthAccount.user_id == user.id, models.OAuthAccount.provider == provider
        )
    )
    if not row:
        raise fail(404, "未绑定该第三方账号")
    db.delete(row)
    db.commit()
    audit(db, request, user, "oauth.unbind", "user", user.id, provider)
    return {"ok": True}
