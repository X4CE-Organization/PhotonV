"""Redis 集成（可选）。

配置 REDIS_URL 后启用，用于：
  - 热点接口缓存（首页 / 元数据）
  - 分布式限流（多进程共享计数）
  - 在线人数统计
  - 实时消息广播（私信、直播间聊天、转码队列唤醒）

没配置或连不上时全部安全降级，功能不受影响。
"""
from __future__ import annotations

import json
import time
from typing import Any, Callable, Optional

from .config import settings

try:  # redis 是可选依赖
    import redis as redis_lib
except Exception:  # pragma: no cover
    redis_lib = None  # type: ignore

_client: Any = None
_ready = False
_last_error = ""
ONLINE_KEY = "photonv:online"
LAST_SEEN: dict[int, float] = {}


def init() -> None:
    """尝试连接 Redis（失败只记录，不影响启动）。"""
    global _client, _ready, _last_error
    if not settings.redis_url or redis_lib is None:
        return
    try:
        _client = redis_lib.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=3,
            health_check_interval=30,
        )
        _client.ping()
        _ready = True
        _last_error = ""
    except Exception as exc:  # noqa: BLE001
        _client = None
        _ready = False
        _last_error = str(exc)
        print(f"[photonv] Redis 连接失败，使用内置回退方案：{exc}")


def enabled() -> bool:
    return bool(settings.redis_url)


def ready() -> bool:
    return _ready


def last_error() -> str:
    return _last_error


def client() -> Optional[Any]:
    return _client if _ready else None


# ------------------------------------------------------------------ 缓存


def cache_get(key: str) -> Optional[Any]:
    redis = client()
    if not redis:
        return None
    try:
        value = redis.get(key)
        return json.loads(value) if value else None
    except Exception:  # noqa: BLE001
        return None


def cache_set(key: str, value: Any, ttl: Optional[int] = None) -> None:
    redis = client()
    if not redis or (ttl if ttl is not None else settings.cache_ttl) <= 0:
        return
    try:
        redis.set(key, json.dumps(value, ensure_ascii=False), ex=max(1, ttl or settings.cache_ttl))
    except Exception:  # noqa: BLE001
        pass


def cache_clear(prefix: str = "photonv:cache:") -> int:
    redis = client()
    if not redis:
        return 0
    removed = 0
    try:
        for key in redis.scan_iter(match=f"{prefix}*", count=200):
            redis.delete(key)
            removed += 1
    except Exception:  # noqa: BLE001
        pass
    return removed


# ------------------------------------------------------------ 分布式限流


def rate_limit(key: str, interval_seconds: int) -> Optional[bool]:
    """返回 True/False；未启用 Redis 时返回 None，由调用方走内存实现。"""
    redis = client()
    if not redis or interval_seconds <= 0:
        return None
    try:
        full = f"photonv:rl:{key}"
        if redis.set(full, "1", nx=True, ex=max(1, int(interval_seconds))):
            return True
        return False
    except Exception:  # noqa: BLE001
        return None


def counter_incr(key: str, ttl: int) -> Optional[int]:
    redis = client()
    if not redis:
        return None
    try:
        full = f"photonv:cnt:{key}"
        value = redis.incr(full)
        if value == 1:
            redis.expire(full, max(1, ttl))
        return int(value)
    except Exception:  # noqa: BLE001
        return None


def counter_get(key: str) -> Optional[int]:
    redis = client()
    if not redis:
        return None
    try:
        value = redis.get(f"photonv:cnt:{key}")
        return int(value) if value is not None else 0
    except Exception:  # noqa: BLE001
        return None


def counter_reset(key: str) -> None:
    redis = client()
    if not redis:
        return
    try:
        redis.delete(f"photonv:cnt:{key}")
    except Exception:  # noqa: BLE001
        pass


def top_counters(prefix: str, limit: int = 10) -> list[dict[str, Any]]:
    """取出计数最高的若干个 key（用于热搜词）。没启用 Redis 时返回空列表。"""
    redis = client()
    if not redis:
        return []
    try:
        rows: list[dict[str, Any]] = []
        for key in redis.scan_iter(match=f"photonv:cnt:{prefix}*", count=500):
            try:
                value = int(redis.get(key) or 0)
            except (TypeError, ValueError):
                continue
            rows.append({"keyword": key.split(prefix, 1)[-1], "count": value, "source": "search"})
        rows.sort(key=lambda item: item["count"], reverse=True)
        return rows[: max(1, limit)]
    except Exception:  # noqa: BLE001
        return []


# ------------------------------------------------------------ 在线人数


def touch_online(user_id: int) -> None:
    redis = client()
    now = time.time()
    if LAST_SEEN.get(user_id, 0) > now - 60:
        return
    LAST_SEEN[user_id] = now
    if len(LAST_SEEN) > 5000:
        for key in [k for k, v in LAST_SEEN.items() if v < now - 600]:
            LAST_SEEN.pop(key, None)
    if not redis:
        return
    try:
        redis.zadd(ONLINE_KEY, {str(user_id): now})
        redis.zremrangebyscore(ONLINE_KEY, 0, now - 300)
    except Exception:  # noqa: BLE001
        pass


def online_count() -> Optional[int]:
    redis = client()
    if not redis:
        return None
    try:
        redis.zremrangebyscore(ONLINE_KEY, 0, time.time() - 300)
        return int(redis.zcard(ONLINE_KEY))
    except Exception:  # noqa: BLE001
        return None


# ------------------------------------------------------------ 发布 / 订阅


def publish(channel: str, payload: dict) -> None:
    redis = client()
    if not redis:
        return
    try:
        redis.publish(f"photonv:{channel}", json.dumps(payload, ensure_ascii=False))
    except Exception:  # noqa: BLE001
        pass


def subscribe_worker(handler: Callable[[str, dict], None]) -> Any:
    """后台线程里订阅 Redis 频道，用于多进程广播（私信、弹幕、直播聊天）。"""
    if not settings.redis_url or redis_lib is None:
        return None

    import threading

    def run() -> None:
        while True:
            try:
                pubsub = redis_lib.from_url(settings.redis_url, decode_responses=True).pubsub()
                pubsub.psubscribe("photonv:*")
                for message in pubsub.listen():
                    if message.get("type") != "pmessage":
                        continue
                    channel = str(message.get("channel", "")).removeprefix("photonv:")
                    try:
                        handler(channel, json.loads(message.get("data") or "{}"))
                    except Exception:  # noqa: BLE001
                        continue
            except Exception:  # noqa: BLE001
                time.sleep(3)

    thread = threading.Thread(target=run, daemon=True, name="redis-subscriber")
    thread.start()
    return thread


def info() -> dict:
    redis = client()
    if not redis:
        return {
            "enabled": enabled(),
            "connected": False,
            "error": _last_error or ("未配置 REDIS_URL" if not enabled() else "连接中"),
        }
    try:
        server = redis.info("server")
        memory = redis.info("memory")
        return {
            "enabled": True,
            "connected": True,
            "version": server.get("redis_version"),
            "memory": memory.get("used_memory_human"),
            "keys": int(redis.dbsize()),
            "online": online_count(),
        }
    except Exception as exc:  # noqa: BLE001
        return {"enabled": True, "connected": False, "error": str(exc)}
