"""用户主页、关注、收藏夹与播放历史。"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import models, settings_store as site
from ..database import get_db
from ..security import current_user, require_user
from ..utils import (
    audit,
    fail,
    iso,
    level_progress,
    notify,
    pagination,
    tag_rows,
    user_brief,
    viewer_flags,
    video_brief,
)

router = APIRouter(prefix="/api/users", tags=["users"])


def find_user(db: Session, username: str) -> models.User:
    user = db.scalar(select(models.User).where(models.User.username == username))
    if not user:
        raise fail(404, "用户不存在")
    return user


@router.get("/{username}")
def profile(username: str, db: Session = Depends(get_db), viewer: Optional[models.User] = Depends(current_user)):
    user = find_user(db, username)
    is_following = False
    if viewer and viewer.id != user.id:
        is_following = bool(
            db.get(models.Follow, {"follower_id": viewer.id, "followee_id": user.id})
        )
    public_videos = db.scalar(
        select(func.count(models.Video.id)).where(
            models.Video.author_id == user.id,
            models.Video.status == "published",
            models.Video.deleted_at.is_(None),
        )
    )
    total_views = db.scalar(
        select(func.coalesce(func.sum(models.Video.views), 0)).where(
            models.Video.author_id == user.id, models.Video.deleted_at.is_(None)
        )
    )
    return {
        "profile": {
            "id": user.id,
            "username": user.username,
            "displayName": user.display_name or user.username,
            "avatar": user.avatar or "",
            "banner": user.banner or "",
            "bio": user.bio or "",
            "gender": user.gender,
            "level": user.level,
            "exp": user.exp,
            "role": user.role if (viewer and viewer.is_admin) or viewer == user else "user",
            "followers": user.follower_count,
            "following": user.following_count,
            "videoCount": int(public_videos or 0),
            "playCount": int(total_views or 0),
            "likeCount": user.like_count,
            "joinedAt": iso(user.created_at),
            "isPrivate": user.is_private,
            "showEmail": user.show_email,
            "email": user.email if user.show_email else "",
        },
        "level": level_progress(user),
        "isFollowing": is_following,
        "isSelf": bool(viewer and viewer.id == user.id),
    }


@router.get("/{username}/videos")
def user_videos(
    username: str,
    page: int = Query(1),
    size: int = Query(0),
    status: str = Query("published"),
    db: Session = Depends(get_db),
    viewer: Optional[models.User] = Depends(current_user),
):
    user = find_user(db, username)
    _, size, limit, offset = pagination(page, size, site.get_int("video_page_size", 24), 60)
    query = select(models.Video).where(models.Video.author_id == user.id, models.Video.deleted_at.is_(None))
    if viewer and viewer.id == user.id and status in {"all", "pending", "private", "rejected", "published"}:
        if status != "all":
            query = query.where(models.Video.status == status)
    else:
        query = query.where(models.Video.status == "published")

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(
        query.order_by(models.Video.is_pinned.desc(), models.Video.id.desc()).limit(limit).offset(offset)
    ).all()
    ids = [item.id for item in rows]
    tags = tag_rows(db, ids)
    flags = viewer_flags(db, ids, viewer)
    return {
        "items": [video_brief(item, tags.get(item.id), flags.get(item.id)) for item in rows],
        "total": int(total),
        "page": page,
        "size": size,
    }


@router.get("/{username}/followers")
def followers(username: str, page: int = Query(1), size: int = Query(0), db: Session = Depends(get_db)):
    user = find_user(db, username)
    _, size, limit, offset = pagination(page, size, 24, 60)
    total = db.scalar(select(func.count()).select_from(models.Follow).where(models.Follow.followee_id == user.id)) or 0
    rows = db.execute(
        select(models.User)
        .join(models.Follow, models.Follow.follower_id == models.User.id)
        .where(models.Follow.followee_id == user.id)
        .order_by(models.Follow.created_at.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return {"items": [user_brief(row[0]) for row in rows], "total": int(total), "page": page, "size": size}


@router.get("/{username}/following")
def following(username: str, page: int = Query(1), size: int = Query(0), db: Session = Depends(get_db)):
    user = find_user(db, username)
    _, size, limit, offset = pagination(page, size, 24, 60)
    total = db.scalar(select(func.count()).select_from(models.Follow).where(models.Follow.follower_id == user.id)) or 0
    rows = db.execute(
        select(models.User)
        .join(models.Follow, models.Follow.followee_id == models.User.id)
        .where(models.Follow.follower_id == user.id)
        .order_by(models.Follow.created_at.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return {"items": [user_brief(row[0]) for row in rows], "total": int(total), "page": page, "size": size}


@router.post("/{username}/follow")
def toggle_follow(
    username: str,
    request: Request,
    db: Session = Depends(get_db),
    viewer: models.User = Depends(require_user),
):
    if not site.get_bool("allow_follow", True):
        raise fail(403, "本站已关闭关注功能")
    target = find_user(db, username)
    if target.id == viewer.id:
        raise fail(400, "不能关注自己")
    existing = db.get(models.Follow, {"follower_id": viewer.id, "followee_id": target.id})
    if existing:
        db.delete(existing)
        viewer.following_count = max(0, viewer.following_count - 1)
        target.follower_count = max(0, target.follower_count - 1)
        db.commit()
        return {"following": False, "followers": target.follower_count}

    db.add(models.Follow(follower_id=viewer.id, followee_id=target.id))
    viewer.following_count += 1
    target.follower_count += 1
    db.commit()
    notify(
        db, target.id, "follow", f"{viewer.display_name or viewer.username} 关注了你",
        ref_type="user", ref_id=viewer.id, from_id=viewer.id, setting_key="notify_follow",
    )
    audit(db, request, viewer, "user.follow", "user", target.id)
    return {"following": True, "followers": target.follower_count}


@router.get("/{username}/favorites")
def favorites(
    username: str,
    folder: int = Query(0),
    page: int = Query(1),
    size: int = Query(0),
    db: Session = Depends(get_db),
    viewer: Optional[models.User] = Depends(current_user),
):
    user = find_user(db, username)
    if user.is_private and (not viewer or (viewer.id != user.id and not viewer.is_admin)):
        raise fail(403, "该用户的收藏夹未公开")

    folders = db.scalars(
        select(models.FavoriteFolder)
        .where(models.FavoriteFolder.user_id == user.id)
        .order_by(models.FavoriteFolder.is_default.desc(), models.FavoriteFolder.id.asc())
    ).all()
    if viewer is None or viewer.id != user.id:
        public_ids = [item.id for item in folders if item.is_public]
        folders = [item for item in folders if item.id in public_ids]

    folder_data = [
        {
            "id": item.id,
            "name": item.name,
            "description": item.description,
            "isPublic": bool(item.is_public),
            "isDefault": bool(item.is_default),
            "count": item.item_count,
        }
        for item in folders
    ]

    _, size, limit, offset = pagination(page, size, 24, 60)
    folder_id = folder or (folders[0].id if folders else 0)
    items: list[dict] = []
    total = 0
    if folder_id:
        base = (
            select(models.Video)
            .join(models.FavoriteItem, models.FavoriteItem.video_id == models.Video.id)
            .where(models.FavoriteItem.folder_id == folder_id, models.Video.deleted_at.is_(None))
        )
        total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
        rows = db.scalars(base.order_by(models.FavoriteItem.created_at.desc()).limit(limit).offset(offset)).all()
        ids = [item.id for item in rows]
        tags = tag_rows(db, ids)
        flags = viewer_flags(db, ids, viewer)
        items = [video_brief(item, tags.get(item.id), flags.get(item.id)) for item in rows]

    return {
        "folders": folder_data,
        "activeFolder": folder_id,
        "items": items,
        "total": int(total),
        "page": page,
        "size": size,
    }


@router.get("/{username}/history")
def history(
    username: str,
    page: int = Query(1),
    size: int = Query(0),
    db: Session = Depends(get_db),
    viewer: Optional[models.User] = Depends(current_user),
):
    user = find_user(db, username)
    if not viewer or (viewer.id != user.id and not viewer.is_admin):
        raise fail(403, "只能查看自己的播放历史")
    _, size, limit, offset = pagination(page, size, 30, 60)
    base = (
        select(models.Video, models.WatchHistory.progress, models.WatchHistory.updated_at)
        .join(models.WatchHistory, models.WatchHistory.video_id == models.Video.id)
        .where(models.WatchHistory.user_id == user.id, models.Video.deleted_at.is_(None))
    )
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = db.execute(base.order_by(models.WatchHistory.updated_at.desc()).limit(limit).offset(offset)).all()
    ids = [row[0].id for row in rows]
    tags = tag_rows(db, ids)
    flags = viewer_flags(db, ids, viewer)
    items = []
    for video, progress, updated in rows:
        data = video_brief(video, tags.get(video.id), flags.get(video.id))
        data["progress"] = progress
        data["watchedAt"] = iso(updated)
        items.append(data)
    return {"items": items, "total": int(total), "page": page, "size": size}
