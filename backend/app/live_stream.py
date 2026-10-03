"""直播接入层：对接 MediaMTX（也兼容 SRS 等提供同样 REST 接口的实现）。

两条推流路线，最终都落到同一个路径 `live/<stream_key>`：

1. **OBS / 专业推流软件** —— RTMP
   服务器 `rtmp://host:1935/live`，串流密钥填 `<stream_key>`
2. **浏览器直接开播（网页开播）** —— WHIP（WebRTC-HTTP ingest）
   `POST http://host:8889/live/<stream_key>/whip`，不需要装任何软件

播放端同样两条：

* WHEP（WebRTC 播放，延迟 1 秒内）—— `http://host:8889/live/<stream_key>/whep`
* HLS（兼容性最好，延迟 5-15 秒）—— `http://host:8888/live/<stream_key>/index.m3u8`

另外：

* `mediamtx_auth()` 是 MediaMTX 的鉴权回调，保证只有拿着正确串流密钥、
  且拥有开播权限的主播才能推流
* `sync_rooms()` 周期性向 MediaMTX 查一次「哪些路径正在推流」，
  用来把直播间状态自动切成 直播中 / 未开播——主播断开后不用手动点下播
"""
from __future__ import annotations

import json
import threading
import time
import urllib.error
import urllib.request

from sqlalchemy import select

from . import models, settings_store as site
from .database import SessionLocal
from .utils import now

PATH_PREFIX = "live/"
SYNC_INTERVAL = 5

_worker: threading.Thread | None = None
_stop = threading.Event()


# ------------------------------------------------------------------ 配置


def enabled() -> bool:
    return site.get_bool("live_ingest_enabled", True)


def api_base() -> str:
    return site.get_str("live_api_url", "").rstrip("/")


def rtmp_server() -> str:
    return site.get_str("live_rtmp_server", "").rstrip("/")


def whip_base() -> str:
    return site.get_str("live_whip_base", "").rstrip("/")


def whep_base() -> str:
    return site.get_str("live_whep_base", "").rstrip("/")


def hls_base() -> str:
    return site.get_str("live_hls_base", "").rstrip("/")


def room_path(room: models.LiveRoom) -> str:
    return f"{PATH_PREFIX}{room.stream_key}"


def urls_for(room: models.LiveRoom) -> dict:
    """主播 / 观众需要的全部地址。前缀没配就返回空串，前端据此隐藏入口。"""
    key = room.stream_key or ""
    path = room_path(room) if key else ""
    rtmp = rtmp_server()
    return {
        "streamKey": key,
        # OBS：服务器 + 串流密钥
        "rtmpServer": f"{rtmp}/{PATH_PREFIX.rstrip('/')}" if rtmp else "",
        "rtmpUrl": f"{rtmp}/{path}" if rtmp and path else "",
        # 浏览器开播
        "whipUrl": f"{whip_base()}/{path}/whip" if whip_base() and path else "",
        # 播放
        "whepUrl": f"{whep_base()}/{path}/whep" if whep_base() and path else "",
        "hlsUrl": f"{hls_base()}/{path}/index.m3u8" if hls_base() and path else "",
        "rtspUrl": f"rtsp://{_rtsp_host()}/{path}" if path else "",
    }


def _rtsp_host() -> str:
    base = rtmp_server()
    if not base:
        return ""
    # example: rtmp://live.example.com:1935 -> live.example.com:8554
    host = base.split("://", 1)[-1].split("/")[0].split(":")[0]
    return f"{host}:8554"


# ------------------------------------------------------------------ REST 查询


def list_paths(timeout: float = 3.0) -> list[dict] | None:
    """向 MediaMTX 查询当前所有路径；没配置或连不上返回 None。"""
    base = api_base()
    if not base:
        return None
    try:
        request = urllib.request.Request(f"{base}/v3/paths/list", method="GET")
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read() or b"{}")
        items = data.get("items")
        return items if isinstance(items, list) else []
    except (urllib.error.URLError, TimeoutError, ValueError, OSError):
        return None


def reachable() -> dict:
    """给后台「缓存与转码」页展示媒体服务器状态。"""
    if not enabled():
        return {"enabled": False, "reachable": False, "paths": 0, "message": "内置推流接入未启用"}
    if not api_base():
        return {"enabled": True, "reachable": False, "paths": 0, "message": "没有配置媒体服务器 API 地址"}
    items = list_paths()
    if items is None:
        return {"enabled": True, "reachable": False, "paths": 0, "message": "连不上媒体服务器"}
    live = [item for item in items if str(item.get("name", "")).startswith(PATH_PREFIX) and item.get("ready")]
    return {
        "enabled": True,
        "reachable": True,
        "paths": len(items),
        "publishing": len(live),
        "message": f"正常，{len(live)} 路正在推流",
    }


def publishing_map() -> dict[str, str]:
    """{stream_key: 推流来源类型}，只包含正在推流的路径。"""
    items = list_paths()
    if not items:
        return {}
    result: dict[str, str] = {}
    for item in items:
        name = str(item.get("name") or "")
        if not name.startswith(PATH_PREFIX) or not item.get("ready"):
            continue
        source = item.get("source") or {}
        kind = str(source.get("type") or "")
        # rtmpConn / rtmpSource / webrtcSession / rtspSession / srtConn ...
        if kind.startswith("rtmp"):
            label = "rtmp"
        elif kind.startswith("webrtc"):
            label = "whip"
        elif kind.startswith("srt"):
            label = "srt"
        else:
            label = kind or "unknown"
        result[name[len(PATH_PREFIX):]] = label
    return result


# ------------------------------------------------------------------ 状态同步


def sync_rooms(db) -> int:
    """把「正在推流的路径」同步到直播间状态，返回发生变化的房间数。"""
    if not enabled() or not api_base():
        return 0
    active = publishing_map()
    rooms = db.scalars(select(models.LiveRoom)).all()
    changed = 0
    for room in rooms:
        if room.status == "banned" or not room.stream_key:
            continue
        kind = active.get(room.stream_key)
        if kind and room.status != "live":
            room.status = "live"
            room.stream_source = kind
            room.started_at = now()
            room.ended_at = None
            changed += 1
        elif not kind and room.status == "live" and room.stream_source:
            # 只自动下线「由推流带起来」的直播，手动开播的不受影响
            room.status = "offline"
            room.stream_source = ""
            room.ended_at = now()
            changed += 1
    if changed:
        db.commit()
    return changed


def check_publish_allowed(db, stream_key: str) -> tuple[bool, str]:
    """推流鉴权：返回 (是否允许, 拒绝原因)。"""
    if not enabled():
        return False, "本站未启用内置推流"
    key = (stream_key or "").strip()
    if not key:
        return False, "缺少串流密钥"
    room = db.scalar(select(models.LiveRoom).where(models.LiveRoom.stream_key == key))
    if not room:
        return False, "串流密钥无效"
    if room.status == "banned":
        return False, "该直播间已被封禁"
    owner = db.get(models.User, room.owner_id)
    if not owner or owner.is_banned:
        return False, "账号不可用"
    if site.get_bool("live_need_approval", True) and not (owner.can_live or owner.is_admin):
        return False, "还没有开播权限"
    if site.get_bool("live_member_only", False) and owner.membership_level <= 0 and not owner.is_admin:
        return False, "仅会员可以开播"
    max_hours = site.get_int("live_max_hours", 12)
    if room.started_at and room.status == "live" and max_hours > 0:
        elapsed = (now() - room.started_at).total_seconds() / 3600
        if elapsed > max_hours:
            return False, f"单场直播最长 {max_hours} 小时"
    return True, ""


# ------------------------------------------------------------------ 后台轮询


def _loop() -> None:
    while not _stop.is_set():
        try:
            if enabled() and api_base():
                db = SessionLocal()
                try:
                    sync_rooms(db)
                finally:
                    db.close()
        except Exception:  # noqa: BLE001 - 轮询失败不影响主进程
            pass
        _stop.wait(SYNC_INTERVAL)


def start_worker() -> None:
    global _worker
    if _worker and _worker.is_alive():
        return
    _stop.clear()
    _worker = threading.Thread(target=_loop, name="photonv-live-sync", daemon=True)
    _worker.start()


def stop_worker() -> None:
    _stop.set()


def status() -> dict:
    info = reachable()
    return {
        **info,
        "rtmpServer": rtmp_server(),
        "whipBase": whip_base(),
        "hlsBase": hls_base(),
    }


def wait_ready(seconds: float = 0.05) -> None:
    """测试用：让轮询线程有机会跑一轮。"""
    time.sleep(seconds)
