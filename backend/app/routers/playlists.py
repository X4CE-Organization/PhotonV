"""合集 / 播放列表：创建、管理、按顺序播放。"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import models, settings_store as site
from ..database import get_db
from ..security import current_user, require_user
from ..utils import audit, fail, iso, tag_rows, user_brief, viewer_flags, video_brief

router = APIRouter(prefix="/api", tags=["playlists"])

MAX_PLAYLISTS = 100
MAX_ITEMS = 500


def playlist_payload(item: models.Playlist, owner: Optional[models.User], viewer_id: Optional[int]) -> dict:
    return {
        "id": item.id,
        "title": item.title,
        "description": item.description or "",
        "cover": item.cover or "",
        "isPublic": bool(item.is_public),
        "videoCount": item.video_count,
        "createdAt": iso(item.created_at),
        "owner": user_brief(owner),
        "isMine": bool(viewer_id and item.user_id == viewer_id),
    }


def load_playlist(
    db: Session, playlist_id: int, viewer: Optional[models.User], need_owner: bool = False
) -> models.Playlist:
    item = db.get(models.Playlist, playlist_id)
    if not item:
        raise fail(404, "合集不存在")
    if need_owner:
        if not viewer or item.user_id != viewer.id:
            raise fail(403, "只能管理自己的合集")
        return item
    if not item.is_public and (not viewer or viewer.id != item.user_id):
        raise fail(404, "合集不存在")
    return item


def items_of(db: Session, playlist_id: int, viewer: Optional[models.User]) -> list[dict]:
    rows = db.scalars(
        select(models.Video)
        .join(models.PlaylistItem, models.PlaylistItem.video_id == models.Video.id)
        .where(models.PlaylistItem.playlist_id == playlist_id)
        .order_by(models.PlaylistItem.order_no.asc(), models.PlaylistItem.created_at.asc())
    ).all()
    visible = [
        row
        for row in rows
        if not row.deleted_at
        and (
            row.status == "published"
            or (viewer and viewer.id == row.author_id)
            or (viewer and viewer.is_admin)
        )
    ]
    ids = [row.id for row in visible]
    tags = tag_rows(db, ids)
    flags = viewer_flags(db, ids, viewer)
    # 带上 source / sourceUrl，合集页才能直接播放
    return [video_brief(row, tags.get(row.id), flags.get(row.id), with_description=True) for row in visible]


@router.get("/playlists/mine")
def my_playlists(user: models.User = Depends(require_user), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(models.Playlist).where(models.Playlist.user_id == user.id).order_by(models.Playlist.id.desc())
    ).all()
    return {"items": [playlist_payload(row, user, user.id) for row in rows]}


@router.get("/playlists/with-video/{video_id}")
def playlists_with_video(
    video_id: int,
    user: models.User = Depends(require_user),
    db: Session = Depends(get_db),
):
    """当前用户的合集里，哪些已经包含这个视频（视频页勾选用）。"""
    rows = db.scalars(
        select(models.Playlist).where(models.Playlist.user_id == user.id).order_by(models.Playlist.id.desc())
    ).all()
    contained = {
        row.video_id
        for row in db.scalars(select(models.PlaylistItem).where(models.PlaylistItem.video_id == video_id)).all()
    }
    return {
        "items": [{**playlist_payload(row, user, user.id), "contains": row.id in contained} for row in rows]
    }


@router.post("/playlists")
def create_playlist(
    payload: dict,
    request: Request,
    user: models.User = Depends(require_user),
    db: Session = Depends(get_db),
):
    if not site.get_bool("playlist_enabled", True):
        raise fail(403, "本站已关闭合集功能")
    title = str(payload.get("title") or "").strip()
    if not title:
        raise fail(400, "请填写合集标题")
    if len(title) > 60:
        raise fail(400, "合集标题最多 60 个字符")
    total = (
        db.scalar(select(func.count()).select_from(models.Playlist).where(models.Playlist.user_id == user.id)) or 0
    )
    if total >= MAX_PLAYLISTS:
        raise fail(400, f"最多创建 {MAX_PLAYLISTS} 个合集")
    item = models.Playlist(
        user_id=user.id,
        title=title,
        description=str(payload.get("description") or "")[:500],
        cover=str(payload.get("cover") or "")[:500],
        is_public=bool(payload.get("is_public", True)),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    audit(db, request, user, "playlist.create", "playlist", item.id, title)
    return {"ok": True, "playlist": playlist_payload(item, user, user.id)}


@router.put("/playlists/{playlist_id}")
def update_playlist(
    playlist_id: int,
    payload: dict,
    request: Request,
    user: models.User = Depends(require_user),
    db: Session = Depends(get_db),
):
    item = load_playlist(db, playlist_id, user, need_owner=True)
    if isinstance(payload.get("title"), str) and payload["title"].strip():
        item.title = payload["title"].strip()[:60]
    if isinstance(payload.get("description"), str):
        item.description = payload["description"][:500]
    if isinstance(payload.get("cover"), str):
        item.cover = payload["cover"][:500]
    if isinstance(payload.get("is_public"), bool):
        item.is_public = payload["is_public"]
    db.commit()
    db.refresh(item)
    audit(db, request, user, "playlist.update", "playlist", item.id)
    return {"ok": True, "playlist": playlist_payload(item, user, user.id)}


@router.delete("/playlists/{playlist_id}")
def delete_playlist(
    playlist_id: int,
    request: Request,
    user: models.User = Depends(require_user),
    db: Session = Depends(get_db),
):
    item = load_playlist(db, playlist_id, user, need_owner=True)
    db.delete(item)
    db.commit()
    audit(db, request, user, "playlist.delete", "playlist", playlist_id)
    return {"ok": True}


@router.get("/playlists/{playlist_id}")
def playlist_detail(
    playlist_id: int,
    db: Session = Depends(get_db),
    viewer: Optional[models.User] = Depends(current_user),
):
    item = load_playlist(db, playlist_id, viewer)
    owner = db.get(models.User, item.user_id)
    return {
        "playlist": playlist_payload(item, owner, viewer.id if viewer else None),
        "items": items_of(db, playlist_id, viewer),
    }


@router.post("/playlists/{playlist_id}/items")
def add_item(
    playlist_id: int,
    payload: dict,
    request: Request,
    user: models.User = Depends(require_user),
    db: Session = Depends(get_db),
):
    item = load_playlist(db, playlist_id, user, need_owner=True)
    video_id = int(payload.get("video_id") or 0)
    video = db.get(models.Video, video_id)
    if not video or video.deleted_at:
        raise fail(404, "视频不存在")
    existing = db.get(models.PlaylistItem, {"playlist_id": item.id, "video_id": video_id})
    if existing:
        return {"ok": True, "already": True, "videoCount": item.video_count}
    if item.video_count >= MAX_ITEMS:
        raise fail(400, f"单个合集最多 {MAX_ITEMS} 个视频")
    current_max = (
        db.scalar(select(func.max(models.PlaylistItem.order_no)).where(models.PlaylistItem.playlist_id == item.id))
        or 0
    )
    order_no = int(current_max) + 1
    db.add(models.PlaylistItem(playlist_id=item.id, video_id=video_id, order_no=order_no))
    item.video_count = (item.video_count or 0) + 1
    if not item.cover:
        item.cover = video.cover or ""
    db.commit()
    audit(db, request, user, "playlist.add", "playlist", item.id, str(video_id))
    return {"ok": True, "already": False, "videoCount": item.video_count, "orderNo": order_no}


@router.delete("/playlists/{playlist_id}/items/{video_id}")
def remove_item(
    playlist_id: int,
    video_id: int,
    request: Request,
    user: models.User = Depends(require_user),
    db: Session = Depends(get_db),
):
    item = load_playlist(db, playlist_id, user, need_owner=True)
    existing = db.get(models.PlaylistItem, {"playlist_id": item.id, "video_id": video_id})
    if existing:
        db.delete(existing)
        item.video_count = max(0, (item.video_count or 0) - 1)
        db.commit()
    audit(db, request, user, "playlist.remove", "playlist", item.id, str(video_id))
    return {"ok": True, "videoCount": item.video_count}


@router.post("/playlists/{playlist_id}/reorder")
def reorder_items(
    playlist_id: int,
    payload: dict,
    user: models.User = Depends(require_user),
    db: Session = Depends(get_db),
):
    item = load_playlist(db, playlist_id, user, need_owner=True)
    order = payload.get("video_ids")
    if not isinstance(order, list):
        raise fail(400, "缺少排序列表")
    rows = {
        row.video_id: row
        for row in db.scalars(
            select(models.PlaylistItem).where(models.PlaylistItem.playlist_id == item.id)
        ).all()
    }
    for index, raw in enumerate(order):
        try:
            row = rows.get(int(raw))
        except (TypeError, ValueError):
            continue
        if row:
            row.order_no = index + 1
    db.commit()
    return {"ok": True}


@router.get("/users/{username}/playlists")
def user_playlists(
    username: str,
    db: Session = Depends(get_db),
    viewer: Optional[models.User] = Depends(current_user),
):
    owner = db.scalar(select(models.User).where(models.User.username == username))
    if not owner:
        raise fail(404, "用户不存在")
    query = select(models.Playlist).where(models.Playlist.user_id == owner.id)
    if not viewer or viewer.id != owner.id:
        query = query.where(models.Playlist.is_public.is_(True))
    rows = db.scalars(query.order_by(models.Playlist.id.desc())).all()
    return {"items": [playlist_payload(row, owner, viewer.id if viewer else None) for row in rows]}
