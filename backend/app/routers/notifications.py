"""站内通知。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..security import require_user
from ..utils import iso, pagination, user_brief

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


def payload(item: models.Notification, db: Session) -> dict:
    sender = db.get(models.User, item.from_id) if item.from_id else None
    return {
        "id": item.id,
        "type": item.type,
        "title": item.title,
        "content": item.content,
        "refType": item.ref_type,
        "refId": item.ref_id,
        "isRead": bool(item.is_read),
        "createdAt": iso(item.created_at),
        "from": user_brief(sender),
    }


@router.get("")
def list_notifications(
    page: int = Query(1),
    size: int = Query(0),
    type: str = Query(""),
    unread: int = Query(0),
    db: Session = Depends(get_db),
    user: models.User = Depends(require_user),
):
    _, size, limit, offset = pagination(page, size, 20, 50)
    query = select(models.Notification).where(models.Notification.user_id == user.id)
    if type and type != "all":
        query = query.where(models.Notification.type == type)
    if unread:
        query = query.where(models.Notification.is_read.is_(False))
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(query.order_by(models.Notification.id.desc()).limit(limit).offset(offset)).all()
    counts = dict(
        db.execute(
            select(models.Notification.type, func.count(models.Notification.id))
            .where(models.Notification.user_id == user.id, models.Notification.is_read.is_(False))
            .group_by(models.Notification.type)
        ).all()
    )
    return {
        "items": [payload(item, db) for item in rows],
        "total": int(total),
        "page": page,
        "size": size,
        "unreadByType": {key: int(value) for key, value in counts.items()},
        "unreadTotal": int(sum(counts.values())),
    }


@router.get("/unread-count")
def unread_count(db: Session = Depends(get_db), user: models.User = Depends(require_user)):
    total = db.scalar(
        select(func.count(models.Notification.id)).where(
            models.Notification.user_id == user.id, models.Notification.is_read.is_(False)
        )
    )
    return {"unread": int(total or 0)}


@router.post("/read")
def mark_read(payload: dict, db: Session = Depends(get_db), user: models.User = Depends(require_user)):
    ids = payload.get("ids")
    if isinstance(ids, list) and ids:
        db.execute(
            update(models.Notification)
            .where(models.Notification.user_id == user.id, models.Notification.id.in_([int(i) for i in ids]))
            .values(is_read=True)
        )
    elif payload.get("all"):
        db.execute(
            update(models.Notification).where(models.Notification.user_id == user.id).values(is_read=True)
        )
    db.commit()
    return {"ok": True}


@router.delete("/{notification_id}")
def delete_notification(
    notification_id: int, db: Session = Depends(get_db), user: models.User = Depends(require_user)
):
    item = db.get(models.Notification, notification_id)
    if item and item.user_id == user.id:
        db.delete(item)
        db.commit()
    return {"ok": True}
