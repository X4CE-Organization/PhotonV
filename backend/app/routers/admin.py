"""管理后台：用户、视频审核、评论、分区、举报、设置、日志与备份。"""
from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, or_, select, text
from sqlalchemy.orm import Session

from .. import live_stream, models, realtime, redis_client as redis, settings_store as site, transcode
from ..database import backup_database, delete_backup, get_db, list_backups
from ..security import hash_password, require_admin, require_superadmin
from ..settings_registry import SETTING_GROUPS, SETTINGS
from ..utils import audit, fail, iso, notify, now, pagination, tag_rows, user_brief, video_brief

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _count(db: Session, model, *conditions) -> int:
    query = select(func.count()).select_from(model)
    if conditions:
        query = query.where(*conditions)
    return int(db.scalar(query) or 0)


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db), admin: models.User = Depends(require_admin)):
    week_ago = now() - timedelta(days=7)
    published = models.Video.status == "published"
    trend_rows = db.execute(
        select(
            func.date_trunc("day", models.Video.created_at).label("day"),
            func.count(models.Video.id),
        )
        .where(models.Video.created_at >= now() - timedelta(days=13))
        .group_by(text("day"))
        .order_by(text("day"))
    ).all()
    return {
        "users": {
            "total": _count(db, models.User),
            "newWeek": _count(db, models.User, models.User.created_at >= week_ago),
            "banned": _count(db, models.User, models.User.is_banned.is_(True)),
            "admins": _count(db, models.User, models.User.role != "user"),
        },
        "videos": {
            "total": _count(db, models.Video, models.Video.deleted_at.is_(None)),
            "published": _count(db, models.Video, published, models.Video.deleted_at.is_(None)),
            "pending": _count(db, models.Video, models.Video.status == "pending", models.Video.deleted_at.is_(None)),
            "rejected": _count(db, models.Video, models.Video.status == "rejected"),
            "newWeek": _count(db, models.Video, models.Video.created_at >= week_ago),
        },
        "interactions": {
            "views": int(db.scalar(select(func.coalesce(func.sum(models.Video.views), 0))) or 0),
            "likes": _count(db, models.VideoLike),
            "coins": int(db.scalar(select(func.coalesce(func.sum(models.VideoCoin.amount), 0))) or 0),
            "comments": _count(db, models.Comment, models.Comment.is_deleted.is_(False)),
            "danmaku": _count(db, models.Danmaku),
            "favorites": _count(db, models.FavoriteItem),
        },
        "reports": {
            "pending": _count(db, models.Report, models.Report.status == "pending"),
            "total": _count(db, models.Report),
        },
        "live": {
            "total": _count(db, models.LiveRoom),
            "living": _count(db, models.LiveRoom, models.LiveRoom.status == "live"),
            "banned": _count(db, models.LiveRoom, models.LiveRoom.status == "banned"),
            "viewers": int(db.scalar(select(func.coalesce(func.sum(models.LiveRoom.viewer_count), 0))) or 0),
        },
        "orders": {
            "pending": _count(db, models.Order, models.Order.status == "pending"),
            "paid": _count(db, models.Order, models.Order.status == "paid"),
            "revenueCents": int(
                db.scalar(
                    select(func.coalesce(func.sum(models.Order.amount_cents), 0)).where(models.Order.status == "paid")
                )
                or 0
            ),
        },
        "system": {
            "redis": redis.info(),
            "ffmpeg": transcode.status(),
            "transcoding": _count(db, models.Video, models.Video.transcode_status == "processing"),
            "transcodePending": _count(db, models.Video, models.Video.transcode_status == "pending"),
            "websocket": realtime.stats(),
        },
        "trend": [{"day": str(row[0])[:10], "count": int(row[1])} for row in trend_rows],
        "pendingVideos": [
            video_brief(item, tag_rows(db, [item.id]).get(item.id))
            for item in db.scalars(
                select(models.Video)
                .where(models.Video.status == "pending", models.Video.deleted_at.is_(None))
                .order_by(models.Video.id.asc())
                .limit(8)
            ).all()
        ],
        "recentUsers": [
            {**user_brief(item), "createdAt": iso(item.created_at)}
            for item in db.scalars(select(models.User).order_by(models.User.id.desc()).limit(8)).all()
        ],
        "recentActions": [
            {
                "id": item.id,
                "actor": item.actor_name,
                "action": item.action,
                "targetType": item.target_type,
                "targetId": item.target_id,
                "createdAt": iso(item.created_at),
            }
            for item in db.scalars(select(models.AuditLog).order_by(models.AuditLog.id.desc()).limit(10)).all()
        ],
    }


# ------------------------------------------------------------------ 用户管理


@router.get("/users")
def list_users(
    q: str = Query(""),
    role: str = Query(""),
    banned: str = Query(""),
    page: int = Query(1),
    size: int = Query(0),
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_admin),
):
    _, size, limit, offset = pagination(page, size, 30, 200)
    query = select(models.User)
    if q:
        like = f"%{q.strip()}%"
        query = query.where(
            or_(models.User.username.ilike(like), models.User.display_name.ilike(like), models.User.email.ilike(like))
        )
    if role:
        query = query.where(models.User.role == role)
    if banned == "true":
        query = query.where(models.User.is_banned.is_(True))
    elif banned == "false":
        query = query.where(models.User.is_banned.is_(False))

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(query.order_by(models.User.id.desc()).limit(limit).offset(offset)).all()
    return {
        "items": [
            {
                "id": item.id,
                "username": item.username,
                "displayName": item.display_name or item.username,
                "avatar": item.avatar or "",
                "email": item.email or "",
                "role": item.role,
                "coins": item.coins,
                "level": item.level,
                "videoCount": item.video_count,
                "followerCount": item.follower_count,
                "isBanned": bool(item.is_banned),
                "banReason": item.ban_reason,
                "createdAt": iso(item.created_at),
                "lastLoginAt": iso(item.last_login_at),
                "lastLoginIp": item.last_login_ip or "",
            }
            for item in rows
        ],
        "total": int(total),
        "page": page,
        "size": size,
    }


@router.put("/users/{user_id}")
def update_user(
    user_id: int,
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_admin),
):
    target = db.get(models.User, user_id)
    if not target:
        raise fail(404, "用户不存在")

    if payload.get("role") is not None:
        if not admin.is_superadmin:
            raise fail(403, "只有超级管理员可以调整角色")
        role = payload["role"] if payload["role"] in {"user", "admin", "superadmin"} else "user"
        if target.id == admin.id and role != "superadmin":
            raise fail(400, "不能降低自己的权限")
        target.role = role

    if isinstance(payload.get("isBanned"), bool):
        if target.is_superadmin and not admin.is_superadmin:
            raise fail(403, "不能封禁超级管理员")
        target.is_banned = payload["isBanned"]
        target.ban_reason = str(payload.get("banReason") or "")[:200]

    if payload.get("coins") is not None:
        if not admin.is_superadmin:
            raise fail(403, "只有超级管理员可以调整硬币")
        try:
            target.coins = max(0, int(payload["coins"]))
        except (TypeError, ValueError):
            pass

    if isinstance(payload.get("password"), str) and payload["password"]:
        if not admin.is_superadmin:
            raise fail(403, "只有超级管理员可以重置密码")
        if len(payload["password"]) < site.get_int("password_min_length", 8):
            raise fail(400, "密码太短")
        target.password_hash = hash_password(payload["password"])

    profile = payload.get("profile") if isinstance(payload.get("profile"), dict) else {}
    for key, column in (("displayName", "display_name"), ("email", "email"), ("bio", "bio"),
                        ("avatar", "avatar")):
        if isinstance(profile.get(key), str):
            setattr(target, column, profile[key][:500] or None)

    db.commit()
    audit(db, request, admin, "admin.user_update", "user", target.id, list(payload.keys()))
    return {"ok": True}


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_superadmin),
):
    if user_id == admin.id:
        raise fail(400, "不能删除自己的账号")
    target = db.get(models.User, user_id)
    if not target:
        raise fail(404, "用户不存在")
    if target.is_superadmin:
        raise fail(403, "不能删除超级管理员")
    db.delete(target)
    db.commit()
    audit(db, request, admin, "admin.user_delete", "user", user_id, target.username)
    return {"ok": True}


# ------------------------------------------------------------------ 视频管理


@router.get("/videos")
def admin_videos(
    q: str = Query(""),
    status: str = Query(""),
    include_deleted: int = Query(0),
    page: int = Query(1),
    size: int = Query(0),
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_admin),
):
    _, size, limit, offset = pagination(page, size, 30, 200)
    query = select(models.Video)
    if not include_deleted:
        query = query.where(models.Video.deleted_at.is_(None))
    if status:
        query = query.where(models.Video.status == status)
    if q:
        like = f"%{q.strip()}%"
        query = query.where(or_(models.Video.title.ilike(like), models.Video.description.ilike(like)))
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(query.order_by(models.Video.id.desc()).limit(limit).offset(offset)).all()
    ids = [item.id for item in rows]
    tags = tag_rows(db, ids)
    items = []
    for item in rows:
        data = video_brief(item, tags.get(item.id), with_description=True)
        data["deleted"] = item.deleted_at is not None
        items.append(data)
    return {"items": items, "total": int(total), "page": page, "size": size}


@router.post("/videos/{video_id}/review")
def review_video(
    video_id: int,
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_admin),
):
    video = db.get(models.Video, video_id)
    if not video:
        raise fail(404, "视频不存在")
    approve = bool(payload.get("approve"))
    reason = str(payload.get("reason") or "")[:200]
    author = db.get(models.User, video.author_id)
    was_published = video.status == "published"
    if approve:
        video.status = "published"
        video.published_at = video.published_at or now()
        video.reject_reason = ""
        video.scheduled_at = None
        if author and not was_published:
            author.video_count += 1
    else:
        video.status = "rejected"
        video.reject_reason = reason or "内容不符合社区规范"
        if author and was_published:
            author.video_count = max(0, author.video_count - 1)
    db.commit()
    if author:
        notify(
            db, author.id, "review",
            f"你的视频《{video.title}》{'已通过审核' if approve else '未通过审核'}",
            "" if approve else video.reject_reason,
            ref_type="video", ref_id=video.id, setting_key="notify_review",
        )
    audit(db, request, admin, "admin.video_review", "video", video.id, video.status)
    return {"ok": True, "status": video.status}


@router.put("/videos/{video_id}")
def admin_update_video(
    video_id: int,
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_admin),
):
    video = db.get(models.Video, video_id)
    if not video:
        raise fail(404, "视频不存在")
    for key, column in (("isPinned", "is_pinned"), ("isFeatured", "is_featured"),
                        ("allowComment", "allow_comment"), ("allowDanmaku", "allow_danmaku"),
                        ("allowDownload", "allow_download")):
        if isinstance(payload.get(key), bool):
            setattr(video, column, payload[key])
    if isinstance(payload.get("title"), str) and payload["title"].strip():
        video.title = payload["title"].strip()[:160]
    if isinstance(payload.get("cover"), str):
        video.cover = payload["cover"][:500]
    db.commit()
    audit(db, request, admin, "admin.video_update", "video", video.id)
    return {"ok": True}


@router.delete("/videos/{video_id}")
def admin_delete_video(
    video_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_admin),
):
    video = db.get(models.Video, video_id)
    if not video:
        raise fail(404, "视频不存在")
    video.deleted_at = now()
    author = db.get(models.User, video.author_id)
    if author and video.status == "published":
        author.video_count = max(0, author.video_count - 1)
    db.commit()
    audit(db, request, admin, "admin.video_delete", "video", video_id, video.title)
    return {"ok": True}


# ------------------------------------------------------------- 评论 / 弹幕


@router.get("/comments")
def admin_comments(
    q: str = Query(""),
    page: int = Query(1),
    size: int = Query(0),
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_admin),
):
    _, size, limit, offset = pagination(page, size, 30, 200)
    query = select(models.Comment).where(models.Comment.is_deleted.is_(False))
    if q:
        query = query.where(models.Comment.content.ilike(f"%{q.strip()}%"))
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(query.order_by(models.Comment.id.desc()).limit(limit).offset(offset)).all()
    return {
        "items": [
            {
                "id": item.id,
                "content": item.content,
                "videoId": item.video_id,
                "videoTitle": (db.get(models.Video, item.video_id).title if db.get(models.Video, item.video_id) else ""),
                "user": user_brief(db.get(models.User, item.user_id)),
                "likeCount": item.like_count,
                "createdAt": iso(item.created_at),
            }
            for item in rows
        ],
        "total": int(total),
        "page": page,
        "size": size,
    }


@router.delete("/comments/{comment_id}")
def admin_delete_comment(
    comment_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_admin),
):
    comment = db.get(models.Comment, comment_id)
    if not comment:
        raise fail(404, "评论不存在")
    comment.is_deleted = True
    video = db.get(models.Video, comment.video_id)
    if video:
        video.comments = max(0, video.comments - 1)
    db.commit()
    audit(db, request, admin, "admin.comment_delete", "comment", comment_id)
    return {"ok": True}


@router.get("/danmaku")
def admin_danmaku(
    q: str = Query(""),
    page: int = Query(1),
    size: int = Query(0),
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_admin),
):
    _, size, limit, offset = pagination(page, size, 40, 200)
    query = select(models.Danmaku)
    if q:
        query = query.where(models.Danmaku.content.ilike(f"%{q.strip()}%"))
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(query.order_by(models.Danmaku.id.desc()).limit(limit).offset(offset)).all()
    return {
        "items": [
            {
                "id": item.id,
                "content": item.content,
                "videoId": item.video_id,
                "time": float(item.time_seconds or 0),
                "color": item.color,
                "mode": item.mode,
                "user": user_brief(db.get(models.User, item.user_id)),
                "createdAt": iso(item.created_at),
            }
            for item in rows
        ],
        "total": int(total),
        "page": page,
        "size": size,
    }


# ------------------------------------------------------------------ 分区/标签


@router.get("/categories")
def admin_categories(db: Session = Depends(get_db), admin: models.User = Depends(require_admin)):
    rows = db.scalars(select(models.Category).order_by(models.Category.sort.asc(), models.Category.id.asc())).all()
    counts = dict(
        db.execute(select(models.Video.category_id, func.count(models.Video.id)).group_by(models.Video.category_id)).all()
    )
    return {
        "items": [
            {
                "id": item.id,
                "slug": item.slug,
                "name": item.name,
                "description": item.description,
                "icon": item.icon,
                "sort": item.sort,
                "isActive": bool(item.is_active),
                "count": int(counts.get(item.id, 0)),
            }
            for item in rows
        ]
    }


@router.post("/categories")
def create_category(
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_admin),
):
    name = str(payload.get("name") or "").strip()
    if not name:
        raise fail(400, "请填写分区名称")
    slug = str(payload.get("slug") or "").strip() or f"c{int(datetime.utcnow().timestamp())}"
    if db.scalar(select(models.Category.id).where(models.Category.slug == slug)):
        raise fail(409, "分区标识已存在")
    item = models.Category(
        slug=slug[:48],
        name=name[:48],
        description=str(payload.get("description") or "")[:255],
        icon=str(payload.get("icon") or "🎬")[:16],
        sort=int(payload.get("sort") or 0),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    audit(db, request, admin, "admin.category_create", "category", item.id, name)
    return {"ok": True, "id": item.id}


@router.put("/categories/{category_id}")
def update_category(
    category_id: int,
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_admin),
):
    item = db.get(models.Category, category_id)
    if not item:
        raise fail(404, "分区不存在")
    if isinstance(payload.get("name"), str) and payload["name"].strip():
        item.name = payload["name"].strip()[:48]
    if isinstance(payload.get("description"), str):
        item.description = payload["description"][:255]
    if isinstance(payload.get("icon"), str):
        item.icon = payload["icon"][:16]
    if payload.get("sort") is not None:
        item.sort = int(payload["sort"])
    if isinstance(payload.get("isActive"), bool):
        item.is_active = payload["isActive"]
    db.commit()
    audit(db, request, admin, "admin.category_update", "category", item.id)
    return {"ok": True}


@router.delete("/categories/{category_id}")
def delete_category(
    category_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_admin),
):
    item = db.get(models.Category, category_id)
    if not item:
        raise fail(404, "分区不存在")
    db.delete(item)
    db.commit()
    audit(db, request, admin, "admin.category_delete", "category", category_id)
    return {"ok": True}


@router.get("/tags")
def admin_tags(db: Session = Depends(get_db), admin: models.User = Depends(require_admin)):
    rows = db.scalars(select(models.Tag).order_by(models.Tag.use_count.desc()).limit(300)).all()
    return {
        "items": [
            {"id": item.id, "name": item.name, "color": item.color, "useCount": item.use_count}
            for item in rows
        ]
    }


@router.delete("/tags/{tag_id}")
def delete_tag(
    tag_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_admin),
):
    tag = db.get(models.Tag, tag_id)
    if tag:
        db.delete(tag)
        db.commit()
        audit(db, request, admin, "admin.tag_delete", "tag", tag_id)
    return {"ok": True}


# -------------------------------------------------------------------- 举报


@router.get("/reports")
def admin_reports(
    status: str = Query(""),
    page: int = Query(1),
    size: int = Query(0),
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_admin),
):
    _, size, limit, offset = pagination(page, size, 30, 200)
    query = select(models.Report)
    if status:
        query = query.where(models.Report.status == status)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(query.order_by(models.Report.id.desc()).limit(limit).offset(offset)).all()
    items = []
    for item in rows:
        target_title = ""
        if item.target_type == "video":
            video = db.get(models.Video, item.target_id)
            target_title = video.title if video else "（已删除）"
        elif item.target_type == "comment":
            comment = db.get(models.Comment, item.target_id)
            target_title = (comment.content[:60] if comment else "（已删除）")
        elif item.target_type == "user":
            user = db.get(models.User, item.target_id)
            target_title = user.username if user else "（已删除）"
        items.append(
            {
                "id": item.id,
                "targetType": item.target_type,
                "targetId": item.target_id,
                "targetTitle": target_title,
                "reason": item.reason,
                "detail": item.detail,
                "status": item.status,
                "handleNote": item.handle_note,
                "reporter": user_brief(db.get(models.User, item.reporter_id)),
                "handler": user_brief(db.get(models.User, item.handler_id)) if item.handler_id else None,
                "createdAt": iso(item.created_at),
                "handledAt": iso(item.handled_at),
            }
        )
    return {"items": items, "total": int(total), "page": page, "size": size}


@router.post("/reports/{report_id}/handle")
def handle_report(
    report_id: int,
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_admin),
):
    report = db.get(models.Report, report_id)
    if not report:
        raise fail(404, "举报不存在")
    action = str(payload.get("action") or "handled")
    report.status = "handled" if action != "reject" else "rejected"
    report.handler_id = admin.id
    report.handle_note = str(payload.get("note") or "")[:500]
    report.handled_at = now()

    if action == "delete":
        if report.target_type == "video":
            video = db.get(models.Video, report.target_id)
            if video:
                video.deleted_at = now()
        elif report.target_type == "comment":
            comment = db.get(models.Comment, report.target_id)
            if comment:
                comment.is_deleted = True
        elif report.target_type == "danmaku":
            item = db.get(models.Danmaku, report.target_id)
            if item:
                db.delete(item)
        elif report.target_type == "user":
            target = db.get(models.User, report.target_id)
            if target and not target.is_superadmin:
                target.is_banned = True
                target.ban_reason = report.reason
    db.commit()
    notify(
        db, report.reporter_id, "system", "你的举报已处理",
        f"处理结果：{report.handle_note or report.status}",
        ref_type="report", ref_id=report.id,
    )
    audit(db, request, admin, "admin.report_handle", "report", report.id, report.status)
    return {"ok": True}


# ------------------------------------------------------------- 公告 / 轮播


@router.get("/announcements")
def admin_announcements(db: Session = Depends(get_db), admin: models.User = Depends(require_admin)):
    rows = db.scalars(select(models.Announcement).order_by(models.Announcement.id.desc()).limit(100)).all()
    return {
        "items": [
            {
                "id": item.id,
                "title": item.title,
                "content": item.content,
                "type": item.type,
                "isPinned": bool(item.is_pinned),
                "isPublic": bool(item.is_public),
                "createdAt": iso(item.created_at),
            }
            for item in rows
        ]
    }


@router.post("/announcements")
def create_announcement(
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_admin),
):
    title = str(payload.get("title") or "").strip()
    if not title:
        raise fail(400, "请填写公告标题")
    item = models.Announcement(
        title=title[:160],
        content=str(payload.get("content") or ""),
        type=str(payload.get("type") or "notice"),
        is_pinned=bool(payload.get("isPinned")),
        is_public=payload.get("isPublic", True) is not False,
        author_id=admin.id,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    audit(db, request, admin, "admin.announcement_create", "announcement", item.id)
    return {"ok": True, "id": item.id}


@router.put("/announcements/{announcement_id}")
def update_announcement(
    announcement_id: int,
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_admin),
):
    item = db.get(models.Announcement, announcement_id)
    if not item:
        raise fail(404, "公告不存在")
    for key, column in (("title", "title"), ("content", "content"), ("type", "type")):
        if isinstance(payload.get(key), str):
            setattr(item, column, payload[key][:2000])
    for key, column in (("isPinned", "is_pinned"), ("isPublic", "is_public")):
        if isinstance(payload.get(key), bool):
            setattr(item, column, payload[key])
    db.commit()
    audit(db, request, admin, "admin.announcement_update", "announcement", item.id)
    return {"ok": True}


@router.delete("/announcements/{announcement_id}")
def delete_announcement(
    announcement_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_admin),
):
    item = db.get(models.Announcement, announcement_id)
    if item:
        db.delete(item)
        db.commit()
        audit(db, request, admin, "admin.announcement_delete", "announcement", announcement_id)
    return {"ok": True}


@router.get("/carousel")
def admin_carousel(db: Session = Depends(get_db), admin: models.User = Depends(require_admin)):
    rows = db.scalars(select(models.Carousel).order_by(models.Carousel.sort.asc(), models.Carousel.id.asc())).all()
    return {
        "items": [
            {"id": item.id, "title": item.title, "subtitle": item.subtitle, "image": item.image,
             "link": item.link, "sort": item.sort, "isActive": bool(item.is_active)}
            for item in rows
        ]
    }


@router.post("/carousel")
def create_carousel(
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_admin),
):
    image = str(payload.get("image") or "").strip()
    if not image:
        raise fail(400, "请上传轮播图片")
    item = models.Carousel(
        title=str(payload.get("title") or "")[:160],
        subtitle=str(payload.get("subtitle") or "")[:255],
        image=image[:500],
        link=str(payload.get("link") or "")[:500],
        sort=int(payload.get("sort") or 0),
        is_active=payload.get("isActive", True) is not False,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    audit(db, request, admin, "admin.carousel_create", "carousel", item.id)
    return {"ok": True, "id": item.id}


@router.put("/carousel/{carousel_id}")
def update_carousel(
    carousel_id: int,
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_admin),
):
    item = db.get(models.Carousel, carousel_id)
    if not item:
        raise fail(404, "轮播不存在")
    for key, column in (("title", "title"), ("subtitle", "subtitle"), ("image", "image"), ("link", "link")):
        if isinstance(payload.get(key), str):
            setattr(item, column, payload[key][:500])
    if payload.get("sort") is not None:
        item.sort = int(payload["sort"])
    if isinstance(payload.get("isActive"), bool):
        item.is_active = payload["isActive"]
    db.commit()
    audit(db, request, admin, "admin.carousel_update", "carousel", item.id)
    return {"ok": True}


@router.delete("/carousel/{carousel_id}")
def delete_carousel(
    carousel_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_admin),
):
    item = db.get(models.Carousel, carousel_id)
    if item:
        db.delete(item)
        db.commit()
        audit(db, request, admin, "admin.carousel_delete", "carousel", carousel_id)
    return {"ok": True}


# ------------------------------------------------------------------ 设置


@router.get("/settings")
def get_settings(db: Session = Depends(get_db), admin: models.User = Depends(require_superadmin)):
    return {
        "groups": SETTING_GROUPS,
        "fields": SETTINGS,
        "values": site.all_settings(mask_secrets=True),
        "publicValues": site.public_settings(),
    }


@router.put("/settings")
def put_settings(
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_superadmin),
):
    patch = payload.get("values") if isinstance(payload.get("values"), dict) else payload
    changed = site.update(db, patch)
    audit(db, request, admin, "admin.settings_update", detail=",".join(changed))
    return {"ok": True, "changed": changed, "values": site.all_settings(mask_secrets=True)}


@router.post("/settings/reset")
def reset_settings(
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_superadmin),
):
    keys = payload.get("keys") if isinstance(payload.get("keys"), list) else None
    site.reset(db, keys)
    audit(db, request, admin, "admin.settings_reset", detail=str(keys)[:200])
    return {"ok": True, "values": site.all_settings(mask_secrets=True)}


# ------------------------------------------------------------------ 日志 / 备份


@router.get("/logs/audit")
def audit_logs(
    q: str = Query(""),
    page: int = Query(1),
    size: int = Query(0),
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_superadmin),
):
    _, size, limit, offset = pagination(page, size, 50, 200)
    query = select(models.AuditLog)
    if q:
        like = f"%{q.strip()}%"
        query = query.where(or_(models.AuditLog.action.ilike(like), models.AuditLog.actor_name.ilike(like)))
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(query.order_by(models.AuditLog.id.desc()).limit(limit).offset(offset)).all()
    return {
        "items": [
            {"id": item.id, "actor": item.actor_name, "action": item.action, "targetType": item.target_type,
             "targetId": item.target_id, "detail": item.detail, "ip": item.ip, "createdAt": iso(item.created_at)}
            for item in rows
        ],
        "total": int(total),
        "page": page,
        "size": size,
    }


@router.get("/logs/login")
def login_logs(
    page: int = Query(1),
    size: int = Query(0),
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_superadmin),
):
    _, size, limit, offset = pagination(page, size, 50, 200)
    total = _count(db, models.LoginLog)
    rows = db.scalars(select(models.LoginLog).order_by(models.LoginLog.id.desc()).limit(limit).offset(offset)).all()
    return {
        "items": [
            {"id": item.id, "username": item.username, "ip": item.ip, "userAgent": item.user_agent,
             "success": bool(item.success), "createdAt": iso(item.created_at)}
            for item in rows
        ],
        "total": total,
        "page": page,
        "size": size,
    }


@router.get("/backups")
def get_backups(admin: models.User = Depends(require_superadmin)):
    return {"items": list_backups()}


@router.post("/backups")
async def create_backup(request: Request, db: Session = Depends(get_db), admin: models.User = Depends(require_superadmin)):
    try:
        file = backup_database("manual")
    except Exception as exc:  # noqa: BLE001
        raise fail(500, f"备份失败：{exc}") from exc
    audit(db, request, admin, "admin.backup", detail=str(file))
    return {"ok": True, "file": file.name}


@router.delete("/backups/{name}")
def remove_backup(
    name: str,
    request: Request,
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_superadmin),
):
    if not delete_backup(name):
        raise fail(404, "备份不存在")
    audit(db, request, admin, "admin.backup_delete", detail=name)
    return {"ok": True}


@router.post("/maintenance/cleanup")
def cleanup_logs(
    request: Request,
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_superadmin),
):
    days = site.get_int("login_log_keep_days", 90)
    cutoff = now() - timedelta(days=days)
    removed_login = db.query(models.LoginLog).filter(models.LoginLog.created_at < cutoff).delete()
    removed_rate = db.query(models.RateLimit).filter(models.RateLimit.expires_at < now()).delete()
    db.commit()
    audit(db, request, admin, "admin.cleanup", detail=f"login={removed_login},rate={removed_rate}")
    return {"ok": True, "removedLoginLogs": int(removed_login or 0), "removedRateLimits": int(removed_rate or 0)}


# ------------------------------------------------------------ 基础设施


@router.get("/infra")
def infra_status(admin: models.User = Depends(require_admin), db: Session = Depends(get_db)):
    return {
        "redis": redis.info(),
        "ffmpeg": transcode.status(),
        "transcode": {
            "pending": _count(db, models.Video, models.Video.transcode_status == "pending"),
            "processing": _count(db, models.Video, models.Video.transcode_status == "processing"),
            "done": _count(db, models.Video, models.Video.transcode_status == "done"),
            "failed": _count(db, models.Video, models.Video.transcode_status == "failed"),
            "skipped": _count(db, models.Video, models.Video.transcode_status == "skipped"),
        },
        "realtime": realtime.stats(),
        "live": live_stream.status(),
        "variants": _count(db, models.VideoVariant),
    }


@router.post("/cache/clear")
def clear_cache(request: Request, admin: models.User = Depends(require_superadmin), db: Session = Depends(get_db)):
    removed = redis.cache_clear("photonv:cache:")
    audit(db, request, admin, "admin.cache_clear", detail=str(removed))
    return {"ok": True, "removed": removed}


@router.post("/videos/{video_id}/transcode")
def retranscode(
    video_id: int,
    request: Request,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    video = db.get(models.Video, video_id)
    if not video:
        raise fail(404, "视频不存在")
    transcode.enqueue(db, video)
    audit(db, request, admin, "admin.transcode_enqueue", "video", video_id)
    return {"ok": True}


@router.post("/users/{user_id}/live-permission")
def set_live_permission(
    user_id: int,
    payload: dict,
    request: Request,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.get(models.User, user_id)
    if not user:
        raise fail(404, "用户不存在")
    user.can_live = bool(payload.get("canLive"))
    db.commit()
    notify(
        db, user.id, "system", "直播权限变更",
        "管理员已为你开通直播权限，可以在「直播 → 我的直播间」里配置并开播了。"
        if user.can_live
        else "你的直播权限已被关闭。",
    )
    audit(db, request, admin, "admin.live_permission", "user", user_id, user.can_live)
    return {"ok": True, "canLive": user.can_live}
