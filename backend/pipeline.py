"""
Full analysis pipeline orchestrator.

Called by TASK 2's POST /sessions/{id}/analyze endpoint.

Steps:
  1. Claude Vision  → VisionAnalysisResult per room
  2. Spatial model  → positioned Room objects
  3. Hazard rules   → hazards + recommendations  [TASK 4 stub]
  4. Safe path      → waypoints + width check
  5. Rearrangements → ghost move/remove actions
  6. Checklist      → first-night + 48-hour items [TASK 4 stub]
  7. Assemble       → complete Session dict

TASK 4 stubs return safe defaults so the pipeline runs end-to-end immediately.
When TASK 4 is ready, replace the two stub functions below — the rest of the
pipeline does not change.

Integration contract for TASK 4:
  _run_hazard_rules  must return (list[dict], list[dict])
    → dicts must match the hazard and recommendation JSON contracts exactly
    → "class" key must appear in each hazard dict (use json alias in pydantic)
  _generate_checklist must be async and return dict with keys
    "first_night" and "first_48_hours" (list[str] each)
"""

import logging
from datetime import datetime, timezone
from typing import Any

from .analysis import analyze_room_photos, ImageData, VisionAnalysisResult
from .checklist import FALLBACK_CHECKLISTS, generate_checklist
from .rules.engine import score_hazards
from .rules.profiles import get_profile
from .rules.recommendations import generate_recommendations
from .spatial.room_builder import build_room_model, Room
from .spatial.path_finder import compute_safe_path, SafePath
from .spatial.rearrangements import suggest_rearrangements, GhostRearrangement

log = logging.getLogger(__name__)

DISCLAIMER = (
    "This tool provides environmental suggestions to support recovery at home. "
    "It is not medical advice and does not replace guidance from your doctor, "
    "occupational therapist, or care team. It may miss hazards. "
    "If you have safety concerns, contact your healthcare provider."
)

def _run_hazard_rules(
    rooms: list[Room],
    vision_results: list[VisionAnalysisResult],
    vision_hazards: list[str],
    recovery_profile: str,
) -> tuple[list[dict], list[dict]]:
    profile = get_profile(recovery_profile)
    hazard_objs = score_hazards(rooms, profile, vision_hazards)
    recommendation_objs = generate_recommendations(hazard_objs, rooms, profile)
    return (
        [hazard.to_dict() for hazard in hazard_objs],
        [recommendation.to_dict() for recommendation in recommendation_objs],
    )


async def _generate_checklist(
    hazards: list[dict],
    recommendations: list[dict],
    recovery_profile: str,
) -> dict:
    try:
        profile = get_profile(recovery_profile)
        checklist = await generate_checklist(hazards, recommendations, profile)
        return checklist.to_dict()
    except Exception:
        log.exception("Checklist generation failed; using fallback")
        fb = FALLBACK_CHECKLISTS.get(recovery_profile)
        if fb is None:
            return {"first_night": [], "first_48_hours": []}
        return {"first_night": list(fb.first_night), "first_48_hours": list(fb.first_48_hours)}


# ---------------------------------------------------------------------------
# Serialisation helpers
# ---------------------------------------------------------------------------

def _room_to_dict(room: Room) -> dict:
    """Serialize a Room to the shared Session JSON contract format."""
    payload = {
        "room_id": room.room_id,
        "room_type": room.room_type,
        "objects": [
            {
                "object_id": obj.object_id,
                "category": obj.category,
                "description": obj.description,
                "relative_position": getattr(obj, "relative_position", ""),
                "position": obj.position,
                "dimensions": obj.dimensions,
                "on_primary_path": obj.on_primary_path,
                "floor_level": obj.floor_level,
                "confidence": obj.confidence,
            }
            for obj in room.objects
        ],
    }
    if getattr(room, "dimensions", None):
        payload["dimensions"] = room.dimensions
    if getattr(room, "floor_type", None):
        payload["floor_type"] = room.floor_type
    if getattr(room, "lighting_quality", None):
        payload["lighting_quality"] = room.lighting_quality
    if getattr(room, "overall_clutter_level", None):
        payload["overall_clutter_level"] = room.overall_clutter_level
    return payload


def _safe_path_to_dict(sp: SafePath) -> dict:
    return {
        "waypoints": [
            {"x": wp.x, "y": wp.y, "z": wp.z, "label": wp.label}
            for wp in sp.waypoints
        ],
        "width_ok": sp.width_ok,
        "min_width_m": sp.min_width_m,
    }


def _rearrangement_to_dict(g: GhostRearrangement) -> dict:
    return {
        "object_id": g.object_id,
        "action": g.action,
        "new_position": g.new_position,
        "reason": g.reason,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def run_full_analysis(
    session_id: str,
    images: list[ImageData],
    recovery_profile: str,
    image_urls: list[str] | None = None,
) -> dict[str, Any]:
    """
    Run the complete analysis pipeline and return a Session dict that matches
    the shared JSON contract.

    Args:
        session_id:       Existing session UUID (created by POST /sessions).
        images:           Uploaded photos with room_type labels and raw bytes.
        recovery_profile: e.g. "walker_after_fall".
        image_urls:       Public Supabase Storage URLs for the uploaded photos.
                          TASK 2 provides these after uploading to Supabase Storage.
                          Stored in the session JSON under images.originals.

    Returns:
        Complete Session dict ready to be stored and returned to the frontend.

    Raises:
        ValueError: if images list is empty.
        anthropic.APIError (and subclasses): on Vision API failures.
        Any other exception propagates so TASK 2's route can catch it and set
        the session status to "error".
    """
    if not images:
        raise ValueError("run_full_analysis requires at least one image")

    # ------------------------------------------------------------------
    # Step 1: Claude Vision analysis
    # ------------------------------------------------------------------
    vision_results: list[VisionAnalysisResult] = await analyze_room_photos(
        images, recovery_profile
    )

    if not vision_results:
        raise ValueError(
            "Claude Vision returned no results — check that images are valid and non-empty"
        )

    # ------------------------------------------------------------------
    # Step 2: Spatial model
    # ------------------------------------------------------------------
    rooms: list[Room] = [build_room_model(vr) for vr in vision_results]

    # ------------------------------------------------------------------
    # Step 3: Hazard rules engine
    # Flatten raw vision hazard text across all rooms for the rules engine.
    # ------------------------------------------------------------------
    vision_hazards: list[str] = [
        hazard
        for vr in vision_results
        for hazard in vr.observed_hazards
    ]
    hazards, recommendations = _run_hazard_rules(
        rooms, vision_results, vision_hazards, recovery_profile
    )

    # ------------------------------------------------------------------
    # Step 4: Safe path
    # ------------------------------------------------------------------
    min_width = get_profile(recovery_profile).min_path_width_m
    safe_path = compute_safe_path(rooms, min_width)

    # ------------------------------------------------------------------
    # Step 5: Ghost rearrangements
    # ------------------------------------------------------------------
    rearrangements = suggest_rearrangements(rooms, hazards, recommendations)

    # ------------------------------------------------------------------
    # Step 6: Checklist
    # ------------------------------------------------------------------
    try:
        checklist = await _generate_checklist(hazards, recommendations, recovery_profile)
    except Exception:
        log.exception("Checklist generation failed; using built-in fallback")
        fb = FALLBACK_CHECKLISTS.get(recovery_profile)
        checklist = {"first_night": list(fb.first_night), "first_48_hours": list(fb.first_48_hours)} if fb else {"first_night": [], "first_48_hours": []}

    # ------------------------------------------------------------------
    # Step 7: Assemble Session
    # ------------------------------------------------------------------
    return {
        "session_id": session_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "recovery_profile": recovery_profile,
        "status": "analyzed",
        "rooms": [_room_to_dict(r) for r in rooms],
        "hazards": hazards,
        "recommendations": recommendations,
        "safe_path": _safe_path_to_dict(safe_path),
        "checklist": checklist,
        "ghost_rearrangements": [_rearrangement_to_dict(g) for g in rearrangements],
        "images": {
            "originals": image_urls or [],
            "annotated": [],
        },
        "disclaimer": DISCLAIMER,
    }
