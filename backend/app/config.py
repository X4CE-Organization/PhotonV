"""运行配置：优先读环境变量，其次读仓库根目录的 .env。"""
from __future__ import annotations

import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]


def _load_env() -> None:
    env_file = ROOT_DIR / ".env"
    if not env_file.exists():
        return
    for raw in env_file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


_load_env()


def _bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, "") or default)
    except ValueError:
        return default


def _resolve(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (ROOT_DIR / path).resolve()


class Settings:
    env: str = os.getenv("APP_ENV") or os.getenv("NODE_ENV") or "development"
    is_prod: bool = env == "production"
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = _int("PORT", 8080)
    site_url: str = os.getenv("SITE_URL", "http://localhost:8080").rstrip("/")

    secret_key: str = os.getenv("SECRET_KEY", "photonv-insecure-dev-secret-change-me")
    token_days: int = _int("ACCESS_TOKEN_EXPIRE_DAYS", 14)

    database_url: str = os.getenv(
        "DATABASE_URL", "postgresql+psycopg://photonv:photonv@localhost:5432/photonv"
    )

    data_dir: Path = _resolve(os.getenv("DATA_DIR", "./data"))
    max_video_mb: int = _int("MAX_VIDEO_MB", 2048)
    max_image_mb: int = _int("MAX_IMAGE_MB", 16)

    root_username: str = os.getenv("ROOT_USERNAME", "root")
    root_password: str = os.getenv("ROOT_PASSWORD", "photonv123456")
    root_email: str = os.getenv("ROOT_EMAIL", "root@photonv.local")

    @property
    def videos_dir(self) -> Path:
        return self.data_dir / "videos"

    @property
    def covers_dir(self) -> Path:
        return self.data_dir / "covers"

    @property
    def avatars_dir(self) -> Path:
        return self.data_dir / "avatars"

    @property
    def backups_dir(self) -> Path:
        return self.data_dir / "backups"

    @property
    def frontend_dist(self) -> Path:
        return ROOT_DIR / "frontend" / "dist"

    def ensure_dirs(self) -> None:
        for directory in (self.videos_dir, self.covers_dir, self.avatars_dir, self.backups_dir):
            directory.mkdir(parents=True, exist_ok=True)


settings = Settings()
