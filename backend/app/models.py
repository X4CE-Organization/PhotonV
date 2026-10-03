"""数据模型（SQLAlchemy 2.0）。"""
from __future__ import annotations

from typing import Optional

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def now_column() -> Mapped[datetime]:
    return mapped_column(DateTime, server_default=func.now())


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    email: Mapped[Optional[str]] = mapped_column(String(160), unique=True, nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(16), default="user")  # user | admin | superadmin
    display_name: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    avatar: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    banner: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    bio: Mapped[str] = mapped_column(Text, default="")
    gender: Mapped[int] = mapped_column(Integer, default=0)
    birthday: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    level: Mapped[int] = mapped_column(Integer, default=0)
    exp: Mapped[int] = mapped_column(Integer, default=0)
    coins: Mapped[int] = mapped_column(Integer, default=0)
    follower_count: Mapped[int] = mapped_column(Integer, default=0)
    following_count: Mapped[int] = mapped_column(Integer, default=0)
    video_count: Mapped[int] = mapped_column(Integer, default=0)
    like_count: Mapped[int] = mapped_column(Integer, default=0)
    play_count: Mapped[int] = mapped_column(Integer, default=0)

    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)
    ban_reason: Mapped[str] = mapped_column(String(255), default="")
    is_private: Mapped[bool] = mapped_column(Boolean, default=False)
    allow_message: Mapped[bool] = mapped_column(Boolean, default=True)
    show_email: Mapped[bool] = mapped_column(Boolean, default=False)
    theme: Mapped[str] = mapped_column(String(16), default="light")

    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_login_ip: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    videos: Mapped[list["Video"]] = relationship(back_populates="author", cascade="all, delete-orphan")

    @property
    def is_admin(self) -> bool:
        return self.role in {"admin", "superadmin"}

    @property
    def is_superadmin(self) -> bool:
        return self.role == "superadmin"


class Follow(Base):
    __tablename__ = "follows"
    __table_args__ = (Index("idx_follows_followee", "followee_id", "created_at"),)

    follower_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    followee_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(48), unique=True)
    name: Mapped[str] = mapped_column(String(48))
    description: Mapped[str] = mapped_column(String(255), default="")
    icon: Mapped[str] = mapped_column(String(16), default="🎬")
    sort: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(48), unique=True)
    color: Mapped[str] = mapped_column(String(16), default="")
    use_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Video(Base):
    __tablename__ = "videos"
    __table_args__ = (
        Index("idx_videos_feed", "status", "deleted_at", "published_at"),
        Index("idx_videos_author", "author_id", "status", "id"),
        Index("idx_videos_hot", "status", "views", "id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    author_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text, default="")
    cover: Mapped[str] = mapped_column(String(500), default="")
    source: Mapped[str] = mapped_column(String(500), default="")
    source_url: Mapped[str] = mapped_column(String(500), default="")
    duration: Mapped[int] = mapped_column(Integer, default=0)
    filesize: Mapped[int] = mapped_column(BigInteger, default=0)
    width: Mapped[int] = mapped_column(Integer, default=0)
    height: Mapped[int] = mapped_column(Integer, default=0)
    category_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending|published|rejected|private
    reject_reason: Mapped[str] = mapped_column(String(255), default="")

    views: Mapped[int] = mapped_column(Integer, default=0)
    likes: Mapped[int] = mapped_column(Integer, default=0)
    coins: Mapped[int] = mapped_column(Integer, default=0)
    favorites: Mapped[int] = mapped_column(Integer, default=0)
    comments: Mapped[int] = mapped_column(Integer, default=0)
    danmaku_count: Mapped[int] = mapped_column(Integer, default=0)
    shares: Mapped[int] = mapped_column(Integer, default=0)

    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False)
    allow_comment: Mapped[bool] = mapped_column(Boolean, default=True)
    allow_danmaku: Mapped[bool] = mapped_column(Boolean, default=True)
    allow_download: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    author: Mapped[User] = relationship(back_populates="videos")
    category: Mapped[Optional[Category]] = relationship()


class VideoTag(Base):
    __tablename__ = "video_tags"

    video_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("videos.id", ondelete="CASCADE"), primary_key=True
    )
    tag_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)


class VideoLike(Base):
    __tablename__ = "video_likes"

    video_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("videos.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class VideoCoin(Base):
    __tablename__ = "video_coins"

    video_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("videos.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    amount: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class FavoriteFolder(Base):
    __tablename__ = "favorite_folders"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(64))
    description: Mapped[str] = mapped_column(String(255), default="")
    is_public: Mapped[bool] = mapped_column(Boolean, default=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    item_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class FavoriteItem(Base):
    __tablename__ = "favorite_items"

    folder_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("favorite_folders.id", ondelete="CASCADE"), primary_key=True
    )
    video_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("videos.id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class WatchHistory(Base):
    __tablename__ = "watch_history"

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    video_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("videos.id", ondelete="CASCADE"), primary_key=True
    )
    progress: Mapped[int] = mapped_column(Integer, default=0)
    duration: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class WatchLater(Base):
    __tablename__ = "watch_later"

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    video_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("videos.id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Comment(Base):
    __tablename__ = "comments"
    __table_args__ = (Index("idx_comments_video", "video_id", "is_deleted", "id"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    video_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("videos.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    parent_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    content: Mapped[str] = mapped_column(Text)
    like_count: Mapped[int] = mapped_column(Integer, default=0)
    reply_count: Mapped[int] = mapped_column(Integer, default=0)
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class CommentLike(Base):
    __tablename__ = "comment_likes"

    comment_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("comments.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Danmaku(Base):
    __tablename__ = "danmaku"
    __table_args__ = (Index("idx_danmaku_video", "video_id", "time_seconds"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    video_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("videos.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    content: Mapped[str] = mapped_column(String(120))
    time_seconds: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    color: Mapped[str] = mapped_column(String(16), default="#ffffff")
    mode: Mapped[str] = mapped_column(String(16), default="scroll")
    font_size: Mapped[int] = mapped_column(Integer, default=25)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Playlist(Base):
    __tablename__ = "playlists"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(String(500), default="")
    cover: Mapped[str] = mapped_column(String(500), default="")
    is_public: Mapped[bool] = mapped_column(Boolean, default=True)
    video_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class PlaylistItem(Base):
    __tablename__ = "playlist_items"

    playlist_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("playlists.id", ondelete="CASCADE"), primary_key=True
    )
    video_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("videos.id", ondelete="CASCADE"), primary_key=True
    )
    order_no: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (Index("idx_notifications_user", "user_id", "is_read", "id"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    from_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    type: Mapped[str] = mapped_column(String(24), default="system")
    title: Mapped[str] = mapped_column(String(160), default="")
    content: Mapped[str] = mapped_column(Text, default="")
    ref_type: Mapped[str] = mapped_column(String(24), default="")
    ref_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    reporter_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    target_type: Mapped[str] = mapped_column(String(24))
    target_id: Mapped[int] = mapped_column(BigInteger)
    reason: Mapped[str] = mapped_column(String(64), default="other")
    detail: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(16), default="pending")
    handler_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    handle_note: Mapped[str] = mapped_column(String(500), default="")
    handled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Announcement(Base):
    __tablename__ = "announcements"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(160))
    content: Mapped[str] = mapped_column(Text, default="")
    type: Mapped[str] = mapped_column(String(24), default="notice")
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    is_public: Mapped[bool] = mapped_column(Boolean, default=True)
    author_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Carousel(Base):
    __tablename__ = "carousel"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(160), default="")
    subtitle: Mapped[str] = mapped_column(String(255), default="")
    image: Mapped[str] = mapped_column(String(500))
    link: Mapped[str] = mapped_column(String(500), default="")
    sort: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (Index("idx_audit_time", "id"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    actor_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    actor_name: Mapped[str] = mapped_column(String(64), default="")
    action: Mapped[str] = mapped_column(String(64))
    target_type: Mapped[str] = mapped_column(String(32), default="")
    target_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    detail: Mapped[str] = mapped_column(Text, default="")
    ip: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class LoginLog(Base):
    __tablename__ = "login_logs"
    __table_args__ = (Index("idx_login_logs_time", "id"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    username: Mapped[str] = mapped_column(String(64), default="")
    ip: Mapped[str] = mapped_column(String(64), default="")
    user_agent: Mapped[str] = mapped_column(String(255), default="")
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class RateLimit(Base):
    __tablename__ = "rate_limits"

    key: Mapped[str] = mapped_column(String(160), primary_key=True)
    count: Mapped[int] = mapped_column(Integer, default=0)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
