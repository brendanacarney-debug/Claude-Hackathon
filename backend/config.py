from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True, slots=True)
class Settings:
    app_name: str
    version: str
    demo_mode: bool
    max_upload_bytes: int
    repo_root: Path
    runtime_dir: Path
    storage_dir: Path
    sessions_dir: Path
    fixture_dir: Path
    cors_origins: tuple[str, ...]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    repo_root = Path(__file__).resolve().parents[1]
    runtime_dir = Path(os.getenv("HOMERECOVER_RUNTIME_DIR") or (repo_root / ".runtime"))
    storage_dir = runtime_dir / "storage"
    sessions_dir = runtime_dir / "sessions"
    fixture_dir = repo_root / "fixtures"

    runtime_dir.mkdir(exist_ok=True)
    storage_dir.mkdir(exist_ok=True)
    sessions_dir.mkdir(exist_ok=True)

    raw_origins = os.getenv("CORS_ORIGINS", "*")
    if raw_origins.strip() == "*":
        cors_origins = ("*",)
    else:
        cors_origins = tuple(
            origin.strip() for origin in raw_origins.split(",") if origin.strip()
        )

    return Settings(
        app_name="HomeRecover Scan",
        version="0.1.0",
        demo_mode=_as_bool(os.getenv("HOMERECOVER_DEMO_MODE"), default=False),
        max_upload_bytes=int(os.getenv("MAX_UPLOAD_MB", "10")) * 1024 * 1024,
        repo_root=repo_root,
        runtime_dir=runtime_dir,
        storage_dir=storage_dir,
        sessions_dir=sessions_dir,
        fixture_dir=fixture_dir,
        cors_origins=cors_origins,
    )
