"""表情包：上传制作、收藏别人的、在评论 / 私信里发送。"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import models, settings_store as site
from ..database import get_db
from ..security import current_user, require_user
from ..utils import audit, fail, iso, user_brief

router = APIRouter(prefix="/api/emojis", tags=["emojis"])

MAX_EMOJIS = 300


def emoji_payload(item: models.Emoji, owner: Optional[models.User], viewer_id: Optional[int]) -> dict:
    return {
        "id": item.id,
        "name": item.name or "",
        "url": item.url,
        "useCount": item.use_count,
        "createdAt": iso(item.created_at),
        "isMine": bool(viewer_id and item.owner_id == viewer_id),
        "owner": user_brief(owner),
    }


def load_emoji(db: Session, emoji_id: int) -> models.Emoji:
    item = db.get(models.Emoji, emoji_id)
    if not item:
        raise fail(404, "表情不存在")
    return item


@router.get("")
def my_emojis(
    db: Session = Depends(get_db),
    user: models.User = Depends(require_user),
):
    if not site.get_bool("emoji_enabled", True):
        return {"enabled": False, "items": []}
    rows = db.scalars(
        select(models.Emoji).where(models.Emoji.owner_id == user.id).order_by(models.Emoji.id.desc()).limit(MAX_EMOJIS)
    ).all()
    return {"enabled": True, "items": [emoji_payload(row, user, user.id) for row in rows]}


@router.get("/popular")
def popular_emojis(
    limit: int = Query(40),
    db: Session = Depends(get_db),
    viewer: Optional[models.User] = Depends(current_user),
):
    if not site.get_bool("emoji_enabled", True):
        return {"items": []}
    size = max(1, min(80, limit))
    rows = db.scalars(
        select(models.Emoji).order_by(models.Emoji.use_count.desc(), models.Emoji.id.desc()).limit(size)
    ).all()
    owners = {row.owner_id: db.get(models.User, row.owner_id) for row in rows}
    return {"items": [emoji_payload(row, owners.get(row.owner_id), viewer.id if viewer else None) for row in rows]}


@router.post("")
def create_emoji(
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_user),
):
    if not site.get_bool("emoji_enabled", True):
        raise fail(403, "本站已关闭表情包功能")
    url = str(payload.get("url") or "").strip()
    if not url:
        raise fail(400, "请先上传表情图片")
    if not (url.startswith("/media/") or url.startswith("http")):
        raise fail(400, "表情地址不合法")
    total = (
        db.scalar(select(func.count()).select_from(models.Emoji).where(models.Emoji.owner_id == user.id)) or 0
    )
    if total >= MAX_EMOJIS:
        raise fail(400, f"最多保存 {MAX_EMOJIS} 个表情")
    item = models.Emoji(
        owner_id=user.id,
        name=str(payload.get("name") or "")[:32],
        url=url[:500],
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    audit(db, request, user, "emoji.create", "emoji", item.id)
    return {"ok": True, "emoji": emoji_payload(item, user, user.id)}


@router.put("/{emoji_id}")
def update_emoji(
    emoji_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_user),
):
    item = load_emoji(db, emoji_id)
    if item.owner_id != user.id:
        raise fail(403, "只能修改自己的表情")
    if isinstance(payload.get("name"), str):
        item.name = payload["name"].strip()[:32]
    db.commit()
    db.refresh(item)
    return {"ok": True, "emoji": emoji_payload(item, user, user.id)}


@router.delete("/{emoji_id}")
def delete_emoji(
    emoji_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_user),
):
    item = load_emoji(db, emoji_id)
    if item.owner_id != user.id and not user.is_admin:
        raise fail(403, "只能删除自己的表情")
    db.delete(item)
    db.commit()
    return {"ok": True}


@router.post("/{emoji_id}/collect")
def collect_emoji(
    emoji_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_user),
):
    """把别人的表情收藏成自己的一份（类似「偷表情」）。"""
    if not site.get_bool("emoji_enabled", True):
        raise fail(403, "本站已关闭表情包功能")
    source = load_emoji(db, emoji_id)
    if source.owner_id == user.id:
        return {"ok": True, "already": True}
    total = (
        db.scalar(select(func.count()).select_from(models.Emoji).where(models.Emoji.owner_id == user.id)) or 0
    )
    if total >= MAX_EMOJIS:
        raise fail(400, f"最多保存 {MAX_EMOJIS} 个表情")
    item = models.Emoji(owner_id=user.id, name=source.name, url=source.url, origin_id=source.id)
    db.add(item)
    source.use_count = (source.use_count or 0) + 1
    db.commit()
    db.refresh(item)
    audit(db, request, user, "emoji.collect", "emoji", source.id)
    return {"ok": True, "already": False, "emoji": emoji_payload(item, user, user.id)}


@router.post("/{emoji_id}/use")
def touch_emoji(
    emoji_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_user),
):
    """发送时打点，用于热门排序。"""
    item = load_emoji(db, emoji_id)
    item.use_count = (item.use_count or 0) + 1
    db.commit()
    return {"ok": True, "useCount": item.use_count}
