from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from .analysis import ImageData
from .config import get_settings
from .database import (
    create_session,
    get_session,
    get_session_images,
    read_storage_bytes,
    save_image_record,
    store_session_result,
    update_session_status,
    upload_image_to_storage,
)
from .pipeline import DISCLAIMER, run_full_analysis
from .rules.profiles import get_profile, list_profiles

log = logging.getLogger(__name__)
settings = get_settings()

app = FastAPI(title=settings.app_name, version=settings.version)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/storage", StaticFiles(directory=settings.storage_dir), name="storage")


class CreateSessionRequest(BaseModel):
    recovery_profile: str


class ManualHazardRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    hazard_class: str = Field(alias="class")
    severity: str
    explanation: str


def _load_demo_session() -> dict[str, Any]:
    fixture_path = Path(settings.fixture_dir) / "demo_session.json"
    return json.loads(fixture_path.read_text(encoding="utf-8"))


async def _require_session(session_id: str) -> dict[str, Any]:
    session = await get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


async def _pipeline_inputs(session_id: str) -> tuple[list[ImageData], list[str]]:
    image_records = await get_session_images(session_id)
    images: list[ImageData] = []
    urls: list[str] = []

    for image_record in image_records:
        image_bytes = await read_storage_bytes(image_record["storage_path"])
        images.append(
            ImageData(
                image_bytes=image_bytes,
                room_type=image_record["room_type"],
                upload_order=image_record["upload_order"],
            )
        )
        urls.append(image_record["storage_path"])

    return images, urls


async def _run_analysis_job(session_id: str) -> None:
    session = await get_session(session_id)
    if session is None:
        return

    try:
        if settings.demo_mode:
            result = _load_demo_session()
            result["session_id"] = session_id
            result["created_at"] = session.get(
                "created_at", datetime.now(timezone.utc).isoformat()
            )
            result["recovery_profile"] = session["recovery_profile"]
            image_records = await get_session_images(session_id)
            result["images"]["originals"] = [
                image_record["storage_path"] for image_record in image_records
            ]
            await store_session_result(session_id, result)
            return

        images, image_urls = await _pipeline_inputs(session_id)
        if not images:
            raise ValueError("No images were uploaded for this session.")

        result = await run_full_analysis(
            session_id=session_id,
            images=images,
            recovery_profile=session["recovery_profile"],
            image_urls=image_urls,
        )
        await store_session_result(session_id, result)
    except Exception as exc:  # pragma: no cover - defensive path
        log.exception("Analysis job failed for session_id=%s", session_id)
        await update_session_status(session_id, "error", str(exc))


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": settings.version}


@app.get("/profiles")
async def profiles() -> list[dict[str, Any]]:
    return [profile.to_dict() for profile in list_profiles()]


@app.post("/sessions", status_code=201)
async def sessions_create(request: CreateSessionRequest) -> dict[str, str]:
    try:
        get_profile(request.recovery_profile)
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    session_id = await create_session(request.recovery_profile)
    return {"session_id": session_id}


@app.post("/sessions/{session_id}/upload")
async def sessions_upload(
    session_id: str,
    photos: list[UploadFile] = File(default_factory=list),
    room_types: str = Form(default="[]"),
) -> dict[str, Any]:
    await _require_session(session_id)

    if not photos:
        raise HTTPException(status_code=400, detail="No photos were provided.")

    try:
        parsed_room_types = json.loads(room_types)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="room_types must be valid JSON.") from exc

    if not isinstance(parsed_room_types, list) or len(parsed_room_types) != len(photos):
        raise HTTPException(
            status_code=400,
            detail="room_types must be a JSON array matching the number of photos.",
        )

    await update_session_status(session_id, "uploading")

    for upload_order, (photo, room_type) in enumerate(
        zip(photos, parsed_room_types, strict=True), start=1
    ):
        payload = await photo.read()
        if len(payload) > settings.max_upload_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"{photo.filename or 'upload'} exceeds the 10MB upload limit.",
            )

        storage_path = await upload_image_to_storage(
            session_id=session_id,
            filename=photo.filename or f"upload-{upload_order}.jpg",
            file_bytes=payload,
            content_type=photo.content_type or "image/jpeg",
        )
        await save_image_record(
            session_id=session_id,
            room_type=str(room_type),
            storage_path=storage_path,
            upload_order=upload_order,
        )

    await update_session_status(session_id, "uploaded")
    return {"uploaded": len(photos), "session_id": session_id}


@app.post("/sessions/{session_id}/analyze")
async def sessions_analyze(
    session_id: str,
    background_tasks: BackgroundTasks,
) -> dict[str, str]:
    await _require_session(session_id)
    await update_session_status(session_id, "analyzing")

    if settings.demo_mode:
        await _run_analysis_job(session_id)
    else:
        background_tasks.add_task(_run_analysis_job, session_id)

    return {"status": "analyzing", "session_id": session_id}


@app.get("/sessions/{session_id}", response_model=None)
async def sessions_get(session_id: str) -> Any:
    session = await _require_session(session_id)

    if session["status"] == "analyzed" and session.get("result_json"):
        return JSONResponse(session["result_json"])

    return {
        "session_id": session["session_id"],
        "status": session["status"],
        "recovery_profile": session["recovery_profile"],
        "error_message": session.get("error_message"),
    }


@app.get("/sessions/{session_id}/export", response_class=HTMLResponse)
async def sessions_export(session_id: str) -> HTMLResponse:
    session = await _require_session(session_id)
    if session["status"] != "analyzed" or not session.get("result_json"):
        raise HTTPException(status_code=409, detail="Session is not analyzed yet.")

    result = session["result_json"]
    checklist = result["checklist"]
    items_html = "".join(f"<li>{item}</li>" for item in checklist["first_night"])
    followup_html = "".join(f"<li>{item}</li>" for item in checklist["first_48_hours"])
    created_at = datetime.fromisoformat(result["created_at"].replace("Z", "+00:00"))

    html = f"""
    <!doctype html>
    <html lang="en">
      <head>
        <meta charset="utf-8" />
        <title>HomeRecover Scan - Recovery Safety Checklist</title>
        <style>
          body {{ font-family: Arial, sans-serif; margin: 40px; color: #0f172a; }}
          h1, h2 {{ margin-bottom: 12px; }}
          ul {{ padding-left: 20px; }}
          li {{ margin-bottom: 8px; line-height: 1.5; }}
          .muted {{ color: #475569; }}
        </style>
      </head>
      <body>
        <h1>HomeRecover Scan - Recovery Safety Checklist</h1>
        <p class="muted">Date: {created_at.strftime("%B %d, %Y")}</p>
        <p class="muted">Profile: {result["recovery_profile"].replace("_", " ")}</p>
        <h2>Before Tonight</h2>
        <ul>{items_html}</ul>
        <h2>First 48 Hours</h2>
        <ul>{followup_html}</ul>
        <p class="muted">{result.get("disclaimer", DISCLAIMER)}</p>
      </body>
    </html>
    """
    return HTMLResponse(content=html)


@app.post("/sessions/{session_id}/hazards")
async def sessions_manual_hazard(
    session_id: str,
    request: ManualHazardRequest,
) -> dict[str, Any]:
    session = await _require_session(session_id)
    if session["status"] != "analyzed" or not session.get("result_json"):
        raise HTTPException(status_code=409, detail="Session is not analyzed yet.")

    result = session["result_json"]
    hazard = {
        "hazard_id": f"manual-{uuid.uuid4().hex[:8]}",
        "class": request.hazard_class,
        "severity": request.severity,
        "explanation": request.explanation,
        "related_object_ids": [],
        "recommendation_ids": [],
    }
    result.setdefault("hazards", []).append(hazard)
    await store_session_result(session_id, result)
    return hazard


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Any, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "detail": exc.detail},
    )
