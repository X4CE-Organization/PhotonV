"""站点设置的读写与缓存。"""
from __future__ import annotations

import json
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models
from .settings_registry import SETTING_MAP, SETTINGS, PUBLIC_KEYS

_cache: dict[str, Any] = {}


def _serialize(value: Any, type_: str) -> str:
    if type_ == "boolean":
        return "true" if value else "false"
    if type_ == "json":
        return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    return "" if value is None else str(value)


def _parse(raw: Optional[str], field: dict) -> Any:
    if raw is None:
        return field["default"]
    type_ = field["type"]
    if type_ == "boolean":
        return raw.lower() in {"1", "true", "yes", "on"}
    if type_ == "number":
        try:
            return int(float(raw))
        except ValueError:
            return field["default"]
    if type_ == "json":
        try:
            return json.loads(raw)
        except (ValueError, TypeError):
            return field["default"]
    return raw


def warm(db: Session) -> None:
    """把数据库里的设置读进内存缓存。"""
    rows = {row.key: row.value for row in db.scalars(select(models.Setting)).all()}
    _cache.clear()
    for field in SETTINGS:
        key = field["key"]
        if key in rows:
            _cache[key] = _parse(rows[key], field)
        elif field["type"] == "password":
            _cache[key] = ""
        else:
            _cache[key] = field["default"]


def get(key: str, default: Any = None) -> Any:
    if key in _cache:
        return _cache[key]
    field = SETTING_MAP.get(key)
    return field["default"] if field else default


def get_str(key: str, default: str = "") -> str:
    value = get(key, default)
    return default if value is None else str(value)


def get_int(key: str, default: int = 0) -> int:
    try:
        return int(get(key, default))
    except (TypeError, ValueError):
        return default


def get_bool(key: str, default: bool = False) -> bool:
    value = get(key, default)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in {"1", "true", "yes", "on"}
    return bool(value)


def get_json(key: str, default: Any = None) -> Any:
    value = get(key, default)
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (ValueError, TypeError):
            return default
    return value if value is not None else default


def all_settings(mask_secrets: bool = False) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for field in SETTINGS:
        value = get(field["key"])
        if mask_secrets and field.get("secret") and value:
            out[field["key"]] = "********"
        else:
            out[field["key"]] = value
    return out


def public_settings() -> dict[str, Any]:
    return {key: get(key) for key in PUBLIC_KEYS}


def update(db: Session, patch: dict[str, Any]) -> list[str]:
    changed: list[str] = []
    for key, value in patch.items():
        field = SETTING_MAP.get(key)
        if not field:
            continue
        if field["type"] == "number":
            try:
                value = int(float(value))
            except (TypeError, ValueError):
                continue
            if "min" in field:
                value = max(field["min"], value)
            if "max" in field:
                value = min(field["max"], value)
        current = get(key)
        if current == value:
            continue
        raw = _serialize(value, field["type"])
        row = db.get(models.Setting, key)
        if row:
            row.value = raw
        else:
            db.add(models.Setting(key=key, value=raw))
        _cache[key] = value
        changed.append(key)
    if changed:
        db.commit()
    return changed


def reset(db: Session, keys: Optional[list[str]] = None) -> None:
    targets = keys or [field["key"] for field in SETTINGS]
    for key in targets:
        row = db.get(models.Setting, key)
        if row:
            db.delete(row)
        _cache.pop(key, None)
    db.commit()
    warm(db)
