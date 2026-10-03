"""数据库连接、会话管理与备份。"""
from __future__ import annotations

import subprocess
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine
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
