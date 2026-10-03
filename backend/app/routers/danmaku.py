"""弹幕：拉取、发送与删除。"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, settings_store as site
from ..database import get_db
from ..security import current_user, require_user
from ..utils import audit, check_banned_words, fail, iso, rate_limit

router = APIRouter(prefix="/api", tags=["danmaku"])


def danmaku_payload(item: models.Danmaku, db: Session, viewer: Optional[models.User]) -> dict:
    author = db.get(models.User, item.user_id)
    return {
        "id": item.id,
        "content": item.content,
        "time": float(item.time_seconds or 0),
        "color": item.color,
        "mode": item.mode,
        "fontSize": item.font_size,
        "createdAt": iso(item.created_at),
        "author": {
            "id": author.id,
            "username": author.username,
            "displayName": author.display_name or author.username,
            "avatar": author.avatar or "",
        }
        if author
        else None,
        "canDelete": bool(viewer and (viewer.id == item.user_id or viewer.is_admin)),
    }


@router.get("/videos/{video_id}/danmaku")
def list_danmaku(
    video_id: int,
    limit: int = Query(3000),
    db: Session = Depends(get_db),
    viewer: Optional[models.User] = Depends(current_user),
):
    video = db.get(models.Video, video_id)
    if not video:
        raise fail(404, "视频不存在")
    rows = db.scalars(
        select(models.Danmaku)
        .where(models.Danmaku.video_id == video_id, models.Danmaku.is_blocked.is_(False))
        .order_by(models.Danmaku.time_seconds.asc())
        .limit(min(5000, max(100, limit)))
    ).all()
    return {
        "items": [danmaku_payload(item, db, viewer) for item in rows],
        "allowDanmaku": bool(video.allow_danmaku and site.get_bool("enable_danmaku", True)),
    }


@router.post("/videos/{video_id}/danmaku")
def create_danmaku(
    video_id: int,
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_user),
):
    if not site.get_bool("enable_danmaku", True):
        raise fail(403, "本站已关闭弹幕")
    video = db.get(models.Video, video_id)
    if not video or video.deleted_at:
        raise fail(404, "视频不存在")
    if not video.allow_danmaku:
        raise fail(403, "该视频已关闭弹幕")

    content = str(payload.get("content") or "").strip()
    if not content:
        raise fail(400, "弹幕内容不能为空")
    max_len = site.get_int("danmaku_max_length", 60)
    if len(content) > max_len:
        raise fail(400, f"弹幕最多 {max_len} 个字符")
    check_banned_words(content)

    # 限流放在校验之后，避免填错内容也要等冷却
    interval = site.get_int("danmaku_interval", 3)
    if not rate_limit(f"danmaku:{user.id}", interval):
        raise fail(429, f"弹幕发送过于频繁，请 {interval} 秒后再试")

    mode = str(payload.get("mode") or "scroll")
    if mode not in {"scroll", "top", "bottom"}:
        mode = "scroll"
    color = str(payload.get("color") or "#ffffff")[:16]
    if not color.startswith("#"):
        color = "#ffffff"

    item = models.Danmaku(
        video_id=video_id,
        user_id=user.id,
        content=content,
        time_seconds=max(0.0, float(payload.get("time") or 0)),
        color=color,
        mode=mode,
        font_size=max(12, min(40, int(payload.get("font_size") or 25))),
    )
    db.add(item)
    video.danmaku_count += 1
    db.commit()
    db.refresh(item)
    return danmaku_payload(item, db, user)


@router.delete("/danmaku/{danmaku_id}")
def delete_danmaku(
    danmaku_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_user),
):
    item = db.get(models.Danmaku, danmaku_id)
    if not item:
        raise fail(404, "弹幕不存在")
    video = db.get(models.Video, item.video_id)
    if item.user_id != user.id and not user.is_admin and (not video or video.author_id != user.id):
        raise fail(403, "没有权限删除该弹幕")
    db.delete(item)
    if video:
        video.danmaku_count = max(0, video.danmaku_count - 1)
    db.commit()
    audit(db, request, user, "danmaku.delete", "danmaku", danmaku_id)
    return {"ok": True}
