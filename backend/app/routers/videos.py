"""视频投稿、列表、详情与相关推荐。"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from .. import models, settings_store as site
from ..database import get_db
from ..security import current_user, require_user
from ..utils import (
    audit,
    check_banned_words,
    fail,
    notify,
    pagination,
    rate_limit,
    tag_rows,
    video_brief,
    viewer_flags,
    now,
)

router = APIRouter(prefix="/api/videos", tags=["videos"])


def load_tags(db: Session, names: list[str]) -> list[models.Tag]:
    tags: list[models.Tag] = []
    for raw in names[: site.get_int("video_tags_max", 10)]:
        name = str(raw).strip()[:24]
        if not name:
            continue
        tag = db.scalar(select(models.Tag).where(models.Tag.name == name))
        if not tag:
            tag = models.Tag(name=name)
            db.add(tag)
            db.flush()
        tags.append(tag)
    return tags


def apply_tags(db: Session, video: models.Video, names: list[str]) -> None:
    db.execute(models.VideoTag.__table__.delete().where(models.VideoTag.video_id == video.id))
    for tag in load_tags(db, names):
        db.add(models.VideoTag(video_id=video.id, tag_id=tag.id))
        tag.use_count = (tag.use_count or 0) + 1
    db.commit()


@router.get("")
def list_videos(
    page: int = Query(1),
    size: int = Query(0),
    category: str = Query(""),
    tag: str = Query(""),
    q: str = Query(""),
    sort: str = Query("new"),
    author: str = Query(""),
    db: Session = Depends(get_db),
    viewer: Optional[models.User] = Depends(current_user),
):
    _, size, limit, offset = pagination(page, size, site.get_int("video_page_size", 24), 60)
    query = select(models.Video).where(
        models.Video.status == "published", models.Video.deleted_at.is_(None)
    )
    if category:
        query = query.join(models.Category, models.Category.id == models.Video.category_id).where(
            models.Category.slug == category
        )
    if tag:
        query = (
            query.join(models.VideoTag, models.VideoTag.video_id == models.Video.id)
            .join(models.Tag, models.Tag.id == models.VideoTag.tag_id)
            .where(models.Tag.name == tag)
        )
    if author:
        query = query.join(models.User, models.User.id == models.Video.author_id).where(
            models.User.username == author
        )
    if q:
        like = f"%{q.strip()}%"
        query = query.where(or_(models.Video.title.ilike(like), models.Video.description.ilike(like)))

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    order = {
        "hot": (models.Video.views.desc(), models.Video.id.desc()),
        "like": (models.Video.likes.desc(), models.Video.id.desc()),
        "coin": (models.Video.coins.desc(), models.Video.id.desc()),
        "comment": (models.Video.comments.desc(), models.Video.id.desc()),
    }.get(sort, (models.Video.id.desc(),))
    rows = db.scalars(
        query.order_by(models.Video.is_pinned.desc(), *order).limit(limit).offset(offset)
    ).all()
    ids = [item.id for item in rows]
    tags_map = tag_rows(db, ids)
    flags = viewer_flags(db, ids, viewer)
    return {
        "items": [video_brief(item, tags_map.get(item.id), flags.get(item.id)) for item in rows],
        "total": int(total),
        "page": page,
        "size": size,
    }


@router.get("/{video_id}")
def video_detail(video_id: int, db: Session = Depends(get_db), viewer: Optional[models.User] = Depends(current_user)):
    video = db.get(models.Video, video_id)
    if not video or video.deleted_at:
        raise fail(404, "视频不存在")
    if video.status != "published":
        allowed = viewer and (viewer.id == video.author_id or viewer.is_admin)
        if not allowed:
            raise fail(404, "视频不存在")

    # 播放计数（同一用户重复播放只算一次）
    count_view = True
    if viewer and site.get_bool("view_count_once_per_user", True):
        exists = db.get(models.WatchHistory, {"user_id": viewer.id, "video_id": video.id})
        count_view = exists is None
    if count_view:
        video.views += 1
        author = db.get(models.User, video.author_id)
        if author:
            author.play_count += 1
        if viewer and viewer.id != video.author_id:
            exp = site.get_int("video_exp_per_view", 1)
            if exp and author:
                author.exp += exp
        db.commit()

    tag_list = tag_rows(db, [video.id]).get(video.id, [])
    flags = viewer_flags(db, [video.id], viewer).get(video.id, {})
    data = video_brief(video, tag_list, flags, with_description=True)
    data["category"] = (
        {"id": video.category.id, "slug": video.category.slug, "name": video.category.name}
        if video.category
        else None
    )
    data["canEdit"] = bool(viewer and (viewer.id == video.author_id or viewer.is_admin))
    return data


@router.get("/{video_id}/related")
def related(video_id: int, db: Session = Depends(get_db), viewer: Optional[models.User] = Depends(current_user)):
    video = db.get(models.Video, video_id)
    if not video:
        raise fail(404, "视频不存在")
    query = select(models.Video).where(
        models.Video.status == "published",
        models.Video.deleted_at.is_(None),
        models.Video.id != video.id,
    )
    if video.category_id:
        query = query.where(
            or_(models.Video.category_id == video.category_id, models.Video.author_id == video.author_id)
        )
    rows = db.scalars(query.order_by(models.Video.views.desc()).limit(12)).all()
    ids = [item.id for item in rows]
    tags = tag_rows(db, ids)
    flags = viewer_flags(db, ids, viewer)
    return {"items": [video_brief(item, tags.get(item.id), flags.get(item.id)) for item in rows]}


@router.post("")
def create_video(
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_user),
):
    if not site.get_bool("allow_upload", True):
        raise fail(403, "本站已关闭投稿")
    if user.level < site.get_int("upload_min_level", 0):
        raise fail(403, f"投稿需要达到 Lv{site.get_int('upload_min_level', 0)}")
    interval = site.get_int("video_upload_interval", 60)
    if not rate_limit(f"upload:{user.id}", interval):
        raise fail(429, f"投稿过于频繁，请 {interval} 秒后再试")

    title = str(payload.get("title") or "").strip()
    if len(title) < 2:
        raise fail(400, "标题至少 2 个字符")
    if len(title) > site.get_int("video_title_max", 80):
        raise fail(400, f"标题最多 {site.get_int('video_title_max', 80)} 个字符")
    description = str(payload.get("description") or "")[: site.get_int("video_desc_max", 2000)]
    source = str(payload.get("source") or "").strip()
    source_url = str(payload.get("source_url") or "").strip()
    if not source and not source_url:
        raise fail(400, "请先上传视频文件或填写视频直链")
    if source_url and not site.get_bool("allow_video_url", True):
        raise fail(400, "本站不允许填写外部视频直链")
    check_banned_words(title, description)

    needs_review = site.get_bool("video_need_review", True)
    video = models.Video(
        author_id=user.id,
        title=title,
        description=description,
        cover=str(payload.get("cover") or "")[:500],
        source=source,
        source_url=source_url,
        duration=int(payload.get("duration") or 0),
        filesize=int(payload.get("filesize") or 0),
        width=int(payload.get("width") or 0),
        height=int(payload.get("height") or 0),
        category_id=int(payload["category_id"]) if payload.get("category_id") else None,
        status="pending" if needs_review else "published",
        allow_comment=bool(payload.get("allow_comment", True)),
        allow_danmaku=bool(payload.get("allow_danmaku", True)),
        allow_download=bool(payload.get("allow_download", site.get_bool("allow_download", True))),
        published_at=None if needs_review else now(),
    )
    db.add(video)
    db.commit()
    db.refresh(video)
    if isinstance(payload.get("tags"), list):
        apply_tags(db, video, payload["tags"])
    if not needs_review:
        user.video_count += 1
        db.commit()
    audit(db, request, user, "video.create", "video", video.id, title)
    return {"ok": True, "id": video.id, "status": video.status}


@router.put("/{video_id}")
def update_video(
    video_id: int,
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_user),
):
    video = db.get(models.Video, video_id)
    if not video or video.deleted_at:
        raise fail(404, "视频不存在")
    if video.author_id != user.id and not user.is_admin:
        raise fail(403, "没有权限修改该视频")

    if isinstance(payload.get("title"), str) and payload["title"].strip():
        title = payload["title"].strip()
        if len(title) > site.get_int("video_title_max", 80):
            raise fail(400, "标题过长")
        video.title = title
    if isinstance(payload.get("description"), str):
        video.description = payload["description"][: site.get_int("video_desc_max", 2000)]
    if isinstance(payload.get("cover"), str):
        video.cover = payload["cover"][:500]
    if payload.get("category_id") is not None:
        video.category_id = int(payload["category_id"]) or None
    for field, key in (("allow_comment", "allow_comment"), ("allow_danmaku", "allow_danmaku"),
                       ("allow_download", "allow_download")):
        if isinstance(payload.get(field), bool):
            setattr(video, key, payload[field])
    if isinstance(payload.get("tags"), list):
        apply_tags(db, video, payload["tags"])
    db.commit()
    audit(db, request, user, "video.update", "video", video.id)
    return {"ok": True}


@router.delete("/{video_id}")
def delete_video(
    video_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_user),
):
    video = db.get(models.Video, video_id)
    if not video or video.deleted_at:
        raise fail(404, "视频不存在")
    if video.author_id != user.id and not user.is_admin:
        raise fail(403, "没有权限删除该视频")
    video.deleted_at = now()
    author = db.get(models.User, video.author_id)
    if author and video.status == "published":
        author.video_count = max(0, author.video_count - 1)
    db.commit()
    audit(db, request, user, "video.delete", "video", video.id, video.title)
    return {"ok": True}


@router.post("/{video_id}/visibility")
def set_visibility(
    video_id: int,
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_user),
):
    video = db.get(models.Video, video_id)
    if not video or video.deleted_at:
        raise fail(404, "视频不存在")
    if video.author_id != user.id and not user.is_admin:
        raise fail(403, "没有权限修改该视频")
    status = str(payload.get("status") or "")
    if status not in {"private", "published", "pending"}:
        raise fail(400, "状态不合法")
    if status == "published" and not user.is_admin and site.get_bool("video_need_review", True):
        raise fail(403, "投稿需要管理员审核后才能公开")
    was_published = video.status == "published"
    video.status = status
    if status == "published" and not video.published_at:
        video.published_at = now()
    if status == "published" and not was_published:
        author = db.get(models.User, video.author_id)
        if author:
            author.video_count += 1
    if was_published and status != "published":
        author = db.get(models.User, video.author_id)
        if author:
            author.video_count = max(0, author.video_count - 1)
    db.commit()
    audit(db, request, user, "video.visibility", "video", video.id, status)
    return {"ok": True, "status": video.status}


@router.post("/{video_id}/share")
def share(video_id: int, db: Session = Depends(get_db)):
    video = db.get(models.Video, video_id)
    if not video or video.status != "published":
        raise fail(404, "视频不存在")
    video.shares += 1
    db.commit()
    return {"ok": True, "shares": video.shares}
