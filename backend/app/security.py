"""密码哈希、JWT 签发与鉴权依赖（全部使用标准库，无第三方加密依赖）。"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Any, Optional

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from .config import settings
from .database import get_db
from . import models

PBKDF2_ROUNDS = 120_000


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), PBKDF2_ROUNDS)
    return f"pbkdf2_sha256${PBKDF2_ROUNDS}${salt}${digest.hex()}"


def verify_password(password: str, hashed: str) -> bool:
    try:
        algorithm, rounds, salt, digest = hashed.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        computed = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt.encode("utf-8"), int(rounds)
        )
        return hmac.compare_digest(computed.hex(), digest)
    except (ValueError, AttributeError):
        return False


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _sign(data: str) -> str:
    return _b64encode(hmac.new(settings.secret_key.encode("utf-8"), data.encode("ascii"), hashlib.sha256).digest())


def create_token(user: models.User, days: Optional[int] = None) -> str:
    """签发 HS256 JWT。"""
    expires_in = (days if days is not None else settings.token_days) * 86400
    now = int(time.time())
    header = _b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    payload = _b64encode(
        json.dumps(
            {"sub": user.id, "username": user.username, "role": user.role, "iat": now, "exp": now + expires_in},
            separators=(",", ":"),
        ).encode()
    )
    body = f"{header}.{payload}"
    return f"{body}.{_sign(body)}"


def decode_token(token: str) -> Optional[dict[str, Any]]:
    parts = token.split(".")
    if len(parts) != 3:
        return None
    body = f"{parts[0]}.{parts[1]}"
    if not hmac.compare_digest(_sign(body), parts[2]):
        return None
    try:
        payload = json.loads(_b64decode(parts[1]))
    except (ValueError, json.JSONDecodeError):
        return None
    if not payload.get("exp") or payload["exp"] < time.time():
        return None
    return payload


def token_from_request(request: Request) -> Optional[str]:
    header = request.headers.get("authorization") or ""
    if header.lower().startswith("bearer "):
        return header[7:].strip()
    return request.cookies.get("photonv_token")


def current_user(request: Request, db: Session = Depends(get_db)) -> Optional[models.User]:
    """可选登录：未登录返回 None。"""
    token = token_from_request(request)
    if not token:
        return None
    payload = decode_token(token)
    if not payload:
        return None
    user = db.get(models.User, payload.get("sub"))
    if not user or user.is_banned:
        return None
    return user


def require_user(user: Optional[models.User] = Depends(current_user)) -> models.User:
    if not user:
        raise HTTPException(status_code=401, detail={"code": "UNAUTHORIZED", "message": "请先登录"})
    return user


def require_admin(user: Optional[models.User] = Depends(current_user)) -> models.User:
    if not user:
        raise HTTPException(status_code=401, detail={"code": "UNAUTHORIZED", "message": "请先登录"})
    if not user.is_admin:
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "没有权限执行该操作"})
    return user


def require_superadmin(user: Optional[models.User] = Depends(current_user)) -> models.User:
    if not user:
        raise HTTPException(status_code=401, detail={"code": "UNAUTHORIZED", "message": "请先登录"})
    if not user.is_superadmin:
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "仅超级管理员可操作"})
    return user
