"""视频转码与多清晰度（ffmpeg）。

- 上传完成后视频进入待转码队列，后台线程逐个处理
- 产出 360p / 480p / 720p 多清晰度 mp4 + HLS（m3u8 + 分片）
- 没有安装 ffmpeg 时标记为 skipped，播放器直接用原始文件，不影响使用
"""
from __future__ import annotations

import shutil
import subprocess
import threading
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models
from .config import settings
from .database import SessionLocal

VARIANTS = [
    ("360p", "640:360", "800k", "96k"),
    ("480p", "854:480", "1200k", "128k"),
    ("720p", "1280:720", "2500k", "128k"),
]

_worker = None
_stop = threading.Event()
_ffmpeg_cache = None


def ffmpeg_path():
    """按 FFMPEG_BIN → 系统 PATH → imageio-ffmpeg 的顺序查找 ffmpeg。"""
    global _ffmpeg_cache
    if _ffmpeg_cache is not None:
        return _ffmpeg_cache or None
    if settings.ffmpeg_bin:
        _ffmpeg_cache = settings.ffmpeg_bin
        return _ffmpeg_cache
    found = shutil.which("ffmpeg")
    if found:
        _ffmpeg_cache = found
        return found
    try:  # 本地开发时的可选依赖
        import imageio_ffmpeg  # type: ignore

        _ffmpeg_cache = imageio_ffmpeg.get_ffmpeg_exe()
        return _ffmpeg_cache
    except Exception:  # noqa: BLE001
        _ffmpeg_cache = ""
        return None


def available() -> bool:
    return bool(ffmpeg_path())


def _run(args):
    try:
        result = subprocess.run(args, capture_output=True, timeout=60 * 60)
        if result.returncode != 0:
            tail = (result.stderr or b"").decode("utf-8", "ignore")[-400:]
            return False, tail
        return True, ""
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def probe(path: Path) -> dict:
    """用 ffmpeg 读时长与分辨率（不依赖 ffprobe）。"""
    ffmpeg = ffmpeg_path()
    if not ffmpeg:
        return {}
    try:
        result = subprocess.run([ffmpeg, "-i", str(path)], capture_output=True, timeout=60)
        text = (result.stderr or b"").decode("utf-8", "ignore")
    except Exception:  # noqa: BLE001
        return {}
    info = {}
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("Duration:"):
            stamp = line.split("Duration:")[1].split(",")[0].strip()
            try:
                hours, minutes, seconds = stamp.split(":")
                info["duration"] = int(float(hours) * 3600 + float(minutes) * 60 + float(seconds))
            except ValueError:
                pass
        if "Video:" in line and "x" in line:
            for token in line.split(","):
                token = token.strip().split(" ")[0]
                if "x" in token and token.replace("x", "").isdigit():
                    width, height = token.split("x")
                    info["width"] = int(width)
                    info["height"] = int(height)
                    break
    return info


def grab_cover(source: Path, target: Path, at_seconds: int = 1) -> bool:
    ffmpeg = ffmpeg_path()
    if not ffmpeg:
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    ok, _ = _run(
        [ffmpeg, "-y", "-ss", str(at_seconds), "-i", str(source), "-frames:v", "1", "-q:v", "3", str(target)]
    )
    return ok


def transcode_video(db: Session, video: models.Video, log=print) -> None:
    """把一个视频转成多清晰度 + HLS，并写入 video_variants。"""
    ffmpeg = ffmpeg_path()
    if not ffmpeg or not video.source:
        video.transcode_status = "skipped"
        video.transcode_error = "未找到 ffmpeg 或没有本站源文件"
        db.commit()
        return
    source_path = settings.data_dir / video.source.replace("/media/", "", 1)
    if not source_path.exists():
        video.transcode_status = "skipped"
        video.transcode_error = "源文件不存在"
        db.commit()
        return

    video.transcode_status = "processing"
    video.transcode_error = ""
    db.commit()

    info = probe(source_path)
    if info.get("duration") and not video.duration:
        video.duration = info["duration"]
    if info.get("width"):
        video.width = info["width"]
        video.height = info["height"]
        if not video.cover:
            cover = settings.covers_dir / f"video-{video.id}.jpg"
            if grab_cover(source_path, cover, max(1, (info.get("duration") or 4) // 3)):
                video.cover = f"/media/covers/{cover.name}"
    db.commit()

    out_dir = settings.processed_dir / str(video.id)
    out_dir.mkdir(parents=True, exist_ok=True)
    source_height = info.get("height") or 0

    db.query(models.VideoVariant).filter(models.VideoVariant.video_id == video.id).delete()
    db.commit()

    produced = []
    for quality, scale, bitrate, audio in VARIANTS:
        target_height = int(scale.split(":")[1])
        if source_height and source_height < target_height * 0.9:
            continue
        target = out_dir / f"{quality}.mp4"
        ok, error = _run(
            [
                ffmpeg, "-y", "-i", str(source_path),
                "-vf", f"scale={scale}:force_original_aspect_ratio=decrease,pad={scale}:(ow-iw)/2:(oh-ih)/2",
                "-c:v", "libx264", "-preset", "veryfast", "-b:v", bitrate,
                "-c:a", "aac", "-b:a", audio, "-movflags", "+faststart", str(target),
            ]
        )
        if not ok:
            log(f"[transcode] {video.id} {quality} 失败：{error[-160:]}")
            continue
        produced.append(
            {
                "quality": quality,
                "label": quality,
                "path": f"/media/processed/{video.id}/{target.name}",
                "filesize": target.stat().st_size,
                "width": int(scale.split(":")[0]),
                "height": target_height,
            }
        )

    base = out_dir / "720p.mp4"
    if not base.exists():
        base = source_path
    playlist = out_dir / "index.m3u8"
    ok, error = _run(
        [
            ffmpeg, "-y", "-i", str(base),
            "-c", "copy", "-f", "hls",
            "-hls_time", str(settings.hls_segment_seconds),
            "-hls_playlist_type", "vod",
            "-hls_segment_filename", str(out_dir / "seg-%03d.ts"),
            str(playlist),
        ]
    )
    if ok:
        video.hls_path = f"/media/processed/{video.id}/index.m3u8"
    else:
        log(f"[transcode] {video.id} HLS 失败：{error[-160:]}")

    for item in produced:
        db.add(models.VideoVariant(video_id=video.id, **item))
    video.transcode_status = "done" if (produced or video.hls_path) else "failed"
    if video.transcode_status == "failed":
        video.transcode_error = "转码未产生任何清晰度"
    db.commit()
    log(f"[transcode] 视频 {video.id} 完成，产出 {len(produced)} 个清晰度")


def _loop() -> None:
    while not _stop.is_set():
        db = SessionLocal()
        try:
            video = db.scalar(
                select(models.Video)
                .where(
                    models.Video.transcode_status == "pending",
                    models.Video.source != "",
                    models.Video.deleted_at.is_(None),
                )
                .order_by(models.Video.id.asc())
                .limit(1)
            )
            if video:
                transcode_video(db, video)
                continue
        except Exception as exc:  # noqa: BLE001
            print(f"[transcode] 队列异常：{exc}")
        finally:
            db.close()
        _stop.wait(6)


def start_worker() -> None:
    global _worker
    if _worker or not settings.transcode_enabled:
        return
    _worker = threading.Thread(target=_loop, daemon=True, name="transcode-worker")
    _worker.start()


def stop_worker() -> None:
    _stop.set()


def enqueue(db: Session, video: models.Video) -> None:
    video.transcode_status = "pending"
    video.transcode_error = ""
    db.commit()


def variants_of(db: Session, video_id: int) -> list:
    rows = db.scalars(
        select(models.VideoVariant)
        .where(models.VideoVariant.video_id == video_id)
        .order_by(models.VideoVariant.height.asc())
    ).all()
    return [
        {
            "quality": item.quality,
            "label": item.label or item.quality,
            "url": item.path,
            "filesize": item.filesize,
            "width": item.width,
            "height": item.height,
        }
        for item in rows
    ]


def status() -> dict:
    path = ffmpeg_path()
    version = ""
    if path:
        try:
            result = subprocess.run([path, "-version"], capture_output=True, timeout=20)
            version = (result.stdout or b"").decode("utf-8", "ignore").splitlines()[0][:120]
        except Exception:  # noqa: BLE001
            version = ""
    return {"available": bool(path), "path": path or "", "version": version}
