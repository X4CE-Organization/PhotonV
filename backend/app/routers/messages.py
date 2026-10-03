"""私信：会话列表、聊天记录、发送与未读。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from .. import models, settings_store as site
from ..database import get_db
from ..security import require_user
from ..utils import audit, fail, iso, notify, pagination, rate_limit, user_brief, now

router = APIRouter(prefix="/api/messages", tags=["messages"])


def pair(user_id: int, other_id: int) -> tuple[int, int]:
    return (user_id, other_id) if user_id < other_id else (other_id, user_id)


def conversation_payload(item: models.Conversation, viewer_id: int, db: Session) -> dict:
    other_id = item.user_b if item.user_a == viewer_id else item.user_a
    other = db.get(models.User, other_id)
    unread = item.unread_a if item.user_a == viewer_id else item.unread_b
    return {
        "id": item.id,
        "user": user_brief(other),
        "lastMessage": item.last_message,
        "lastAt": iso(item.last_at),
        "unread": unread,
    }


def message_payload(item: models.DirectMessage, viewer_id: int) -> dict:
    return {
        "id": item.id,
        "content": item.content,
        "createdAt": iso(item.created_at),
        "mine": item.sender_id == viewer_id,
        "isRead": bool(item.is_read),
    }


@router.get("/conversations")
def conversations(user: models.User = Depends(require_user), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(models.Conversation)
        .where(or_(models.Conversation.user_a == user.id, models.Conversation.user_b == user.id))
        .order_by(models.Conversation.last_at.desc())
        .limit(100)
    ).all()
    return {"items": [conversation_payload(item, user.id, db) for item in rows]}


@router.get("/unread")
def unread(user: models.User = Depends(require_user), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(models.Conversation).where(
            or_(models.Conversation.user_a == user.id, models.Conversation.user_b == user.id)
        )
    ).all()
    total = sum((item.unread_a if item.user_a == user.id else item.unread_b) for item in rows)
    return {"unread": int(total)}


@router.get("/{conversation_id}")
def messages(
    conversation_id: int,
    page: int = Query(1),
    size: int = Query(0),
    user: models.User = Depends(require_user),
    db: Session = Depends(get_db),
):
    item = db.get(models.Conversation, conversation_id)
    if not item or user.id not in (item.user_a, item.user_b):
        raise fail(404, "会话不存在")
    _, size, limit, offset = pagination(page, size, 30, 100)
    rows = db.scalars(
        select(models.DirectMessage)
        .where(models.DirectMessage.conversation_id == conversation_id)
        .order_by(models.DirectMessage.id.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    rows = list(reversed(rows))
    # 标记已读
    for row in rows:
        if row.sender_id != user.id and not row.is_read:
            row.is_read = True
    if item.user_a == user.id:
        item.unread_a = 0
    else:
        item.unread_b = 0
    db.commit()
    return {
        "conversation": conversation_payload(item, user.id, db),
        "items": [message_payload(row, user.id) for row in rows],
        "page": page,
        "size": size,
    }


@router.post("")
async def send(
    payload: dict,
    request: Request,
    user: models.User = Depends(require_user),
    db: Session = Depends(get_db),
):
    if not site.get_bool("allow_message", True):
        raise fail(403, "本站已关闭私信")
    if not rate_limit(f"dm:{user.id}", 2):
        raise fail(429, "发送过于频繁，请稍后再试")

    content = str(payload.get("content") or "").strip()
    if not content:
        raise fail(400, "消息不能为空")
    if len(content) > 1000:
        raise fail(400, "消息太长")

    target = None
    if payload.get("to_user_id"):
        target = db.get(models.User, int(payload["to_user_id"]))
    elif payload.get("username"):
        target = db.scalar(select(models.User).where(models.User.username == str(payload["username"])))
    if not target:
        raise fail(404, "对方不存在")
    if target.id == user.id:
        raise fail(400, "不能给自己发私信")
    if not target.allow_message:
        raise fail(403, "对方已关闭私信")

    a, b = pair(user.id, target.id)
    item = db.scalar(
        select(models.Conversation).where(models.Conversation.user_a == a, models.Conversation.user_b == b)
    )
    if not item:
        item = models.Conversation(user_a=a, user_b=b)
        db.add(item)
        db.commit()
        db.refresh(item)

    message = models.DirectMessage(conversation_id=item.id, sender_id=user.id, content=content)
    db.add(message)
    item.last_message = content[:200]
    item.last_at = now()
    if item.user_a == target.id:
        item.unread_a += 1
    else:
        item.unread_b += 1
    db.commit()
    db.refresh(message)
    audit(db, request, user, "message.send", "user", target.id)

    from .. import realtime

    await realtime.send_to_user(
        target.id,
        {
            "event": "message",
            "conversationId": item.id,
            "message": message_payload(message, target.id),
            "from": user_brief(user),
        },
    )
    return {
        "ok": True,
        "conversationId": item.id,
        "message": message_payload(message, user.id),
    }


@router.delete("/{conversation_id}")
def remove(conversation_id: int, user: models.User = Depends(require_user), db: Session = Depends(get_db)):
    item = db.get(models.Conversation, conversation_id)
    if not item or user.id not in (item.user_a, item.user_b):
        raise fail(404, "会话不存在")
    db.query(models.DirectMessage).filter(models.DirectMessage.conversation_id == conversation_id).delete()
    db.delete(item)
    db.commit()
    return {"ok": True}
