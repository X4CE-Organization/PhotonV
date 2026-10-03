"""站点根目录的 SEO 资源：sitemap.xml / rss.xml / robots.txt。

这些路径不带 /api 前缀，必须在 SPA 兜底路由之前注册。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, settings_store as site
from ..database import get_db

router = APIRouter(tags=["seo"])


def _base() -> str:
    return site.get_str("site_url", "").rstrip("/") or "http://localhost"


def _escape(text: object) -> str:
    return (
        str(text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


@router.get("/sitemap.xml", include_in_schema=False)
def sitemap(db: Session = Depends(get_db)):
    base = _base()
    videos = db.scalars(
        select(models.Video)
        .where(models.Video.status == "published", models.Video.deleted_at.is_(None))
        .order_by(models.Video.id.desc())
        .limit(5000)
    ).all()
    users = db.scalars(select(models.User).where(models.User.is_banned.is_(False)).limit(2000)).all()
    categories = db.scalars(select(models.Category).where(models.Category.is_active.is_(True))).all()
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for path in ("/", "/rank", "/live"):
        lines.append(f"<url><loc>{base}{path}</loc></url>")
    for item in categories:
        lines.append(f"<url><loc>{base}/category/{_escape(item.slug)}</loc></url>")
    for item in videos:
        stamp = item.published_at or item.created_at
        lastmod = stamp.strftime("%Y-%m-%d") if stamp else ""
        lines.append(f"<url><loc>{base}/video/{item.id}</loc><lastmod>{lastmod}</lastmod></url>")
    for item in users:
        lines.append(f"<url><loc>{base}/space/{_escape(item.username)}</loc></url>")
    lines.append("</urlset>")
    return Response("\n".join(lines), media_type="application/xml")


@router.get("/rss.xml", include_in_schema=False)
def rss(db: Session = Depends(get_db)):
    base = _base()
    name = site.get_str("site_name", "PhotonV")
    desc = site.get_str("site_description", "")
    rows = db.scalars(
        select(models.Video)
        .where(models.Video.status == "published", models.Video.deleted_at.is_(None))
        .order_by(models.Video.id.desc())
        .limit(50)
    ).all()
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0"><channel>',
        f"<title>{_escape(name)}</title>",
        f"<link>{base}</link>",
        f"<description>{_escape(desc)}</description>",
    ]
    for item in rows:
        stamp = item.published_at or item.created_at
        published = stamp.strftime("%a, %d %b %Y %H:%M:%S +0000") if stamp else ""
        lines.append(
            "<item>"
            f"<title>{_escape(item.title)}</title>"
            f"<link>{base}/video/{item.id}</link>"
            f"<guid>{base}/video/{item.id}</guid>"
            f"<author>{_escape(item.author.username if item.author else '')}</author>"
            f"<pubDate>{published}</pubDate>"
            f"<description>{_escape((item.description or '')[:300])}</description>"
            "</item>"
        )
    lines.append("</channel></rss>")
    return Response("\n".join(lines), media_type="application/rss+xml")


@router.get("/robots.txt", include_in_schema=False)
def robots():
    base = _base()
    body = "\n".join(
        [
            "User-agent: *",
            "Allow: /",
            "Disallow: /admin",
            "Disallow: /settings",
            "Disallow: /messages",
            f"Sitemap: {base}/sitemap.xml",
            "",
        ]
    )
    return Response(body, media_type="text/plain")
