"""数据模型（SQLAlchemy 2.0）。"""
from __future__ import annotations

from typing import Optional

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
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

    # 会员 / 直播 / 邮件
    membership_level: Mapped[int] = mapped_column(Integer, default=0)
    membership_expires: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    total_earned: Mapped[int] = mapped_column(Integer, default=0)
    can_live: Mapped[bool] = mapped_column(Boolean, default=False)
    stream_key: Mapped[str] = mapped_column(String(64), default="")
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    mail_optout: Mapped[bool] = mapped_column(Boolean, default=False)
    last_bonus_date: Mapped[str] = mapped_column(String(16), default="")
    phone: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    phone_verified: Mapped[bool] = mapped_column(Boolean, default=False)

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

    # 定时发布：到点后由后台自动把 pending 变为 published
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # 转码与多清晰度
    transcode_status: Mapped[str] = mapped_column(String(16), default="pending")
    transcode_error: Mapped[str] = mapped_column(String(500), default="")
    hls_path: Mapped[str] = mapped_column(String(500), default="")

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


class VideoNote(Base):
    """带时间点的视频笔记（类似视频内的个人笔记）。"""

    __tablename__ = "video_notes"
    __table_args__ = (Index("idx_video_notes_video", "video_id", "time_seconds"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    video_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("videos.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    time_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    content: Mapped[str] = mapped_column(String(1000), default="")
    is_public: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class Emoji(Base):
    """自定义表情包：用户上传或从别处收藏，可在评论 / 私信里发送。"""

    __tablename__ = "emojis"
    __table_args__ = (Index("idx_emojis_owner", "owner_id", "id"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    owner_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(32), default="")
    url: Mapped[str] = mapped_column(String(500))
    origin_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    use_count: Mapped[int] = mapped_column(Integer, default=0)
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


# ---------------------------------------------------------------- 邮件


class MailCode(Base):
    __tablename__ = "mail_codes"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(160), index=True)
    code: Mapped[str] = mapped_column(String(16))
    purpose: Mapped[str] = mapped_column(String(16), default="verify")
    user_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    used: Mapped[bool] = mapped_column(Boolean, default=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class MailLog(Base):
    __tablename__ = "mail_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    to_email: Mapped[str] = mapped_column(String(160))
    subject: Mapped[str] = mapped_column(String(200), default="")
    category: Mapped[str] = mapped_column(String(24), default="system")
    status: Mapped[str] = mapped_column(String(16), default="sent")
    error: Mapped[str] = mapped_column(String(500), default="")
    user_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


# ------------------------------------------------------------ 第三方登录


class OAuthAccount(Base):
    __tablename__ = "oauth_accounts"
    __table_args__ = (UniqueConstraint("provider", "provider_user_id", name="uq_oauth_provider_user"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    provider: Mapped[str] = mapped_column(String(24))
    provider_user_id: Mapped[str] = mapped_column(String(64))
    provider_username: Mapped[str] = mapped_column(String(64), default="")
    provider_email: Mapped[str] = mapped_column(String(160), default="")
    avatar: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


# ----------------------------------------------------------------- 私信


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (UniqueConstraint("user_a", "user_b", name="uq_conversation_pair"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_a: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    user_b: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    last_message: Mapped[str] = mapped_column(String(300), default="")
    last_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    unread_a: Mapped[int] = mapped_column(Integer, default=0)
    unread_b: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class DirectMessage(Base):
    __tablename__ = "direct_messages"
    __table_args__ = (Index("idx_dm_conversation", "conversation_id", "id"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("conversations.id", ondelete="CASCADE")
    )
    sender_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    content: Mapped[str] = mapped_column(Text)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


# ----------------------------------------------------------------- 直播


class LiveRoom(Base):
    __tablename__ = "live_rooms"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    owner_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(120))
    cover: Mapped[str] = mapped_column(String(500), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    category_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )
    stream_key: Mapped[str] = mapped_column(String(64), default="")
    play_url: Mapped[str] = mapped_column(String(500), default="")
    # 推流来源：rtmp（OBS 等） / whip（浏览器开播） / ''（未推流）
    stream_source: Mapped[str] = mapped_column(String(16), default="")
    status: Mapped[str] = mapped_column(String(16), default="offline")
    viewer_count: Mapped[int] = mapped_column(Integer, default=0)
    total_viewers: Mapped[int] = mapped_column(Integer, default=0)
    danmaku_count: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class LiveChat(Base):
    __tablename__ = "live_chats"
    __table_args__ = (Index("idx_live_chat_room", "room_id", "id"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    room_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("live_rooms.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    content: Mapped[str] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


# ------------------------------------------------------------ 会员 / 订单


class MembershipPlan(Base):
    __tablename__ = "membership_plans"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(48))
    days: Mapped[int] = mapped_column(Integer, default=30)
    price_cents: Mapped[int] = mapped_column(Integer, default=0)
    description: Mapped[str] = mapped_column(String(255), default="")
    badge: Mapped[str] = mapped_column(String(24), default="")
    sort: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (Index("idx_orders_user", "user_id", "id"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    order_no: Mapped[str] = mapped_column(String(40), unique=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    type: Mapped[str] = mapped_column(String(16), default="membership")
    plan_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    target_user_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    title: Mapped[str] = mapped_column(String(120), default="")
    amount_cents: Mapped[int] = mapped_column(Integer, default=0)
    coins: Mapped[int] = mapped_column(Integer, default=0)
    pay_method: Mapped[str] = mapped_column(String(24), default="manual")
    status: Mapped[str] = mapped_column(String(16), default="pending")
    note: Mapped[str] = mapped_column(String(255), default="")
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    trade_no: Mapped[str] = mapped_column(String(64), default="")
    pay_payload: Mapped[str] = mapped_column(Text, default="")


class SmsCode(Base):
    __tablename__ = "sms_codes"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    phone: Mapped[str] = mapped_column(String(32), index=True)
    code: Mapped[str] = mapped_column(String(16))
    purpose: Mapped[str] = mapped_column(String(16), default="bind")
    user_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    used: Mapped[bool] = mapped_column(Boolean, default=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class VideoVariant(Base):
    __tablename__ = "video_variants"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    video_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("videos.id", ondelete="CASCADE"))
    quality: Mapped[str] = mapped_column(String(16))
    label: Mapped[str] = mapped_column(String(24), default="")
    path: Mapped[str] = mapped_column(String(500))
    filesize: Mapped[int] = mapped_column(BigInteger, default=0)
    width: Mapped[int] = mapped_column(Integer, default=0)
    height: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Moment(Base):
    """动态：只能在个人主页里发布和浏览，不单独开全站频道。"""

    __tablename__ = "moments"
    __table_args__ = (Index("idx_moments_user", "user_id", "id"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    content: Mapped[str] = mapped_column(Text, default="")
    # JSON 数组，最多 9 张图
    images: Mapped[str] = mapped_column(Text, default="[]")
    # 仅自己可见：个人主页里的私密碎碎念
    is_private: Mapped[bool] = mapped_column(Boolean, default=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    like_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class MomentLike(Base):
    __tablename__ = "moment_likes"

    moment_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("moments.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
