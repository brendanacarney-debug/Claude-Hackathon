from __future__ import annotations

from uuid import uuid4

from backend.models import (
    Hazard,
    Recommendation,
    RecoveryProfile,
    Room,
    RoomObject,
    coerce_hazards,
    coerce_profile,
    coerce_rooms,
)


RECOMMENDATION_TEMPLATES: dict[str, dict[str, dict[str, str]]] = {
    "floor_obstacle": {
        "rug": {
            "category": "remove",
            "text": "Remove the {description} from {location}. If it must stay, secure all edges flat with double-sided carpet tape.",
            "expected_benefit": "Eliminates trip hazard on {path_description}",
        },
        "cord": {
            "category": "move",
            "text": "Route the {description} along the wall or under furniture, away from the walking path. Use cord covers if it must cross a walkway.",
            "expected_benefit": "Clears trip hazard from {path_description}",
        },
        "clutter": {
            "category": "remove",
            "text": "Clear the {description} from the floor in {location}. Store items in a bin or on a shelf.",
            "expected_benefit": "Opens floor space for safe walker navigation",
        },
        "default": {
            "category": "remove",
            "text": "Clear the {description} from {location} before tonight so the walking path stays open.",
            "expected_benefit": "Reduces trip risk on {path_description}",
        },
    },
    "path_obstruction": {
        "default": {
            "category": "move",
            "text": "Move the {description} to {suggested_new_location} to open at least {min_width}cm of clear width for the walker.",
            "expected_benefit": "Restores safe walker clearance on {path_description}",
        }
    },
    "transfer_challenge": {
        "low_bed": {
            "category": "professional",
            "text": "The bed appears low for safe sit-to-stand transfers. Consider bed risers or discuss with an occupational therapist. A stable chair or grab handle beside the bed can also help.",
            "expected_benefit": "Safer transfers, especially in early recovery days",
        },
        "default": {
            "category": "professional",
            "text": "Add or arrange a stable support surface beside the bed or main seat so the patient has something solid to push from during transfers.",
            "expected_benefit": "Improves stability when standing up or sitting down",
        },
    },
    "bathroom_risk": {
        "no_grab_bar": {
            "category": "professional",
            "text": "No grab bar detected near the {fixture}. A temporary clamp-on grab bar can help without drilling. Discuss permanent installation with your care team.",
            "expected_benefit": "Provides stable support during bathroom transfers",
        },
        "slip_surface": {
            "category": "add",
            "text": "Place a non-slip bath mat on the {surface_type} floor near the {fixture}. Make sure it has rubber backing and lies completely flat.",
            "expected_benefit": "Reduces slip risk on wet bathroom surfaces",
        },
        "default": {
            "category": "adjust",
            "text": "Rework the bathroom setup near the {fixture} so there is a stable support surface and no slippery or raised transition underfoot.",
            "expected_benefit": "Makes bathroom transfers safer during recovery",
        },
    },
    "reachability_issue": {
        "high_items": {
            "category": "move",
            "text": "Move {items} from the high {surface} down to {accessible_surface} within arm's reach of the {reference_point}. Nothing essential should require reaching above shoulder height.",
            "expected_benefit": "Prevents unsafe reaching and reduces need to stand for basic items",
        },
        "low_items": {
            "category": "move",
            "text": "Move {items} from the floor up to {accessible_surface} at waist height. Bending to the floor increases fall risk.",
            "expected_benefit": "Eliminates bending requirement for daily essentials",
        },
        "default": {
            "category": "move",
            "text": "Rearrange essentials so they stay on {accessible_surface} within easy reach of the {reference_point}.",
            "expected_benefit": "Keeps daily essentials reachable without bending or stretching",
        },
    },
    "lighting_issue": {
        "dark_route": {
            "category": "add",
            "text": "Place a plug-in night light or motion-activated light in the {location}. The bathroom route must be visible without needing to find a switch at night.",
            "expected_benefit": "Reduces nighttime misstep risk on the bathroom route",
        },
        "no_bedside_lamp": {
            "category": "add",
            "text": "Place a lamp or touch-activated light within arm's reach of the bed. The patient should be able to light the room before standing up.",
            "expected_benefit": "Safe transition from lying down to standing",
        },
        "default": {
            "category": "add",
            "text": "Improve lighting in {location} so the recovery route stays visible during nighttime trips.",
            "expected_benefit": "Improves visibility on the main walking route",
        },
    },
    "wound_care_issue": {
        "default": {
            "category": "adjust",
            "text": "Set up a clean, accessible surface near {location} for wound care supplies. Keep dressings, antiseptic, and instructions together in a small tray or caddy.",
            "expected_benefit": "Organized wound care reduces infection risk and awkward positioning",
        }
    },
}


def generate_recommendations(
    hazards: list[Hazard] | list[dict],
    rooms: list[Room] | list[dict],
    profile: RecoveryProfile | dict,
) -> list[Recommendation]:
    hazard_models = coerce_hazards(hazards)
    room_models = coerce_rooms(rooms)
    profile_model = coerce_profile(profile)

    object_lookup: dict[str, tuple[Room, RoomObject]] = {}
    for room in room_models:
        for obj in room.objects:
            object_lookup[obj.object_id] = (room, obj)

    recommendations: list[Recommendation] = []
    for priority, hazard in enumerate(hazard_models, start=1):
        related_pairs = [
            object_lookup[object_id]
            for object_id in hazard.related_object_ids
            if object_id in object_lookup
        ]
        primary_room, primary_object = related_pairs[0] if related_pairs else (None, None)
        template_key = _choose_template_key(hazard, primary_object)
        template = _resolve_template(hazard.hazard_class, template_key)
        slots = _build_slots(hazard, primary_room, primary_object, profile_model, related_pairs)

        recommendation = Recommendation(
            recommendation_id=str(uuid4()),
            priority=priority,
            category=template["category"],
            text=_fill_template(template["text"], slots),
            target_location=slots["location"],
            expected_benefit=_fill_template(template["expected_benefit"], slots),
        )
        hazard.recommendation_ids = [recommendation.recommendation_id]
        recommendations.append(recommendation)

    return recommendations


def _choose_template_key(hazard: Hazard, primary_object: RoomObject | None) -> str:
    explanation = hazard.explanation.lower()
    category = primary_object.category.lower() if primary_object else ""

    if hazard.hazard_class == "floor_obstacle":
        if category in {"rug", "cord", "clutter"}:
            return category
        return "default"

    if hazard.hazard_class == "transfer_challenge":
        if "bed" in explanation and ("low" in explanation or "borderline low" in explanation):
            return "low_bed"
        return "default"

    if hazard.hazard_class == "bathroom_risk":
        if "grab bar" in explanation or "support surface" in explanation:
            return "no_grab_bar"
        if "tile" in explanation or "slip" in explanation or "non-slip" in explanation:
            return "slip_surface"
        return "default"

    if hazard.hazard_class == "reachability_issue":
        if "floor" in explanation or "low" in explanation:
            return "low_items"
        if "high" in explanation or category in {"shelf", "cabinet"}:
            return "high_items"
        return "default"

    if hazard.hazard_class == "lighting_issue":
        if "bed" in explanation and "lamp" in explanation:
            return "no_bedside_lamp"
        return "dark_route"

    return "default"


def _resolve_template(hazard_class: str, template_key: str) -> dict[str, str]:
    templates = RECOMMENDATION_TEMPLATES[hazard_class]
    return templates.get(template_key, templates["default"])


def _build_slots(
    hazard: Hazard,
    room: Room | None,
    obj: RoomObject | None,
    profile: RecoveryProfile,
    related_pairs: list[tuple[Room, RoomObject]],
) -> dict[str, str]:
    description = _object_description(obj)
    location = _location_label(hazard, room, obj)
    fixture = obj.category.replace("_", " ") if obj else "fixture"
    surface_type = (room.floor_type if room and room.floor_type else "bathroom").replace("_", " ")
    accessible_surface = "the nightstand"
    reference_point = "bed"

    if any(pair_obj.category.lower() in {"counter", "cabinet"} for _, pair_obj in related_pairs):
        accessible_surface = "a waist-height counter or cabinet shelf"
    if room and room.room_type.lower() == "bathroom":
        reference_point = "toilet area"

    if obj and obj.category.lower() in {"shelf", "cabinet"}:
        surface = obj.category.replace("_", " ")
    else:
        surface = "storage surface"

    items = "daily essentials"
    if obj and obj.metadata.get("contains_essentials"):
        items = "medications, chargers, and other daily essentials"
    elif "medication" in hazard.explanation.lower():
        items = "medications and daily essentials"

    return {
        "description": description,
        "location": location,
        "path_description": "the bed-to-bathroom route",
        "suggested_new_location": _suggested_new_location(room),
        "min_width": str(int(profile.min_path_width_m * 100)),
        "fixture": fixture,
        "surface_type": surface_type,
        "items": items,
        "surface": surface,
        "accessible_surface": accessible_surface,
        "reference_point": reference_point,
    }


def _fill_template(template: str, slots: dict[str, str]) -> str:
    text = template.format_map(_FallbackDict(slots))
    while "  " in text:
        text = text.replace("  ", " ")
    return text.strip()


def _object_description(obj: RoomObject | None) -> str:
    if obj is None:
        return "obstacle"
    if obj.description:
        return obj.description
    return obj.category.replace("_", " ")


def _location_label(hazard: Hazard, room: Room | None, obj: RoomObject | None) -> str:
    if room is None:
        explanation = hazard.explanation.lower()
        if "hallway" in explanation:
            return "hallway"
        if "bathroom" in explanation:
            return "bathroom"
        if "bedroom" in explanation:
            return "bedroom"
        return "main walking route"
    room_label = room.room_type.replace("_", " ")
    if obj and obj.on_primary_path:
        return f"{room_label} walking path"
    return room_label


def _suggested_new_location(room: Room | None) -> str:
    if room is None:
        return "the nearest wall or corner"
    return f"the far wall or corner of the {room.room_type.replace('_', ' ')}"


class _FallbackDict(dict):
    def __missing__(self, key: str) -> str:
        return key.replace("_", " ")
