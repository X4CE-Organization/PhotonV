"""WebSocket 实时接口：直播间聊天、私信推送。"""
from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from .. import models, realtime, settings_store as site
from ..database import SessionLocal
from ..security import decode_token
from ..utils import iso, rate_limit, user_brief

router = APIRouter(tags=["realtime"])


def user_from_token(token: str):
    payload = decode_token(token or "")
    if not payload:
        return None
    db = SessionLocal()
    try:
        return db.get(models.User, payload.get("sub"))
    finally:
        db.close()


@router.websocket("/ws/live/{room_id}")
async def live_socket(socket: WebSocket, room_id: int):
    user = user_from_token(socket.query_params.get("token", ""))
    await socket.accept()
    room = f"live:{room_id}"
    await realtime.join_room(room, socket)
    try:
        await socket.send_json({"event": "hello", "room": room_id, "user": user_brief(user)})
        while True:
            payload = await socket.receive_json()
            content = str(payload.get("content") or "").strip()
            if not content or not user:
                continue
            limit = site.get_int("live_chat_max_length", 100)
            if len(content) > limit:
                await socket.send_json({"event": "error", "message": f"最多 {limit} 个字符"})
                continue
            if not rate_limit(f"ws-live:{user.id}", site.get_int("live_chat_interval", 2)):
                await socket.send_json({"event": "error", "message": "发言过于频繁"})
                continue
            db = SessionLocal()
            try:
                item = models.LiveChat(room_id=room_id, user_id=user.id, content=content)
                db.add(item)
                room_row = db.get(models.LiveRoom, room_id)
                if room_row:
                    room_row.danmaku_count += 1
                    room_row.viewer_count = max(room_row.viewer_count, 0)
                db.commit()
                db.refresh(item)
                message = {
                    "event": "chat",
                    "id": item.id,
                    "content": content,
                    "createdAt": iso(item.created_at),
                    "user": user_brief(user),
                }
            finally:
                db.close()
            await realtime.broadcast(room, message)
    except WebSocketDisconnect:
        pass
    except Exception:  # noqa: BLE001
        pass
    finally:
        await realtime.leave_room(room, socket)


@router.websocket("/ws/messages")
async def message_socket(socket: WebSocket):
    user = user_from_token(socket.query_params.get("token", ""))
    await socket.accept()
    if not user:
        await socket.send_json({"event": "error", "message": "未登录"})
        await socket.close()
        return
    await realtime.join_user(user.id, socket)
    db = SessionLocal()
    try:
        unread_rows = db.scalars(
            select(models.Conversation).where(
                (models.Conversation.user_a == user.id) | (models.Conversation.user_b == user.id)
            )
        ).all()
        unread = sum((row.unread_a if row.user_a == user.id else row.unread_b) for row in unread_rows)
    finally:
        db.close()
    try:
        await socket.send_json({"event": "hello", "unread": int(unread)})
        while True:
            await socket.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception:  # noqa: BLE001
        pass
    finally:
        await realtime.leave_user(user.id, socket)
