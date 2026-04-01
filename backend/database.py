from __future__ import annotations

import asyncio
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import get_settings

_LOCK = asyncio.Lock()


def _session_path(session_id: str) -> Path:
    return get_settings().sessions_dir / f"{session_id}.json"


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _slugify_filename(filename: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9._-]+", "-", filename).strip("-")
    return sanitized or "upload.jpg"


def _storage_file_path(storage_path: str) -> Path:
    clean_path = storage_path.removeprefix("/storage/").replace("/", "\\")
    return get_settings().storage_dir / clean_path


async def create_session(recovery_profile: str) -> str:
    session_id = str(uuid.uuid4())
    payload = {
        "session_id": session_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "recovery_profile": recovery_profile,
        "status": "created",
        "result_json": None,
        "error_message": None,
        "images": [],
    }

    async with _LOCK:
        await asyncio.to_thread(_write_json, _session_path(session_id), payload)

    return session_id


async def get_session(session_id: str) -> dict[str, Any] | None:
    return await asyncio.to_thread(_read_json, _session_path(session_id))


async def update_session_status(
    session_id: str,
    status: str,
    error_message: str | None = None,
) -> None:
    async with _LOCK:
        payload = await asyncio.to_thread(_read_json, _session_path(session_id))
        if payload is None:
            return
        payload["status"] = status
        payload["error_message"] = error_message
        await asyncio.to_thread(_write_json, _session_path(session_id), payload)


async def store_session_result(session_id: str, result_json: dict[str, Any]) -> None:
    async with _LOCK:
        payload = await asyncio.to_thread(_read_json, _session_path(session_id))
        if payload is None:
            return
        payload["status"] = "analyzed"
        payload["error_message"] = None
        payload["result_json"] = result_json
        await asyncio.to_thread(_write_json, _session_path(session_id), payload)


async def save_image_record(
    session_id: str,
    room_type: str,
    storage_path: str,
    upload_order: int,
) -> None:
    async with _LOCK:
        payload = await asyncio.to_thread(_read_json, _session_path(session_id))
        if payload is None:
            return

        payload.setdefault("images", []).append(
            {
                "image_id": str(uuid.uuid4()),
                "session_id": session_id,
                "room_type": room_type,
                "storage_path": storage_path,
                "upload_order": upload_order,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        payload["images"].sort(key=lambda image: image["upload_order"])
        await asyncio.to_thread(_write_json, _session_path(session_id), payload)


async def get_session_images(session_id: str) -> list[dict[str, Any]]:
    payload = await asyncio.to_thread(_read_json, _session_path(session_id))
    if payload is None:
        return []
    return sorted(payload.get("images", []), key=lambda image: image["upload_order"])


async def upload_image_to_storage(
    session_id: str,
    filename: str,
    file_bytes: bytes,
    content_type: str,
) -> str:
    del content_type
    safe_filename = f"{uuid.uuid4().hex}-{_slugify_filename(filename)}"
    destination = get_settings().storage_dir / session_id / safe_filename
    destination.parent.mkdir(parents=True, exist_ok=True)
    await asyncio.to_thread(destination.write_bytes, file_bytes)
    return f"/storage/{session_id}/{safe_filename}"


async def read_storage_bytes(storage_path: str) -> bytes:
    file_path = _storage_file_path(storage_path)
    return await asyncio.to_thread(file_path.read_bytes)
