"""评论：发布、回复、点赞、置顶与删除。"""
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
    check_banned_words,
    fail,
    iso,
    notify,
    pagination,
    rate_limit,
    notify_mentions,
    user_brief,
)

router = APIRouter(prefix="/api", tags=["comments"])


def comment_payload(comment: models.Comment, db: Session, viewer: Optional[models.User]) -> dict:
    author = db.get(models.User, comment.user_id)
    liked = False
    if viewer:
        liked = bool(db.get(models.CommentLike, {"comment_id": comment.id, "user_id": viewer.id}))
    return {
        "id": comment.id,
        "content": comment.content,
        "likeCount": comment.like_count,
        "replyCount": comment.reply_count,
        "isPinned": bool(comment.is_pinned),
        "parentId": comment.parent_id,
        "createdAt": iso(comment.created_at),
        "liked": liked,
        "author": user_brief(author),
        "canDelete": bool(viewer and (viewer.id == comment.user_id or viewer.is_admin)),
    }


@router.get("/videos/{video_id}/comments")
def list_comments(
    video_id: int,
    page: int = Query(1),
    size: int = Query(0),
    sort: str = Query(""),
    parent_id: int = Query(0),
    db: Session = Depends(get_db),
    viewer: Optional[models.User] = Depends(current_user),
):
    video = db.get(models.Video, video_id)
    if not video:
        raise fail(404, "视频不存在")
    _, size, limit, offset = pagination(page, size, site.get_int("comment_page_size", 20), 50)
    order_field = sort or site.get_str("comment_order", "hot")

    base = select(models.Comment).where(
        models.Comment.video_id == video_id, models.Comment.is_deleted.is_(False)
    )
    if parent_id:
        base = base.where(models.Comment.parent_id == parent_id)
    else:
        base = base.where(models.Comment.parent_id.is_(None))

    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    order = (
        (models.Comment.like_count.desc(), models.Comment.id.desc())
        if order_field == "hot"
        else (models.Comment.id.desc(),)
    )
    rows = db.scalars(
        base.order_by(models.Comment.is_pinned.desc(), *order).limit(limit).offset(offset)
    ).all()

    items = []
    for comment in rows:
        data = comment_payload(comment, db, viewer)
        if not parent_id:
            replies = db.scalars(
                select(models.Comment)
                .where(models.Comment.parent_id == comment.id, models.Comment.is_deleted.is_(False))
                .order_by(models.Comment.id.asc())
                .limit(3)
            ).all()
            data["replies"] = [comment_payload(item, db, viewer) for item in replies]
        items.append(data)
    return {
        "items": items,
        "total": int(total),
        "page": page,
        "size": size,
        "allowComment": bool(video.allow_comment),
    }


@router.post("/videos/{video_id}/comments")
def create_comment(
    video_id: int,
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_user),
):
    if not site.get_bool("enable_comment", True):
        raise fail(403, "本站已关闭评论")
    video = db.get(models.Video, video_id)
    if not video or video.deleted_at:
        raise fail(404, "视频不存在")
    if not video.allow_comment:
        raise fail(403, "该视频已关闭评论")

    content = str(payload.get("content") or "").strip()
    if not content:
        raise fail(400, "评论内容不能为空")
    max_len = site.get_int("comment_max_length", 500)
    if len(content) > max_len:
        raise fail(400, f"评论最多 {max_len} 个字符")
    check_banned_words(content)

    # 限流放在校验之后：表单填错不会白等一个冷却时间
    interval = site.get_int("comment_interval", 5)
    if not rate_limit(f"comment:{user.id}", interval):
        raise fail(429, f"评论过于频繁，请 {interval} 秒后再试")

    parent_id = int(payload["parent_id"]) if payload.get("parent_id") else None
    parent = db.get(models.Comment, parent_id) if parent_id else None
    if parent_id and not parent:
        raise fail(404, "要回复的评论不存在")
    if parent and parent.parent_id:
        parent_id = parent.parent_id

    comment = models.Comment(video_id=video_id, user_id=user.id, parent_id=parent_id, content=content)
    db.add(comment)
    video.comments += 1
    if parent_id:
        target = db.get(models.Comment, parent_id)
        if target:
            target.reply_count += 1
    db.commit()
    db.refresh(comment)

    if video.author_id != user.id:
        notify(
            db, video.author_id, "reply", f"{user.display_name or user.username} 评论了你的视频",
            content[:200], from_id=user.id, ref_type="video", ref_id=video.id, setting_key="notify_reply",
        )
    if parent and parent.user_id not in {user.id, video.author_id}:
        notify(
            db, parent.user_id, "reply", f"{user.display_name or user.username} 回复了你",
            content[:200], from_id=user.id, ref_type="video", ref_id=video.id, setting_key="notify_reply",
        )
    notify_mentions(db, content, user, "video", video.id, "评论")
    audit(db, request, user, "comment.create", "comment", comment.id)
    return comment_payload(comment, db, user)


@router.delete("/comments/{comment_id}")
def delete_comment(
    comment_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_user),
):
    comment = db.get(models.Comment, comment_id)
    if not comment or comment.is_deleted:
        raise fail(404, "评论不存在")
    video = db.get(models.Video, comment.video_id)
    if comment.user_id != user.id and not user.is_admin and (not video or video.author_id != user.id):
        raise fail(403, "没有权限删除该评论")
    comment.is_deleted = True
    if video:
        video.comments = max(0, video.comments - 1)
    if comment.parent_id:
        parent = db.get(models.Comment, comment.parent_id)
        if parent:
            parent.reply_count = max(0, parent.reply_count - 1)
    db.commit()
    audit(db, request, user, "comment.delete", "comment", comment.id)
    return {"ok": True}


@router.post("/comments/{comment_id}/like")
def like_comment(
    comment_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_user),
):
    comment = db.get(models.Comment, comment_id)
    if not comment or comment.is_deleted:
        raise fail(404, "评论不存在")
    existing = db.get(models.CommentLike, {"comment_id": comment_id, "user_id": user.id})
    if existing:
        db.delete(existing)
        comment.like_count = max(0, comment.like_count - 1)
        db.commit()
        return {"liked": False, "likeCount": comment.like_count}
    db.add(models.CommentLike(comment_id=comment_id, user_id=user.id))
    comment.like_count += 1
    db.commit()
    if comment.user_id != user.id:
        notify(
            db, comment.user_id, "like", f"{user.display_name or user.username} 点赞了你的评论",
            comment.content[:120], from_id=user.id, ref_type="comment", ref_id=comment.id,
            setting_key="notify_like",
        )
    return {"liked": True, "likeCount": comment.like_count}


@router.post("/comments/{comment_id}/pin")
def pin_comment(
    comment_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_user),
):
    comment = db.get(models.Comment, comment_id)
    if not comment:
        raise fail(404, "评论不存在")
    video = db.get(models.Video, comment.video_id)
    if not video or (video.author_id != user.id and not user.is_admin):
        raise fail(403, "只有 UP 主可以置顶评论")
    comment.is_pinned = not comment.is_pinned
    db.commit()
    audit(db, request, user, "comment.pin", "comment", comment.id, comment.is_pinned)
    return {"isPinned": bool(comment.is_pinned)}
