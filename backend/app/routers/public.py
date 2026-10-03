"""站点公开接口：设置、首页、分区、标签、搜索与排行榜。"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import func, or_, select, text
from sqlalchemy.orm import Session

from .. import models, redis_client as redis, settings_store as site
from ..database import get_db
from ..security import current_user
from ..utils import iso, pagination, publish_due_videos, tag_rows, user_brief, video_brief, viewer_flags

router = APIRouter(prefix="/api", tags=["public"])


def decorate(db: Session, rows: list[models.Video], viewer: Optional[models.User]) -> list[dict]:
    ids = [item.id for item in rows]
    tags = tag_rows(db, ids)
    flags = viewer_flags(db, ids, viewer)
    return [video_brief(item, tags.get(item.id), flags.get(item.id)) for item in rows]


@router.get("/settings")
def public_settings():
    return {"settings": site.public_settings()}


@router.get("/meta")
def meta(db: Session = Depends(get_db)):
    ttl = site.get_int("cache_meta_seconds", 60)
    if ttl:
        cached = redis.cache_get("photonv:cache:meta")
        if cached:
            return cached
    categories = db.scalars(
        select(models.Category).where(models.Category.is_active.is_(True)).order_by(models.Category.sort.asc())
    ).all()
    hot_tags = db.scalars(select(models.Tag).order_by(models.Tag.use_count.desc()).limit(24)).all()
    payload = {
        "settings": site.public_settings(),
        "categories": [
            {"id": item.id, "slug": item.slug, "name": item.name, "icon": item.icon,
             "description": item.description}
            for item in categories
        ],
        "hotTags": [{"id": item.id, "name": item.name, "color": item.color, "count": item.use_count} for item in hot_tags],
    }
    if ttl:
        redis.cache_set("photonv:cache:meta", payload, ttl)
    return payload


@router.get("/home")
def home(db: Session = Depends(get_db), viewer: Optional[models.User] = Depends(current_user)):
    publish_due_videos(db)
    ttl = site.get_int("cache_home_seconds", 10)
    anonymous = viewer is None
    if ttl and anonymous:
        cached = redis.cache_get("photonv:cache:home")
        if cached:
            return cached
    recommend_count = site.get_int("home_recommend_count", 24)
    ranking_size = site.get_int("home_ranking_size", 10)

    carousel = []
    if site.get_bool("show_home_carousel", True):
        carousel = [
            {"id": item.id, "title": item.title, "subtitle": item.subtitle, "image": item.image,
             "link": item.link}
            for item in db.scalars(
                select(models.Carousel)
                .where(models.Carousel.is_active.is_(True))
                .order_by(models.Carousel.sort.asc(), models.Carousel.id.asc())
            ).all()
        ]

    published = select(models.Video).where(
        models.Video.status == "published", models.Video.deleted_at.is_(None)
    )
    featured_rows = db.scalars(
        published.where(models.Video.is_featured.is_(True)).order_by(models.Video.id.desc()).limit(8)
    ).all()
    recommend_rows = db.scalars(
        published.order_by(models.Video.is_pinned.desc(), models.Video.views.desc(), models.Video.id.desc())
        .limit(recommend_count)
    ).all()
    latest_rows = db.scalars(published.order_by(models.Video.id.desc()).limit(12)).all()
    ranking_rows = db.scalars(published.order_by(models.Video.views.desc()).limit(ranking_size)).all()
    like_rows = db.scalars(published.order_by(models.Video.likes.desc()).limit(ranking_size)).all()

    stats = {
        "users": db.scalar(select(func.count(models.User.id))) or 0,
        "videos": db.scalar(
            select(func.count(models.Video.id)).where(models.Video.status == "published")
        )
        or 0,
        "views": db.scalar(select(func.coalesce(func.sum(models.Video.views), 0))) or 0,
        "danmaku": db.scalar(select(func.coalesce(func.sum(models.Video.danmaku_count), 0))) or 0,
        "comments": db.scalar(select(func.count(models.Comment.id))) or 0,
    }

    announcements = [
        {"id": item.id, "title": item.title, "content": item.content, "type": item.type,
         "isPinned": bool(item.is_pinned), "createdAt": iso(item.created_at)}
        for item in db.scalars(
            select(models.Announcement)
            .where(models.Announcement.is_public.is_(True))
            .order_by(models.Announcement.is_pinned.desc(), models.Announcement.id.desc())
            .limit(5)
        ).all()
    ]

    payload = {
        "notice": site.get_str("home_notice", ""),
        "carousel": carousel,
        "stats": stats,
        "featured": decorate(db, featured_rows, viewer),
        "recommend": decorate(db, recommend_rows, viewer),
        "latest": decorate(db, latest_rows, viewer),
        "ranking": decorate(db, ranking_rows, viewer),
        "rankingByLike": decorate(db, like_rows, viewer),
        "announcements": announcements,
        "online": redis.online_count(),
    }
    if ttl and anonymous:
        redis.cache_set("photonv:cache:home", payload, ttl)
    return payload


@router.get("/categories")
def categories(db: Session = Depends(get_db)):
    rows = db.scalars(
        select(models.Category).where(models.Category.is_active.is_(True)).order_by(models.Category.sort.asc())
    ).all()
    counts = dict(
        db.execute(
            select(models.Video.category_id, func.count(models.Video.id))
            .where(models.Video.status == "published", models.Video.deleted_at.is_(None))
            .group_by(models.Video.category_id)
        ).all()
    )
    return {
        "items": [
            {
                "id": item.id,
                "slug": item.slug,
                "name": item.name,
                "icon": item.icon,
                "description": item.description,
                "count": int(counts.get(item.id, 0)),
            }
            for item in rows
        ]
    }


@router.get("/tags")
def tags(limit: int = Query(60), db: Session = Depends(get_db)):
    rows = db.scalars(select(models.Tag).order_by(models.Tag.use_count.desc()).limit(min(200, limit))).all()
    return {"items": [{"id": item.id, "name": item.name, "color": item.color, "count": item.use_count} for item in rows]}


@router.get("/announcements")
def announcements(db: Session = Depends(get_db)):
    rows = db.scalars(
        select(models.Announcement)
        .where(models.Announcement.is_public.is_(True))
        .order_by(models.Announcement.is_pinned.desc(), models.Announcement.id.desc())
        .limit(50)
    ).all()
    return {
        "items": [
            {"id": item.id, "title": item.title, "content": item.content, "type": item.type,
             "isPinned": bool(item.is_pinned), "createdAt": iso(item.created_at)}
            for item in rows
        ]
    }


@router.get("/search")
def search(
    q: str = Query(""),
    type: str = Query("video"),
    page: int = Query(1),
    size: int = Query(0),
    db: Session = Depends(get_db),
    viewer: Optional[models.User] = Depends(current_user),
):
    keyword = q.strip()
    if not keyword:
        _, size, _, _ = pagination(page, size, site.get_int("video_page_size", 24), 60)
        return {"videos": [], "users": [], "total": 0, "page": page, "size": size}
    like = f"%{keyword}%"

    if site.get_bool("search_hot_enabled", True):
        redis.counter_incr(f"search:{keyword[:32]}", 7 * 86400)

    users = [
        user_brief(item)
        for item in db.scalars(
            select(models.User)
            .where(or_(models.User.username.ilike(like), models.User.display_name.ilike(like)))
            .order_by(models.User.follower_count.desc())
            .limit(12)
        ).all()
    ]

    _, size, limit, offset = pagination(page, size, site.get_int("video_page_size", 24), 60)
    query = select(models.Video).where(
        models.Video.status == "published",
        models.Video.deleted_at.is_(None),
        or_(models.Video.title.ilike(like), models.Video.description.ilike(like)),
    )
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(query.order_by(models.Video.views.desc()).limit(limit).offset(offset)).all()
    return {
        "videos": decorate(db, rows, viewer),
        "users": users,
        "total": int(total),
        "page": page,
        "size": size,
    }


@router.get("/search/hot")
def hot_searches(db: Session = Depends(get_db)):
    """热搜词：优先用真实搜索计数，不足时用热度最高的标签补齐。"""
    items: list[dict] = []
    if site.get_bool("search_hot_enabled", True):
        items = redis.top_counters("search:", 10)
    if len(items) < 10:
        taken = {item["keyword"] for item in items}
        rows = db.scalars(select(models.Tag).order_by(models.Tag.use_count.desc()).limit(20)).all()
        for row in rows:
            if row.name in taken:
                continue
            items.append({"keyword": row.name, "count": row.use_count, "source": "tag"})
            if len(items) >= 10:
                break
    return {"items": items[:10]}


@router.get("/rank")
def ranking(
    type: str = Query("views"),
    period: str = Query("all"),
    limit: int = Query(50),
    db: Session = Depends(get_db),
    viewer: Optional[models.User] = Depends(current_user),
):
    publish_due_videos(db)
    limit = min(100, max(5, limit))
    if type == "fans":
        users = db.scalars(
            select(models.User).where(models.User.is_banned.is_(False))
            .order_by(models.User.follower_count.desc()).limit(limit)
        ).all()
        return {
            "type": type,
            "users": [
                {**user_brief(item), "playCount": item.play_count, "likeCount": item.like_count}
                for item in users
            ],
            "items": [],
        }

    query = select(models.Video).where(
        models.Video.status == "published", models.Video.deleted_at.is_(None)
    )
    if period == "week":
        query = query.where(models.Video.created_at >= func.now() - text("interval '7 days'"))
    order = {
        "likes": models.Video.likes.desc(),
        "coins": models.Video.coins.desc(),
        "favorites": models.Video.favorites.desc(),
        "comments": models.Video.comments.desc(),
    }.get(type, models.Video.views.desc())
    rows = db.scalars(query.order_by(order, models.Video.id.desc()).limit(limit)).all()
    return {"type": type, "items": decorate(db, rows, viewer), "users": []}


@router.get("/following-feed")
def following_feed(
    page: int = Query(1),
    size: int = Query(0),
    db: Session = Depends(get_db),
    viewer: Optional[models.User] = Depends(current_user),
):
    if not viewer:
        return {"items": [], "total": 0, "page": page, "size": size}
    _, size, limit, offset = pagination(page, size, 24, 60)
    query = (
        select(models.Video)
        .join(models.Follow, models.Follow.followee_id == models.Video.author_id)
        .where(
            models.Follow.follower_id == viewer.id,
            models.Video.status == "published",
            models.Video.deleted_at.is_(None),
        )
    )
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(query.order_by(models.Video.id.desc()).limit(limit).offset(offset)).all()
    return {"items": decorate(db, rows, viewer), "total": int(total), "page": page, "size": size}
