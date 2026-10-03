"""通用工具：分页、序列化、审计日志、通知、限流、敏感词。"""
from __future__ import annotations

import time
from datetime import datetime
from typing import Any, Optional

from fastapi import HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models
from . import settings_store as site


# ------------------------------------------------------------------ 通用


def now() -> datetime:
    return datetime.utcnow()


def fail(status: int, message: str, code: Optional[str] = None) -> HTTPException:
    return HTTPException(status_code=status, detail={"code": code or "ERROR", "message": message})


def pagination(page: int, size: int, default_size: int = 20, max_size: int = 100) -> tuple[int, int, int, int]:
    page = max(1, int(page or 1))
    size = min(max_size, max(1, int(size or default_size)))
    return page, size, size, (page - 1) * size


def iso(value: Optional[datetime]) -> Optional[str]:
    return value.strftime("%Y-%m-%d %H:%M:%S") if value else None


# ------------------------------------------------------------ 序列化


def user_brief(user: Optional[models.User]) -> Optional[dict[str, Any]]:
    if not user:
        return None
    return {
        "id": user.id,
        "username": user.username,
        "displayName": user.display_name or user.username,
        "avatar": user.avatar or "",
        "bio": user.bio or "",
        "level": user.level,
        "followerCount": user.follower_count,
        "videoCount": user.video_count,
        "role": user.role if user.is_admin else "user",
    }


def user_me(user: models.User) -> dict[str, Any]:
    data = user_brief(user) or {}
    data.update(
        {
            "email": user.email or "",
            "role": user.role,
            "coins": user.coins,
            "exp": user.exp,
            "followingCount": user.following_count,
            "likeCount": user.like_count,
            "playCount": user.play_count,
            "isPrivate": user.is_private,
            "allowMessage": user.allow_message,
            "showEmail": user.show_email,
            "theme": user.theme,
            "gender": user.gender,
            "birthday": user.birthday or "",
            "banner": user.banner or "",
            "createdAt": iso(user.created_at),
            "lastLoginAt": iso(user.last_login_at),
            "isAdmin": user.is_admin,
            "isSuperadmin": user.is_superadmin,
            "membershipLevel": user.membership_level,
            "membershipExpires": iso(user.membership_expires),
            "membershipActive": bool(user.membership_expires and user.membership_expires > now()),
            "totalEarned": user.total_earned,
            "canLive": bool(user.can_live or user.is_admin),
            "emailVerified": bool(user.email_verified),
            "mailOptout": bool(user.mail_optout),
            "streamKey": user.stream_key or "",
        }
    )
    return data


def tag_rows(db: Session, video_ids: list[int]) -> dict[int, list[dict]]:
    if not video_ids:
        return {}
    rows = db.execute(
        select(models.VideoTag.video_id, models.Tag.id, models.Tag.name, models.Tag.color).join(
            models.Tag, models.Tag.id == models.VideoTag.tag_id
        ).where(models.VideoTag.video_id.in_(video_ids))
    ).all()
    result: dict[int, list[dict]] = {}
    for video_id, tag_id, name, color in rows:
        result.setdefault(video_id, []).append({"id": tag_id, "name": name, "color": color})
    return result


def viewer_flags(db: Session, video_ids: list[int], viewer: Optional[models.User]) -> dict[int, dict]:
    if not viewer or not video_ids:
        return {}
    liked = {
        row[0]
        for row in db.execute(
            select(models.VideoLike.video_id).where(
                models.VideoLike.user_id == viewer.id, models.VideoLike.video_id.in_(video_ids)
            )
        ).all()
    }
    coined = {
        row[0]
        for row in db.execute(
            select(models.VideoCoin.video_id).where(
                models.VideoCoin.user_id == viewer.id, models.VideoCoin.video_id.in_(video_ids)
            )
        ).all()
    }
    favorited = {
        row[0]
        for row in db.execute(
            select(models.FavoriteItem.video_id)
            .join(models.FavoriteFolder, models.FavoriteFolder.id == models.FavoriteItem.folder_id)
            .where(models.FavoriteFolder.user_id == viewer.id, models.FavoriteItem.video_id.in_(video_ids))
        ).all()
    }
    later = {
        row[0]
        for row in db.execute(
            select(models.WatchLater.video_id).where(
                models.WatchLater.user_id == viewer.id, models.WatchLater.video_id.in_(video_ids)
            )
        ).all()
    }
    return {
        video_id: {
            "liked": video_id in liked,
            "coined": video_id in coined,
            "favorited": video_id in favorited,
            "watchLater": video_id in later,
        }
        for video_id in video_ids
    }


def video_brief(
    video: models.Video,
    tags: Optional[list[dict]] = None,
    flags: Optional[dict] = None,
    with_description: bool = False,
) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": video.id,
        "title": video.title,
        "cover": video.cover or "",
        "duration": video.duration,
        "status": video.status,
        "views": video.views,
        "likes": video.likes,
        "coins": video.coins,
        "favorites": video.favorites,
        "comments": video.comments,
        "danmaku": video.danmaku_count,
        "shares": video.shares,
        "isPinned": bool(video.is_pinned),
        "isFeatured": bool(video.is_featured),
        "createdAt": iso(video.created_at),
        "publishedAt": iso(video.published_at),
        "author": user_brief(video.author),
        "categoryId": video.category_id,
        "tags": tags or [],
    }
    if with_description:
        data["description"] = video.description or ""
        data["allowComment"] = bool(video.allow_comment)
        data["allowDanmaku"] = bool(video.allow_danmaku)
        data["allowDownload"] = bool(video.allow_download)
        data["sourceUrl"] = video.source_url or ""
        data["source"] = video.source or ""
        data["filesize"] = video.filesize
        data["rejectReason"] = video.reject_reason or ""
    if flags:
        data.update(flags)
    return data


# ------------------------------------------------------------ 审计 / 通知


def audit(
    db: Session,
    request: Optional[Request],
    actor: Optional[models.User],
    action: str,
    target_type: str = "",
    target_id: Optional[int] = None,
    detail: Any = None,
) -> None:
    if not site.get_bool("audit_log", True):
        return
    entry = models.AuditLog(
        actor_id=actor.id if actor else None,
        actor_name=actor.username if actor else "anonymous",
        action=action,
        target_type=target_type,
        target_id=target_id,
        detail="" if detail is None else str(detail)[:500],
        ip=(request.client.host if request and request.client else "")[:64],
    )
    db.add(entry)
    db.commit()


def notify(
    db: Session,
    user_id: int,
    type_: str,
    title: str,
    content: str = "",
    from_id: Optional[int] = None,
    ref_type: str = "",
    ref_id: Optional[int] = None,
    setting_key: Optional[str] = None,
) -> None:
    if setting_key and not site.get_bool(setting_key, True):
        return
    db.add(
        models.Notification(
            user_id=user_id,
            from_id=from_id,
            type=type_,
            title=title[:160],
            content=content[:2000],
            ref_type=ref_type,
            ref_id=ref_id,
        )
    )
    db.commit()


# ------------------------------------------------------------ 限流 / 敏感词

_buckets: dict[str, float] = {}


def rate_limit(key: str, interval_seconds: int) -> bool:
    """简单内存限流：同一 key 在 interval 内只允许一次。"""
    if interval_seconds <= 0:
        return True
    from . import redis_client as _redis

    shared = _redis.rate_limit(key, interval_seconds)
    if shared is not None:
        return shared
    current = time.time()
    last = _buckets.get(key, 0)
    if current - last < interval_seconds:
        return False
    _buckets[key] = current
    if len(_buckets) > 5000:
        cutoff = current - 3600
        for name in [name for name, stamp in _buckets.items() if stamp < cutoff]:
            _buckets.pop(name, None)
    return True


def check_banned_words(*texts: str) -> None:
    words = site.get_json("banned_words", []) or []
    joined = "\n".join(texts)
    for word in words:
        if word and word in joined:
            raise fail(400, f"内容包含敏感词「{word}」，请修改后重试")


# ------------------------------------------------------------ 经验 / 等级


def grant_exp(db: Session, user: models.User, amount: int) -> None:
    if amount <= 0:
        return
    user.exp = (user.exp or 0) + amount
    step = max(10, site.get_int("level_exp_step", 200))
    level = min(6, user.exp // step)
    if level > (user.level or 0):
        user.level = level
        notify(db, user.id, "system", f"恭喜升级到 Lv{level}", "继续加油，创作更多精彩内容吧！")
    db.commit()


def level_name(level: int) -> str:
    names = site.get_json("level_names", []) or []
    if 0 <= level < len(names):
        return names[level]
    return names[-1] if names else f"Lv{level}"


def level_progress(user: models.User) -> dict[str, Any]:
    step = max(10, site.get_int("level_exp_step", 200))
    current = user.exp % step
    return {
        "level": user.level,
        "name": level_name(user.level),
        "exp": user.exp,
        "current": current,
        "next": step,
        "percent": round(current * 100 / step, 1),
    }
