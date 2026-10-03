"""WebSocket 实时通道：私信、直播间聊天、在线人数。

单进程时直接在内存里广播；配了 Redis 会通过 Pub/Sub 转发给其他进程，
所以多副本部署时消息也不会丢。
"""
from __future__ import annotations

from collections import defaultdict

from fastapi import WebSocket

from . import redis_client as redis

_rooms: dict = defaultdict(set)
_users: dict = defaultdict(set)


async def join_room(room: str, socket: WebSocket) -> None:
    _rooms[room].add(socket)


async def leave_room(room: str, socket: WebSocket) -> None:
    _rooms[room].discard(socket)
    if not _rooms[room]:
        _rooms.pop(room, None)


async def join_user(user_id: int, socket: WebSocket) -> None:
    _users[user_id].add(socket)


async def leave_user(user_id: int, socket: WebSocket) -> None:
    _users[user_id].discard(socket)
    if not _users[user_id]:
        _users.pop(user_id, None)


async def broadcast(room: str, payload: dict, forward: bool = True) -> None:
    for socket in list(_rooms.get(room, ())):
        try:
            await socket.send_json(payload)
        except Exception:  # noqa: BLE001
            await leave_room(room, socket)
    if forward:
        redis.publish(f"ws:{room}", payload)


async def send_to_user(user_id: int, payload: dict, forward: bool = True) -> None:
    for socket in list(_users.get(user_id, ())):
        try:
            await socket.send_json(payload)
        except Exception:  # noqa: BLE001
            await leave_user(user_id, socket)
    if forward:
        redis.publish(f"ws:user:{user_id}", payload)


def deliver_local(channel: str, payload: dict) -> None:
    """Redis 订阅回调：把别的进程发来的消息投给本机连接。"""
    import asyncio

    if channel.startswith("ws:user:"):
        try:
            user_id = int(channel.split(":")[-1])
        except ValueError:
            return
        sockets = list(_users.get(user_id, ()))
    elif channel.startswith("ws:"):
        sockets = list(_rooms.get(channel[3:], ()))
    else:
        return
    if not sockets:
        return
    try:
        loop = asyncio.get_event_loop_policy().get_event_loop()
    except Exception:  # noqa: BLE001
        return
    if not loop or loop.is_closed():
        return
    for socket in sockets:
        try:
            asyncio.run_coroutine_threadsafe(socket.send_json(payload), loop)
        except Exception:  # noqa: BLE001
            continue


def stats() -> dict:
    return {"rooms": len(_rooms), "connections": sum(len(item) for item in _rooms.values())}
