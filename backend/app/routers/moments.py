"""动态：只挂在个人主页下，没有全站动态频道。

发布 / 点赞 / 删除都在这个 router 里，个人主页通过
`GET /api/users/{username}/moments` 拉某个人的动态列表。
"""
from __future__ import annotations

import json
from typing import Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import models, settings_store as site
from ..database import get_db
from ..security import current_user, require_user
from ..utils import audit, check_banned_words, fail, iso, pagination, rate_limit, user_brief

router = APIRouter(prefix="/api", tags=["moments"])

MAX_IMAGES = 9


def parse_images(raw: Optional[str]) -> list[str]:
    if not raw:
        return []
    try:
        value = json.loads(raw)
    except (TypeError, ValueError):
        return []
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str)][:MAX_IMAGES]


def moment_payload(
    item: models.Moment,
    author: Optional[models.User],
    viewer_id: Optional[int],
    liked: bool = False,
) -> dict:
    return {
        "id": item.id,
        "content": item.content,
        "images": parse_images(item.images),
        "isPrivate": bool(item.is_private),
        "likeCount": int(item.like_count or 0),
        "liked": liked,
        "isMine": bool(viewer_id and item.user_id == viewer_id),
        "createdAt": iso(item.created_at),
        "author": user_brief(author),
    }


def find_user(db: Session, username: str) -> models.User:
    user = db.scalar(select(models.User).where(models.User.username == username))
    if not user:
        raise fail(404, "用户不存在")
    return user


def liked_ids(db: Session, viewer: Optional[models.User], moment_ids: list[int]) -> set[int]:
    if not viewer or not moment_ids:
        return set()
    rows = db.scalars(
        select(models.MomentLike.moment_id).where(
            models.MomentLike.user_id == viewer.id,
            models.MomentLike.moment_id.in_(moment_ids),
        )
    ).all()
    return {int(row) for row in rows}


class MomentIn(BaseModel):
    content: str = Field(default="", max_length=2000)
    images: list[str] = Field(default_factory=list)
    is_private: bool = False


@router.get("/users/{username}/moments")
def list_moments(
    username: str,
    page: int = 1,
    size: int = 20,
    db: Session = Depends(get_db),
    viewer: Optional[models.User] = Depends(current_user),
):
    """个人主页的动态列表。私密动态只有本人（和管理员）能看到。"""
    if not site.get_bool("moments_enabled", True):
        return {"items": [], "total": 0, "enabled": False}
    user = find_user(db, username)
    is_self = bool(viewer and viewer.id == user.id)
    is_staff = bool(viewer and viewer.is_admin)
    if user.is_private and not is_self and not is_staff:
        raise fail(403, "该用户设置了隐私，暂不公开主页")

    page, size, limit, offset = pagination(page, size, default_size=20, max_size=50)
    query = select(models.Moment).where(
        models.Moment.user_id == user.id,
        models.Moment.is_deleted.is_(False),
    )
    if not is_self and not is_staff:
        query = query.where(models.Moment.is_private.is_(False))

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(query.order_by(models.Moment.id.desc()).limit(limit).offset(offset)).all()
    liked = liked_ids(db, viewer, [row.id for row in rows])
    return {
        "items": [moment_payload(row, user, viewer.id if viewer else None, row.id in liked) for row in rows],
        "total": int(total),
        "page": page,
        "size": size,
        "enabled": True,
    }


@router.post("/moments")
def create_moment(
    payload: MomentIn,
    request: Request,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_user),
):
    if not site.get_bool("moments_enabled", True):
        raise fail(403, "动态功能已关闭")
    if not rate_limit(f"moment:{user.id}", 20):
        raise fail(429, "发得太快了，歇一会儿再发")

    content = (payload.content or "").strip()
    images = [item for item in payload.images if item][:MAX_IMAGES]
    if not content and not images:
        raise fail(400, "写点什么或者配张图吧")
    if len(content) > 2000:
        content = content[:2000]
    check_banned_words(content)

    item = models.Moment(
        user_id=user.id,
        content=content,
        images=json.dumps(images, ensure_ascii=False),
        is_private=bool(payload.is_private),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    audit(db, request, user, "moment.create", target_type="moment", target_id=item.id)
    return {"id": item.id, "createdAt": iso(item.created_at)}


@router.delete("/moments/{moment_id}")
def delete_moment(
    moment_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_user),
):
    item = db.get(models.Moment, moment_id)
    if not item or item.is_deleted:
        raise fail(404, "动态不存在")
    if item.user_id != user.id and not user.is_admin:
        raise fail(403, "只能删除自己的动态")
    item.is_deleted = True
    db.commit()
    audit(db, request, user, "moment.delete", target_type="moment", target_id=item.id)
    return {"ok": True}


@router.post("/moments/{moment_id}/like")
def toggle_like(
    moment_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_user),
):
    item = db.get(models.Moment, moment_id)
    if not item or item.is_deleted:
        raise fail(404, "动态不存在")
    if item.is_private and item.user_id != user.id:
        raise fail(403, "无权操作")

    existing = db.get(models.MomentLike, {"moment_id": moment_id, "user_id": user.id})
    if existing:
        db.delete(existing)
        item.like_count = max(0, int(item.like_count or 0) - 1)
        liked = False
    else:
        db.add(models.MomentLike(moment_id=moment_id, user_id=user.id))
        item.like_count = int(item.like_count or 0) + 1
        liked = True
    db.commit()
    return {"liked": liked, "likeCount": int(item.like_count or 0)}
