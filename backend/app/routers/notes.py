"""视频笔记：按时间点记录，可设为公开让其他人看到。"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, settings_store as site
from ..database import get_db
from ..security import current_user, require_user
from ..utils import audit, check_banned_words, fail, iso, user_brief

router = APIRouter(prefix="/api", tags=["notes"])


def note_payload(item: models.VideoNote, author: Optional[models.User], viewer_id: Optional[int]) -> dict:
    return {
        "id": item.id,
        "videoId": item.video_id,
        "time": round(float(item.time_seconds or 0), 2),
        "content": item.content,
        "isPublic": bool(item.is_public),
        "isMine": bool(viewer_id and item.user_id == viewer_id),
        "createdAt": iso(item.created_at),
        "updatedAt": iso(item.updated_at),
        "author": user_brief(author),
    }


def get_note(db: Session, note_id: int) -> models.VideoNote:
    item = db.get(models.VideoNote, note_id)
    if not item:
        raise fail(404, "笔记不存在")
    return item


@router.get("/videos/{video_id}/notes")
def list_notes(
    video_id: int,
    db: Session = Depends(get_db),
    viewer: Optional[models.User] = Depends(current_user),
):
    if not site.get_bool("video_notes_enabled", True):
        return {"items": [], "enabled": False}
    video = db.get(models.Video, video_id)
    if not video or video.deleted_at:
        raise fail(404, "视频不存在")
    query = select(models.VideoNote).where(models.VideoNote.video_id == video_id)
    if viewer:
        query = query.where(
            (models.VideoNote.is_public.is_(True)) | (models.VideoNote.user_id == viewer.id)
        )
    else:
        query = query.where(models.VideoNote.is_public.is_(True))
    rows = db.scalars(query.order_by(models.VideoNote.time_seconds.asc(), models.VideoNote.id.asc()).limit(500)).all()
    authors = {
        row.id: db.get(models.User, row.user_id)
        for row in rows
    }
    return {
        "enabled": True,
        "items": [note_payload(row, authors.get(row.id), viewer.id if viewer else None) for row in rows],
    }


@router.post("/videos/{video_id}/notes")
def create_note(
    video_id: int,
    payload: dict,
    request: Request,
    user: models.User = Depends(require_user),
    db: Session = Depends(get_db),
):
    if not site.get_bool("video_notes_enabled", True):
        raise fail(403, "本站已关闭视频笔记")
    video = db.get(models.Video, video_id)
    if not video or video.deleted_at:
        raise fail(404, "视频不存在")
    content = str(payload.get("content") or "").strip()
    if not content:
        raise fail(400, "笔记内容不能为空")
    limit = site.get_int("note_max_length", 1000)
    if len(content) > limit:
        raise fail(400, f"笔记最多 {limit} 个字符")
    check_banned_words(content)
    try:
        position = max(0.0, float(payload.get("time") or 0))
    except (TypeError, ValueError):
        position = 0.0
    item = models.VideoNote(
        video_id=video_id,
        user_id=user.id,
        time_seconds=position,
        content=content,
        is_public=bool(payload.get("is_public", True)),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    audit(db, request, user, "note.create", "video", video_id)
    return {"ok": True, "note": note_payload(item, user, user.id)}


@router.put("/notes/{note_id}")
def update_note(
    note_id: int,
    payload: dict,
    request: Request,
    user: models.User = Depends(require_user),
    db: Session = Depends(get_db),
):
    item = get_note(db, note_id)
    if item.user_id != user.id:
        raise fail(403, "只能修改自己的笔记")
    if isinstance(payload.get("content"), str) and payload["content"].strip():
        content = payload["content"].strip()
        limit = site.get_int("note_max_length", 1000)
        if len(content) > limit:
            raise fail(400, f"笔记最多 {limit} 个字符")
        check_banned_words(content)
        item.content = content
    if payload.get("time") is not None:
        try:
            item.time_seconds = max(0.0, float(payload["time"]))
        except (TypeError, ValueError):
            pass
    if isinstance(payload.get("is_public"), bool):
        item.is_public = payload["is_public"]
    db.commit()
    db.refresh(item)
    audit(db, request, user, "note.update", "note", item.id)
    return {"ok": True, "note": note_payload(item, user, user.id)}


@router.delete("/notes/{note_id}")
def delete_note(
    note_id: int,
    request: Request,
    user: models.User = Depends(require_user),
    db: Session = Depends(get_db),
):
    item = get_note(db, note_id)
    if item.user_id != user.id and not user.is_admin:
        raise fail(403, "只能删除自己的笔记")
    db.delete(item)
    db.commit()
    audit(db, request, user, "note.delete", "note", note_id)
    return {"ok": True}


@router.get("/me/notes")
def my_notes(
    db: Session = Depends(get_db),
    user: models.User = Depends(require_user),
):
    rows = db.scalars(
        select(models.VideoNote)
        .where(models.VideoNote.user_id == user.id)
        .order_by(models.VideoNote.id.desc())
        .limit(200)
    ).all()
    videos = {row.video_id: db.get(models.Video, row.video_id) for row in rows}
    return {
        "items": [
            {
                **note_payload(row, user, user.id),
                "video": (
                    {
                        "id": videos[row.video_id].id,
                        "title": videos[row.video_id].title,
                        "cover": videos[row.video_id].cover or "",
                    }
                    if videos.get(row.video_id)
                    else None
                ),
            }
            for row in rows
        ]
    }
