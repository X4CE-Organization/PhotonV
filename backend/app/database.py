"""数据库连接、会话管理与备份。"""
from __future__ import annotations

import subprocess
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True, pool_size=10, max_overflow=20)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Iterator[Session]:
    """FastAPI 依赖：每个请求一个会话。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """建表（幂等）。"""
    from . import models  # noqa: F401  确保模型已注册

    Base.metadata.create_all(bind=engine)
    ensure_columns()


# 老库补列：新增字段时加到这里，已存在会报错并跳过，不影响启动。
COLUMN_MIGRATIONS: list[tuple[str, str]] = [
    ("users", "membership_level INTEGER NOT NULL DEFAULT 0"),
    ("users", "membership_expires TIMESTAMP"),
    ("users", "total_earned INTEGER NOT NULL DEFAULT 0"),
    ("users", "can_live BOOLEAN NOT NULL DEFAULT false"),
    ("users", "stream_key VARCHAR(64) NOT NULL DEFAULT ''"),
    ("users", "email_verified BOOLEAN NOT NULL DEFAULT false"),
    ("users", "mail_optout BOOLEAN NOT NULL DEFAULT false"),
    ("users", "last_bonus_date VARCHAR(16) NOT NULL DEFAULT ''"),
    ("users", "phone VARCHAR(32)"),
    ("users", "phone_verified BOOLEAN NOT NULL DEFAULT false"),
    ("videos", "transcode_status VARCHAR(16) NOT NULL DEFAULT 'pending'"),
    ("videos", "transcode_error VARCHAR(500) NOT NULL DEFAULT ''"),
    ("videos", "hls_path VARCHAR(500) NOT NULL DEFAULT ''"),
    ("orders", "trade_no VARCHAR(64) NOT NULL DEFAULT ''"),
    ("orders", "pay_payload TEXT NOT NULL DEFAULT ''"),
]

# 索引迁移（幂等）
INDEX_MIGRATIONS: list[str] = [
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_phone ON users(phone) WHERE phone IS NOT NULL",
    "CREATE INDEX IF NOT EXISTS idx_sms_codes_phone ON sms_codes(phone, purpose, used)",
]


def ensure_columns() -> None:
    for table, definition in COLUMN_MIGRATIONS:
        try:
            with engine.begin() as connection:
                connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {definition}"))
        except Exception:  # noqa: BLE001 - 列已存在
            continue
    for statement in INDEX_MIGRATIONS:
        try:
            with engine.begin() as connection:
                connection.execute(text(statement))
        except Exception:  # noqa: BLE001
            continue


def _pg_url() -> str:
    """pg_dump 只认标准连接串，去掉 SQLAlchemy 的驱动后缀。"""
    return settings.database_url.replace("postgresql+psycopg://", "postgresql://")


def backup_database(label: str = "manual") -> Path:
    """用 pg_dump 备份到 data/backups，返回文件路径。"""
    settings.backups_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%S")
    target = settings.backups_dir / f"photonv-{label}-{stamp}.sql"
    subprocess.run(
        ["pg_dump", "--no-owner", "--no-privileges", "-f", str(target), _pg_url()],
        check=True,
        capture_output=True,
    )
    return target


def list_backups() -> list[dict]:
    if not settings.backups_dir.exists():
        return []
    items: list[dict] = []
    for path in settings.backups_dir.glob("*.sql"):
        stat = path.stat()
        items.append(
            {
                "file": path.name,
                "size": stat.st_size,
                "created_at": datetime.utcfromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            }
        )
    return sorted(items, key=lambda item: item["created_at"], reverse=True)


def delete_backup(name: str) -> bool:
    safe = Path(name).name
    if not safe.endswith(".sql"):
        return False
    target = settings.backups_dir / safe
    if not target.exists():
        return False
    target.unlink()
    return True
