"""直播：开播申请、直播间、聊天与观看人数。"""
from __future__ import annotations

from typing import Optional

import secrets

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import models, realtime, redis_client as redis, settings_store as site
from ..database import get_db
from ..security import current_user, require_admin, require_user
from ..utils import audit, fail, iso, notify, pagination, rate_limit, user_brief, now

router = APIRouter(prefix="/api/live", tags=["live"])
ROOM_TTL = 60


def room_payload(room: models.LiveRoom, db: Session, viewer: Optional[models.User] = None) -> dict:
    owner = db.get(models.User, room.owner_id)
    online = redis.online_count()
    viewers = room.viewer_count
    return {
        "id": room.id,
        "title": room.title,
        "cover": room.cover,
        "description": room.description,
        "status": room.status,
        "categoryId": room.category_id,
        "viewers": viewers,
        "online": online,
        "totalViewers": room.total_viewers,
        "chatCount": room.danmaku_count,
        "startedAt": iso(room.started_at),
        "owner": {
            **(user_brief(owner) or {}),
            "membershipLevel": owner.membership_level if owner else 0,
        },
        "isMine": bool(viewer and owner and viewer.id == owner.id),
        "canManage": bool(viewer and (viewer.id == room.owner_id or viewer.is_admin)),
    }


@router.get("/rooms")
def rooms(
    status: str = Query("live"),
    keyword: str = Query(""),
    page: int = Query(1),
    size: int = Query(0),
    db: Session = Depends(get_db),
    viewer: Optional[models.User] = Depends(current_user),
):
    _, size, limit, offset = pagination(page, size, 24, 60)
    query = select(models.LiveRoom)
    if status and status != "all":
        query = query.where(models.LiveRoom.status == status)
    else:
        query = query.where(models.LiveRoom.status != "banned")
    if keyword:
        query = query.where(models.LiveRoom.title.ilike(f"%{keyword.strip()}%"))
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(
        query.order_by(
            (models.LiveRoom.status == "live").desc(),
            models.LiveRoom.viewer_count.desc(),
            models.LiveRoom.id.desc(),
        )
        .limit(limit)
        .offset(offset)
    ).all()
    return {"items": [room_payload(item, db, viewer) for item in rows], "total": int(total), "page": page, "size": size}


@router.get("/mine")
def my_room(user: models.User = Depends(require_user), db: Session = Depends(get_db)):
    room = db.scalar(select(models.LiveRoom).where(models.LiveRoom.owner_id == user.id))
    if not room:
        return {"room": None, "canLive": bool(user.can_live or user.is_admin)}
    stream_key = room.stream_key or secrets.token_hex(12)
    if not room.stream_key:
        room.stream_key = stream_key
        user.stream_key = stream_key
        db.commit()
    return {
        "room": {**room_payload(room, db, user), "streamKey": stream_key, "playUrl": room.play_url},
        "pushUrl": f"{site.get_str('live_push_base', '').rstrip('/')}/{stream_key}",
        "canLive": bool(user.can_live or user.is_admin),
        "notice": site.get_str("live_notice", ""),
    }


@router.post("/rooms")
def upsert_room(
    payload: dict,
    request: Request,
    user: models.User = Depends(require_user),
    db: Session = Depends(get_db),
):
    if not site.get_bool("live_enabled", True):
        raise fail(403, "本站已关闭直播")
    if not (user.can_live or user.is_admin):
        raise fail(403, "还没有开播权限，请联系管理员开通")

    room = db.scalar(select(models.LiveRoom).where(models.LiveRoom.owner_id == user.id))
    title = str(payload.get("title") or "").strip()
    if not title:
        raise fail(400, "请填写直播间标题")
    if not room:
        room = models.LiveRoom(
            owner_id=user.id,
            title=title[:120],
            stream_key=secrets.token_hex(12),
        )
        user.stream_key = room.stream_key
        db.add(room)
    room.title = title[:120]
    if isinstance(payload.get("cover"), str):
        room.cover = payload["cover"][:500]
    if isinstance(payload.get("description"), str):
        room.description = payload["description"][:1000]
    if payload.get("category_id"):
        room.category_id = int(payload["category_id"])
    if isinstance(payload.get("play_url"), str):
        room.play_url = payload["play_url"][:500]
    db.commit()
    db.refresh(room)
    audit(db, request, user, "live.room_save", "live", room.id)
    return {
        "ok": True,
        "room": {**room_payload(room, db, user), "streamKey": room.stream_key, "playUrl": room.play_url},
        "pushUrl": f"{site.get_str('live_push_base', '').rstrip('/')}/{room.stream_key}",
    }


@router.post("/rooms/{room_id}/status")
async def set_status(
    room_id: int,
    payload: dict,
    request: Request,
    user: models.User = Depends(require_user),
    db: Session = Depends(get_db),
):
    room = db.get(models.LiveRoom, room_id)
    if not room:
        raise fail(404, "直播间不存在")
    if room.owner_id != user.id and not user.is_admin:
        raise fail(403, "没有权限操作该直播间")
    status = str(payload.get("status") or "offline")
    if status not in {"live", "offline"}:
        raise fail(400, "状态不合法")
    if status == "live":
        if room.status == "banned" and not user.is_admin:
            raise fail(403, "该直播间已被封禁")
        room.status = "live"
        room.started_at = room.started_at or now()
        room.ended_at = None
    else:
        room.status = "offline"
        room.ended_at = now()
    db.commit()
    await realtime.broadcast(f"live:{room.id}", {"event": "status", "status": room.status})
    audit(db, request, user, "live.status", "live", room.id, status)
    return {"ok": True, "status": room.status}


@router.get("/rooms/{room_id}")
def room_detail(
    room_id: int,
    db: Session = Depends(get_db),
    viewer: Optional[models.User] = Depends(current_user),
):
    room = db.get(models.LiveRoom, room_id)
    if not room or room.status == "banned":
        raise fail(404, "直播间不存在或已被封禁")
    room.total_viewers += 1
    room.viewer_count = (room.viewer_count or 0) + 1
    db.commit()
    chat = db.scalars(
        select(models.LiveChat)
        .where(models.LiveChat.room_id == room_id)
        .order_by(models.LiveChat.id.desc())
        .limit(50)
    ).all()
    return {
        "room": {**room_payload(room, db, viewer), "playUrl": room.play_url},
        "chat": [
            {
                "id": item.id,
                "content": item.content,
                "createdAt": iso(item.created_at),
                "user": user_brief(db.get(models.User, item.user_id)),
            }
            for item in reversed(list(chat))
        ],
    }


@router.get("/rooms/{room_id}/chat")
def chat_history(room_id: int, db: Session = Depends(get_db)):
    rows = db.scalars(
        select(models.LiveChat).where(models.LiveChat.room_id == room_id).order_by(models.LiveChat.id.desc()).limit(80)
    ).all()
    return {
        "items": [
            {
                "id": item.id,
                "content": item.content,
                "createdAt": iso(item.created_at),
                "user": user_brief(db.get(models.User, item.user_id)),
            }
            for item in reversed(list(rows))
        ]
    }


@router.post("/rooms/{room_id}/chat")
async def send_chat(
    room_id: int,
    payload: dict,
    user: models.User = Depends(require_user),
    db: Session = Depends(get_db),
):
    room = db.get(models.LiveRoom, room_id)
    if not room or room.status == "banned":
        raise fail(404, "直播间不存在")
    interval = site.get_int("live_chat_interval", 2)
    if not rate_limit(f"live-chat:{user.id}", interval):
        raise fail(429, "发言过于频繁")
    content = str(payload.get("content") or "").strip()
    if not content:
        raise fail(400, "内容不能为空")
    limit = site.get_int("live_chat_max_length", 100)
    if len(content) > limit:
        raise fail(400, f"最多 {limit} 个字符")

    item = models.LiveChat(room_id=room_id, user_id=user.id, content=content)
    db.add(item)
    room.danmaku_count += 1
    db.commit()
    db.refresh(item)
    message = {
        "event": "chat",
        "id": item.id,
        "content": content,
        "createdAt": iso(item.created_at),
        "user": user_brief(user),
    }
    await realtime.broadcast(f"live:{room_id}", message)
    return message


@router.delete("/rooms/{room_id}")
def delete_room(room_id: int, request: Request, admin: models.User = Depends(require_admin), db: Session = Depends(get_db)):
    room = db.get(models.LiveRoom, room_id)
    if not room:
        raise fail(404, "直播间不存在")
    db.query(models.LiveChat).filter(models.LiveChat.room_id == room_id).delete()
    db.delete(room)
    db.commit()
    audit(db, request, admin, "admin.live_delete", "live", room_id)
    return {"ok": True}


@router.get("/admin/rooms")
def admin_rooms(
    status: str = Query(""),
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    query = select(models.LiveRoom)
    if status:
        query = query.where(models.LiveRoom.status == status)
    rows = db.scalars(query.order_by(models.LiveRoom.id.desc()).limit(200)).all()
    return {"items": [room_payload(item, db) for item in rows]}


@router.post("/admin/rooms/{room_id}/status")
def admin_set_status(
    room_id: int,
    payload: dict,
    request: Request,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    room = db.get(models.LiveRoom, room_id)
    if not room:
        raise fail(404, "直播间不存在")
    status = str(payload.get("status") or "offline")
    if status not in {"live", "offline", "banned"}:
        raise fail(400, "状态不合法")
    room.status = status
    if status == "offline":
        room.ended_at = now()
    db.commit()
    notify(
        db, room.owner_id, "system", "直播间状态已变更",
        f"管理员将你的直播间状态调整为「{status}」。", ref_type="live", ref_id=room.id,
    )
    audit(db, request, admin, "admin.live_status", "live", room.id, status)
    return {"ok": True, "status": room.status}
