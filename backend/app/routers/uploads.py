"""文件上传：头像 / 封面 / 视频。"""
from __future__ import annotations

import secrets
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile

from .. import models, settings_store as site
from ..config import settings
from ..security import require_user
from ..utils import fail

router = APIRouter(prefix="/api/upload", tags=["upload"])

IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/svg+xml": ".svg",
}
VIDEO_TYPES = {
    "video/mp4": ".mp4",
    "video/webm": ".webm",
    "video/quicktime": ".mov",
    "video/x-matroska": ".mkv",
    "video/x-m4v": ".m4v",
}


def _timestamp() -> str:
    return datetime.utcnow().strftime("%Y%m%d%H%M%S")


def _name(original: str, suffix: str) -> str:
    return f"{_timestamp()}-{secrets.token_hex(4)}{suffix}"


async def _save(file: UploadFile, directory: Path, url_prefix: str, allowed: dict, max_mb: int) -> dict:
    suffix = allowed.get((file.content_type or "").lower())
    if not suffix:
        suffix = Path(file.filename or "").suffix.lower()
        if suffix not in allowed.values():
            raise fail(400, "不支持的文件格式")
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / _name(file.filename or "", suffix)
    size = 0
    limit = max_mb * 1024 * 1024
    with target.open("wb") as handle:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > limit:
                handle.close()
                target.unlink(missing_ok=True)
                raise fail(400, f"文件超过 {max_mb} MB 限制")
            handle.write(chunk)
    await file.close()
    return {"url": f"{url_prefix}/{target.name}", "size": size, "name": target.name}


def _check_extensions(suffix: str, key: str, message: str) -> None:
    allowed = [str(item).lower().lstrip(".") for item in (site.get_json(key, []) or [])]
    if allowed and suffix.lstrip(".").lower() not in allowed:
        raise fail(400, message)


@router.post("/image")
async def upload_image(
    file: UploadFile = File(...),
    user: models.User = Depends(require_user),
):
    max_mb = site.get_int("max_image_mb", settings.max_image_mb)
    result = await _save(file, settings.covers_dir, "/media/covers", IMAGE_TYPES, max_mb)
    _check_extensions(Path(result["name"]).suffix, "image_extensions", "该图片格式不被允许")
    return result


@router.post("/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    user: models.User = Depends(require_user),
):
    max_mb = site.get_int("max_image_mb", settings.max_image_mb)
    return await _save(file, settings.avatars_dir, "/media/avatars", IMAGE_TYPES, max_mb)


@router.post("/video")
async def upload_video(
    file: UploadFile = File(...),
    user: models.User = Depends(require_user),
):
    if not site.get_bool("allow_upload", True):
        raise fail(403, "本站已关闭投稿")
    max_mb = site.get_int("max_video_mb", settings.max_video_mb)
    allowed = dict(VIDEO_TYPES)
    extensions = [str(item).lower().lstrip(".") for item in (site.get_json("video_extensions", []) or [])]
    result = await _save(file, settings.videos_dir, "/media/videos", allowed, max_mb)
    _check_extensions(Path(result["name"]).suffix, "video_extensions",
                      f"只允许上传 {'、'.join(extensions)} 格式的视频")
    return result
