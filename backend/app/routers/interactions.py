"""点赞、投币、收藏、稍后再看与播放进度。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..security import require_user
from ..utils import audit, fail, iso, notify, now, tag_rows, video_brief

router = APIRouter(prefix="/api", tags=["interactions"])


def get_video(db: Session, video_id: int) -> models.Video:
    video = db.get(models.Video, video_id)
    if not video or video.deleted_at:
        raise fail(404, "视频不存在")
    return video


@router.post("/videos/{video_id}/like")
def toggle_like(
    video_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_user),
):
    video = get_video(db, video_id)
    existing = db.get(models.VideoLike, {"video_id": video_id, "user_id": user.id})
    author = db.get(models.User, video.author_id)
    if existing:
        db.delete(existing)
        video.likes = max(0, video.likes - 1)
        if author:
            author.like_count = max(0, author.like_count - 1)
        db.commit()
        return {"liked": False, "likes": video.likes}

    db.add(models.VideoLike(video_id=video_id, user_id=user.id))
    video.likes += 1
    if author:
        author.like_count += 1
    db.commit()
    if video.author_id != user.id:
        notify(
            db, video.author_id, "like", f"{user.display_name or user.username} 点赞了你的视频",
            video.title, from_id=user.id, ref_type="video", ref_id=video.id, setting_key="notify_like",
        )
    audit(db, request, user, "video.like", "video", video.id)
    return {"liked": True, "likes": video.likes}


@router.post("/videos/{video_id}/coin")
def give_coin(
    video_id: int,
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_user),
):
    video = get_video(db, video_id)
    amount = max(1, min(2, int(payload.get("amount") or 1)))
    existing = db.get(models.VideoCoin, {"video_id": video_id, "user_id": user.id})
    already = existing.amount if existing else 0
    if already >= 2:
        raise fail(400, "已经投过 2 个硬币了")
    amount = min(amount, 2 - already)
    if user.coins < amount:
        raise fail(400, "硬币不足")

    user.coins -= amount
    if existing:
        existing.amount += amount
    else:
        db.add(models.VideoCoin(video_id=video_id, user_id=user.id, amount=amount))
    video.coins += amount
    db.commit()
    if video.author_id != user.id:
        notify(
            db, video.author_id, "coin",
            f"{user.display_name or user.username} 给你的视频投了 {amount} 个硬币",
            video.title, from_id=user.id, ref_type="video", ref_id=video.id, setting_key="notify_coin",
        )
    audit(db, request, user, "video.coin", "video", video.id, amount)
    return {"coins": video.coins, "myCoins": user.coins, "given": already + amount}


@router.post("/videos/{video_id}/favorite")
def toggle_favorite(
    video_id: int,
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_user),
):
    video = get_video(db, video_id)
    folder_id = int(payload.get("folder_id") or 0)
    folder = db.get(models.FavoriteFolder, folder_id) if folder_id else None
    if not folder or folder.user_id != user.id:
        folder = db.scalar(
            select(models.FavoriteFolder)
            .where(models.FavoriteFolder.user_id == user.id)
            .order_by(models.FavoriteFolder.is_default.desc(), models.FavoriteFolder.id.asc())
        )
    if not folder:
        folder = models.FavoriteFolder(user_id=user.id, name="默认收藏夹", is_default=True)
        db.add(folder)
        db.commit()
        db.refresh(folder)

    existing = db.get(models.FavoriteItem, {"folder_id": folder.id, "video_id": video_id})
    if existing:
        db.delete(existing)
        folder.item_count = max(0, folder.item_count - 1)
        db.commit()
        still = db.scalar(
            select(models.FavoriteItem.folder_id)
            .join(models.FavoriteFolder, models.FavoriteFolder.id == models.FavoriteItem.folder_id)
            .where(models.FavoriteFolder.user_id == user.id, models.FavoriteItem.video_id == video_id)
        )
        if not still:
            video.favorites = max(0, video.favorites - 1)
            db.commit()
        return {"favorited": False, "favorites": video.favorites, "folderId": folder.id}

    db.add(models.FavoriteItem(folder_id=folder.id, video_id=video_id))
    folder.item_count += 1
    video.favorites += 1
    db.commit()
    audit(db, request, user, "video.favorite", "video", video.id, folder.id)
    return {"favorited": True, "favorites": video.favorites, "folderId": folder.id}


@router.post("/videos/{video_id}/watch-later")
def toggle_watch_later(
    video_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_user),
):
    get_video(db, video_id)
    existing = db.get(models.WatchLater, {"user_id": user.id, "video_id": video_id})
    if existing:
        db.delete(existing)
        db.commit()
        return {"watchLater": False}
    db.add(models.WatchLater(user_id=user.id, video_id=video_id))
    db.commit()
    return {"watchLater": True}


@router.post("/videos/{video_id}/progress")
def save_progress(
    video_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_user),
):
    video = get_video(db, video_id)
    progress = max(0, int(payload.get("progress") or 0))
    duration = max(0, int(payload.get("duration") or video.duration or 0))
    row = db.get(models.WatchHistory, {"user_id": user.id, "video_id": video_id})
    if row:
        row.progress = progress
        row.duration = duration or row.duration
        row.updated_at = now()
    else:
        db.add(
            models.WatchHistory(user_id=user.id, video_id=video_id, progress=progress, duration=duration)
        )
    if duration and not video.duration:
        video.duration = duration
    db.commit()
    return {"ok": True}


@router.get("/me/watch-later")
def my_watch_later(db: Session = Depends(get_db), user: models.User = Depends(require_user)):
    rows = db.scalars(
        select(models.Video)
        .join(models.WatchLater, models.WatchLater.video_id == models.Video.id)
        .where(models.WatchLater.user_id == user.id, models.Video.deleted_at.is_(None))
        .order_by(models.WatchLater.created_at.desc())
    ).all()
    ids = [item.id for item in rows]
    tags = tag_rows(db, ids)
    return {"items": [video_brief(item, tags.get(item.id)) for item in rows]}


@router.get("/me/favorite-folders")
def my_folders(db: Session = Depends(get_db), user: models.User = Depends(require_user)):
    rows = db.scalars(
        select(models.FavoriteFolder)
        .where(models.FavoriteFolder.user_id == user.id)
        .order_by(models.FavoriteFolder.is_default.desc(), models.FavoriteFolder.id.asc())
    ).all()
    return {
        "items": [
            {
                "id": item.id,
                "name": item.name,
                "description": item.description,
                "isPublic": bool(item.is_public),
                "isDefault": bool(item.is_default),
                "count": item.item_count,
                "createdAt": iso(item.created_at),
            }
            for item in rows
        ]
    }


@router.post("/me/favorite-folders")
def create_folder(
    payload: dict,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_user),
):
    name = str(payload.get("name") or "").strip()
    if not name:
        raise fail(400, "请填写收藏夹名称")
    folder = models.FavoriteFolder(
        user_id=user.id,
        name=name[:32],
        description=str(payload.get("description") or "")[:200],
        is_public=bool(payload.get("is_public", True)),
    )
    db.add(folder)
    db.commit()
    db.refresh(folder)
    return {"ok": True, "id": folder.id}


@router.put("/me/favorite-folders/{folder_id}")
def update_folder(
    folder_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_user),
):
    folder = db.get(models.FavoriteFolder, folder_id)
    if not folder or folder.user_id != user.id:
        raise fail(404, "收藏夹不存在")
    if isinstance(payload.get("name"), str) and payload["name"].strip():
        folder.name = payload["name"].strip()[:32]
    if isinstance(payload.get("description"), str):
        folder.description = payload["description"][:200]
    if isinstance(payload.get("is_public"), bool):
        folder.is_public = payload["is_public"]
    db.commit()
    return {"ok": True}


@router.delete("/me/favorite-folders/{folder_id}")
def delete_folder(
    folder_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_user),
):
    folder = db.get(models.FavoriteFolder, folder_id)
    if not folder or folder.user_id != user.id:
        raise fail(404, "收藏夹不存在")
    if folder.is_default:
        raise fail(400, "默认收藏夹不能删除")
    for item in db.scalars(
        select(models.FavoriteItem).where(models.FavoriteItem.folder_id == folder_id)
    ).all():
        video = db.get(models.Video, item.video_id)
        if video:
            video.favorites = max(0, video.favorites - 1)
    db.delete(folder)
    db.commit()
    return {"ok": True}
