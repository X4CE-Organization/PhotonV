"""初始化数据：超级管理员、分区、示例内容。"""
from __future__ import annotations

import shutil
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

import secrets
from datetime import timedelta

from . import models
from .config import ROOT_DIR, settings
from .security import hash_password
from .utils import now

CATEGORIES = [
    ("anime", "动画", "sparkles", "番剧、手书、MMD、动画短片"),
    ("game", "游戏", "gamepad", "实况、攻略、赛事与整活"),
    ("knowledge", "知识", "book", "科普、课程、学习笔记"),
    ("tech", "科技", "cpu", "数码、编程、硬件评测"),
    ("life", "生活", "home", "日常、Vlog、手工与宠物"),
    ("music", "音乐", "music", "翻唱、演奏、原创音乐"),
    ("film", "影视", "film", "剪辑、解说、影评"),
    ("food", "美食", "utensils", "探店、做饭、吃播"),
    ("sports", "运动", "dumbbell", "健身、球类、极限运动"),
    ("dance", "舞蹈", "activity", "宅舞、街舞、编舞"),
]

MEMBERSHIP_PLANS = [
    ("月度会员", 30, 1500, "专属标识 · 上传更大视频 · 可开播", 0),
    ("季度会员", 90, 4000, "月度会员全部权益，相当于每月 13.3 元", 1),
    ("年度会员", 365, 13800, "月度会员全部权益，相当于每月 11.5 元", 2),
]

DEMO_VIDEOS = [
    {
        "title": "【PhotonV 演示】弹幕、投币、收藏一次看懂",
        "description": "这是一条自动生成的示例视频，用来演示播放器、弹幕、评论、点赞与收藏等核心功能。\n\n"
        "你可以在后台「系统设置」里调整投稿审核、弹幕开关、硬币奖励等策略。",
        "category": "knowledge",
        "tags": ["PhotonV", "演示", "开源"],
        "views": 1280,
        "likes": 96,
        "coins": 42,
        "author": "root",
    },
    {
        "title": "从零搭一个微视频平台：技术选型与部署",
        "description": "FastAPI + Vue 3 + PostgreSQL 的一套完整实现，包含投稿审核、弹幕、收藏夹、举报与后台运维。",
        "category": "tech",
        "tags": ["FastAPI", "Vue3", "部署"],
        "views": 864,
        "likes": 71,
        "coins": 25,
        "author": "alice",
    },
    {
        "title": "三分钟看懂弹幕是怎么滚起来的",
        "description": "弹幕排布、去重与轨道分配的简单思路，附完整实现位置说明。",
        "category": "knowledge",
        "tags": ["弹幕", "前端"],
        "views": 523,
        "likes": 44,
        "coins": 12,
        "author": "bob",
    },
    {
        "title": "【Vlog】在服务器上折腾一整天",
        "description": "记录一次完整的部署过程：装数据库、配反向代理、开 HTTPS、迁移数据。",
        "category": "life",
        "tags": ["Vlog", "运维"],
        "views": 412,
        "likes": 33,
        "coins": 9,
        "author": "carol",
    },
    {
        "title": "开源社区是怎么运转的",
        "description": "从 issue、PR 到发版，聊聊一个开源项目需要哪些角色与流程。",
        "category": "knowledge",
        "tags": ["开源", "社区"],
        "views": 305,
        "likes": 28,
        "coins": 7,
        "author": "root",
    },
    {
        "title": "一分钟学会给视频做封面",
        "description": "封面决定点击率，这里有几条能立刻用上的构图与配色技巧。",
        "category": "tech",
        "tags": ["封面", "设计"],
        "views": 268,
        "likes": 22,
        "coins": 5,
        "author": "alice",
    },
]

DEMO_COMMENTS = [
    "这个平台看起来挺完整的，先占个楼。",
    "弹幕功能好用，希望能加个自定义颜色。",
    "已经在服务器上跑起来了，部署文档写得很清楚。",
    "UP 主更新好快，支持一下！",
    "收藏夹能不能支持多级分类？",
    "硬币不够了，明天再来投。",
]

DEMO_DANMAKU = [
    ("前方高能", 1.5, "#ffffff", "scroll"),
    ("这个功能好耶", 3.2, "#ff9d00", "scroll"),
    ("已三连", 5.6, "#00a1d6", "top"),
    ("开源的就是香", 8.4, "#7ac756", "scroll"),
    ("收藏了慢慢看", 11.0, "#ff6699", "bottom"),
]


def _cover_svg(title: str, subtitle: str, color: str, index: int) -> str:
    safe_title = title.replace("&", "＆").replace("<", "＜").replace(">", "＞")
    safe_sub = subtitle.replace("&", "＆").replace("<", "＜").replace(">", "＞")
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="960" height="540" viewBox="0 0 960 540">
  <defs>
    <linearGradient id="g{index}" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="{color}"/>
      <stop offset="100%" stop-color="#111827"/>
    </linearGradient>
  </defs>
  <rect width="960" height="540" fill="url(#g{index})"/>
  <circle cx="820" cy="90" r="150" fill="#ffffff" opacity="0.08"/>
  <circle cx="120" cy="470" r="200" fill="#ffffff" opacity="0.06"/>
  <text x="60" y="250" font-family="PingFang SC, Microsoft YaHei, sans-serif" font-size="54" font-weight="700" fill="#ffffff">{safe_title}</text>
  <text x="60" y="320" font-family="PingFang SC, Microsoft YaHei, sans-serif" font-size="28" fill="#ffffff" opacity="0.85">{safe_sub}</text>
  <text x="60" y="470" font-family="PingFang SC, Microsoft YaHei, sans-serif" font-size="26" fill="#ffffff" opacity="0.6">PhotonV</text>
</svg>
"""


def _write_covers() -> list[str]:
    covers: list[str] = []
    palette = ["#0ea5e9", "#6366f1", "#f97316", "#22c55e", "#ec4899", "#8b5cf6"]
    for index, item in enumerate(DEMO_VIDEOS):
        name = f"demo-{index + 1}.svg"
        target = settings.covers_dir / name
        if not target.exists():
            target.write_text(
                _cover_svg(item["title"][:16], item["category"], palette[index % len(palette)], index),
                encoding="utf-8",
            )
        covers.append(f"/media/covers/{name}")
    return covers


def _demo_video_file() -> str:
    """把仓库里自带的 CC0 示例视频复制到数据目录；没有就返回空。"""
    source = ROOT_DIR / "docs" / "demo" / "sample.mp4"
    if not source.exists():
        return ""
    target_dir = settings.videos_dir / "demo"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / "sample.mp4"
    if not target.exists():
        shutil.copyfile(source, target)
    return "/media/videos/demo/sample.mp4"


def ensure_seed(db: Session) -> None:
    # 超级管理员
    if not db.scalar(select(func.count(models.User.id))):
        root = models.User(
            username=settings.root_username,
            email=settings.root_email,
            password_hash=hash_password(settings.root_password),
            role="superadmin",
            display_name=settings.root_username,
            bio="PhotonV 超级管理员",
            coins=100,
        )
        db.add(root)
        db.commit()

    # 分区
    if not db.scalar(select(func.count(models.Category.id))):
        for sort, (slug, name, icon, description) in enumerate(CATEGORIES):
            db.add(models.Category(slug=slug, name=name, icon=icon, description=description, sort=sort))
        db.commit()

    # 会员套餐
    if not db.scalar(select(func.count(models.MembershipPlan.id))):
        for name, days, price, description, sort in MEMBERSHIP_PLANS:
            db.add(
                models.MembershipPlan(
                    name=name,
                    days=days,
                    price_cents=price,
                    description=description,
                    badge="大会员",
                    sort=sort,
                )
            )
        db.commit()

    # 示例用户
    if not db.scalar(select(models.User).where(models.User.username == "alice")):
        for name, bio in (
            ("alice", "喜欢折腾前端与设计"),
            ("bob", "后端工程师，专注性能优化"),
            ("carol", "记录生活，偶尔写点教程"),
        ):
            db.add(
                models.User(
                    username=name,
                    email=f"{name}@photonv.local",
                    password_hash=hash_password(settings.root_password),
                    display_name=name,
                    bio=bio,
                    coins=20,
                    email_verified=True,
                )
            )
        db.commit()
        for name in ("alice", "bob", "carol"):
            user = db.scalar(select(models.User).where(models.User.username == name))
            if user:
                db.add(models.FavoriteFolder(user_id=user.id, name="默认收藏夹", is_default=True))
        db.commit()

    # 超管：直播权限 + 会员身份
    root_user = db.scalar(select(models.User).where(models.User.username == settings.root_username))
    if root_user and not root_user.can_live:
        root_user.can_live = True
        root_user.coins = max(root_user.coins, 200)
        root_user.membership_level = 2
        root_user.membership_expires = now() + timedelta(days=365)
        db.commit()

    # 示例视频
    if not db.scalar(select(func.count(models.Video.id))):
        covers = _write_covers()
        media = _demo_video_file()
        users = {item.username: item for item in db.scalars(select(models.User)).all()}
        categories = {item.slug: item for item in db.scalars(select(models.Category)).all()}
        tag_cache: dict[str, models.Tag] = {}
        for index, item in enumerate(DEMO_VIDEOS):
            author = users.get(item["author"]) or users.get(settings.root_username)
            if not author:
                continue
            category = categories.get(item["category"])
            video = models.Video(
                author_id=author.id,
                title=item["title"],
                description=item["description"],
                cover=covers[index],
                source=media,
                duration=12 if media else 0,
                filesize=(ROOT_DIR / "docs" / "demo" / "sample.mp4").stat().st_size if media else 0,
                category_id=category.id if category else None,
                status="published",
                views=item["views"],
                likes=item["likes"],
                coins=item["coins"],
                favorites=index + 1,
                is_featured=index < 2,
                published_at=now(),
                transcode_status="skipped",
                transcode_error="示例视频跳过转码",
            )
            db.add(video)
            db.commit()
            db.refresh(video)
            for tag_name in item["tags"]:
                tag = tag_cache.get(tag_name)
                if not tag:
                    tag = db.scalar(select(models.Tag).where(models.Tag.name == tag_name))
                    if not tag:
                        tag = models.Tag(name=tag_name)
                        db.add(tag)
                        db.commit()
                        db.refresh(tag)
                    tag_cache[tag_name] = tag
                db.add(models.VideoTag(video_id=video.id, tag_id=tag.id))
                tag.use_count = (tag.use_count or 0) + 1
            author.video_count += 1
            author.like_count += item["likes"]
            author.play_count += item["views"]
            db.commit()

            # 评论
            for offset, text in enumerate(DEMO_COMMENTS[index % 3 : index % 3 + 3]):
                commenter = list(users.values())[(index + offset) % len(users)]
                db.add(
                    models.Comment(
                        video_id=video.id,
                        user_id=commenter.id,
                        content=text,
                        like_count=max(0, 18 - offset * 5),
                    )
                )
            video.comments = 3
            # 弹幕
            for content, time_seconds, color, mode in DEMO_DANMAKU:
                db.add(
                    models.Danmaku(
                        video_id=video.id,
                        user_id=author.id,
                        content=content,
                        time_seconds=time_seconds + index,
                        color=color,
                        mode=mode,
                    )
                )
            video.danmaku_count = len(DEMO_DANMAKU)
            db.commit()

    # 公告
    if not db.scalar(select(func.count(models.Announcement.id))):
        admin = db.scalar(select(models.User).where(models.User.role == "superadmin"))
        db.add(
            models.Announcement(
                title="PhotonV 上线啦",
                content="欢迎来到 PhotonV！这是一个完全开源的微视频平台，支持投稿、弹幕、评论、收藏与关注。\n\n"
                "投稿后需要管理员审核，审核通过即会自动公开。",
                type="notice",
                is_pinned=True,
                author_id=admin.id if admin else None,
            )
        )
        db.commit()

    # 轮播
    if not db.scalar(select(func.count(models.Carousel.id))):
        palette = ["#0ea5e9", "#6366f1", "#f97316"]
        for index, (title, subtitle) in enumerate(
            [
                ("欢迎来到 PhotonV", "开源微视频平台"),
                ("投稿你的第一条视频", "审核通过即自动公开"),
                ("弹幕、投币、收藏", "一个都不少"),
            ]
        ):
            name = f"banner-{index + 1}.svg"
            target = settings.covers_dir / name
            if not target.exists():
                target.write_text(_cover_svg(title, subtitle, palette[index], 90 + index), encoding="utf-8")
            db.add(
                models.Carousel(
                    title=title,
                    subtitle=subtitle,
                    image=f"/media/covers/{name}",
                    link="/",
                    sort=index,
                )
            )
        db.commit()

    # 示例直播间
    if not db.scalar(select(func.count(models.LiveRoom.id))):
        owner = db.scalar(select(models.User).where(models.User.username == settings.root_username))
        category = db.scalar(select(models.Category).where(models.Category.slug == "knowledge"))
        if owner:
            room = models.LiveRoom(
                owner_id=owner.id,
                title="PhotonV 直播间 · 随时来聊",
                cover="/media/covers/banner-1.svg",
                description="这是示例直播间。接入 nginx-rtmp / SRS 后填好推流地址即可开播。",
                category_id=category.id if category else None,
                stream_key=secrets.token_hex(12),
                play_url="",
                status="offline",
            )
            owner.stream_key = room.stream_key
            owner.can_live = True
            db.add(room)
            db.commit()
