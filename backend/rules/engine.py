from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from uuid import uuid4

from backend.models import Hazard, RecoveryProfile, Room, RoomObject, Severity, coerce_profile, coerce_rooms

FLOOR_OBSTACLE_CATEGORIES = {"rug", "cord", "clutter", "other"}
PATH_OBSTRUCTION_CATEGORIES = {"chair", "table", "cabinet", "other"}
SUPPORT_SURFACE_CATEGORIES = {"grab_bar", "counter", "cabinet", "nightstand", "table"}
LIGHT_SOURCE_CATEGORIES = {"lamp"}
ESSENTIAL_KEYWORDS = (
    "medication",
    "medications",
    "phone",
    "charger",
    "water",
    "glasses",
    "remote",
    "daily essential",
    "supply",
    "supplies",
)
SEVERITY_RANK = {
    Severity.URGENT.value: 0,
    Severity.MODERATE.value: 1,
    Severity.LOW.value: 2,
}


@dataclass(slots=True)
class HazardCandidate:
    hazard_class: str
    specific_score: int
    explanation: str
    related_object_ids: list[str]


def calculate_severity(hazard_class: str, profile: RecoveryProfile, specific_score: int) -> str:
    weight = profile.hazard_weights[hazard_class]
    combined = weight * specific_score
    if combined >= 12:
        return Severity.URGENT.value
    if combined >= 6:
        return Severity.MODERATE.value
    return Severity.LOW.value


def score_hazards(
    rooms: list[Room] | list[dict],
    profile: RecoveryProfile | dict,
    vision_hazards: list[str] | None = None,
) -> list[Hazard]:
    profile_model = coerce_profile(profile)
    room_models = coerce_rooms(rooms)
    observations = [item.lower() for item in (vision_hazards or [])]

    candidates: list[HazardCandidate] = []
    candidates.extend(_score_floor_obstacles(room_models, observations))
    candidates.extend(_score_path_obstructions(room_models, profile_model, observations))
    candidates.extend(_score_transfer_challenges(room_models))
    candidates.extend(_score_bathroom_risks(room_models, observations))
    candidates.extend(_score_reachability_issues(room_models, profile_model, observations))
    candidates.extend(_score_lighting_issues(room_models))
    candidates.extend(_score_wound_care_issues(room_models, profile_model, observations))

    hazards = [
        Hazard(
            hazard_id=str(uuid4()),
            hazard_class=candidate.hazard_class,
            severity=calculate_severity(candidate.hazard_class, profile_model, candidate.specific_score),
            explanation=candidate.explanation,
            related_object_ids=list(candidate.related_object_ids),
            recommendation_ids=[],
        )
        for candidate in _dedupe_candidates(candidates)
    ]

    hazards.sort(
        key=lambda hazard: (
            SEVERITY_RANK[hazard.severity],
            -profile_model.hazard_weights[hazard.hazard_class],
            hazard.hazard_class,
            hazard.explanation,
        )
    )
    return hazards


def _score_floor_obstacles(rooms: list[Room], observations: list[str]) -> list[HazardCandidate]:
    combined_observations = " ".join(observations)
    candidates: list[HazardCandidate] = []

    for room in rooms:
        for obj in room.objects:
            category = obj.category.lower()
            description = _combined_text(obj.description, obj.relative_position)
            is_floor_level = _is_floor_level_object(obj)
            near_primary_path = obj.on_primary_path or _distance_to_primary_path(obj) <= 0.5

            if category not in FLOOR_OBSTACLE_CATEGORIES or not is_floor_level:
                continue

            if category == "rug" and near_primary_path:
                candidates.append(
                    HazardCandidate(
                        hazard_class="floor_obstacle",
                        specific_score=3,
                        explanation=(
                            f"Loose rug on the walking path in the {room.room_type}. "
                            "A walker can catch on the edge and cause a fall."
                        ),
                        related_object_ids=[obj.object_id],
                    )
                )
                continue

            if category == "cord":
                if near_primary_path and _mentions_any(description, "cross", "across", "crossing"):
                    score = 3
                    explanation = (
                        f"Cord crosses the primary walking path in the {room.room_type}. "
                        "It can catch a walker or cause a trip."
                    )
                elif near_primary_path:
                    score = 2
                    explanation = (
                        f"Cord sits beside the walking path in the {room.room_type}. "
                        "It could still catch a foot or walker wheel."
                    )
                else:
                    continue
                candidates.append(
                    HazardCandidate(
                        hazard_class="floor_obstacle",
                        specific_score=score,
                        explanation=explanation,
                        related_object_ids=[obj.object_id],
                    )
                )
                continue

            if category == "clutter":
                score = 3 if near_primary_path else 1
                path_phrase = "on the primary route" if near_primary_path else "on the floor"
                candidates.append(
                    HazardCandidate(
                        hazard_class="floor_obstacle",
                        specific_score=score,
                        explanation=(
                            f"Clutter is {path_phrase} in the {room.room_type}. "
                            "Loose items on the floor reduce safe walker clearance."
                        ),
                        related_object_ids=[obj.object_id],
                    )
                )
                continue

            if category == "other" and (
                _mentions_any(description, "shoe", "slipper")
                or _mentions_any(combined_observations, "shoe", "slipper")
            ):
                candidates.append(
                    HazardCandidate(
                        hazard_class="floor_obstacle",
                        specific_score=2,
                        explanation=(
                            f"Shoes or loose items are on the floor in the {room.room_type}. "
                            "They create a moderate trip risk during recovery."
                        ),
                        related_object_ids=[obj.object_id],
                    )
                )
    return candidates


def _score_path_obstructions(
    rooms: list[Room], profile: RecoveryProfile, observations: list[str]
) -> list[HazardCandidate]:
    candidates: list[HazardCandidate] = []
    needs_walker_clearance = "needs_walker_clearance" in profile.constraints
    combined_observations = " ".join(observations)

    for room in rooms:
        for obj in room.objects:
            category = obj.category.lower()
            if category in PATH_OBSTRUCTION_CATEGORIES and obj.on_primary_path:
                clearance = _path_clearance(obj)
                descriptor_text = _combined_text(obj.description, obj.relative_position, combined_observations)

                if clearance is None:
                    if _mentions_any(descriptor_text, "narrow", "blocking", "blocks", "obstruct", "squeeze"):
                        score = 3 if needs_walker_clearance else 2
                        explanation = (
                            f"{_title_case(category)} appears to obstruct the walking route in the {room.room_type}. "
                            f"Open at least {int(profile.min_path_width_m * 100)}cm of clearance for safe walker use."
                        )
                        candidates.append(
                            HazardCandidate(
                                hazard_class="path_obstruction",
                                specific_score=score,
                                explanation=explanation,
                                related_object_ids=[obj.object_id],
                            )
                        )
                    continue

                if clearance >= profile.min_path_width_m:
                    continue

                if clearance < 0.7 or (needs_walker_clearance and category != "other"):
                    score = 3
                else:
                    score = 2

                candidates.append(
                    HazardCandidate(
                        hazard_class="path_obstruction",
                        specific_score=score,
                        explanation=(
                            f"{_title_case(category)} narrows the route in the {room.room_type} to about "
                            f"{int(clearance * 100)}cm, below the {int(profile.min_path_width_m * 100)}cm "
                            "clearance needed for safe walker use."
                        ),
                        related_object_ids=[obj.object_id],
                    )
                )

            if category == "door" and obj.on_primary_path and obj.dimensions.width < profile.min_path_width_m:
                score = 3 if obj.dimensions.width < 0.7 else 2
                candidates.append(
                    HazardCandidate(
                        hazard_class="path_obstruction",
                        specific_score=score,
                        explanation=(
                            f"Doorway on the recovery route is only about {int(obj.dimensions.width * 100)}cm wide. "
                            "That creates a squeeze point for the walker."
                        ),
                        related_object_ids=[obj.object_id],
                    )
                )

        if room.doorway_width_m is not None and room.doorway_width_m < profile.min_path_width_m:
            score = 3 if room.doorway_width_m < 0.7 else 2
            candidates.append(
                HazardCandidate(
                    hazard_class="path_obstruction",
                    specific_score=score,
                    explanation=(
                        f"The {room.room_type} doorway narrows to about {int(room.doorway_width_m * 100)}cm. "
                        "That is below the target walker clearance."
                    ),
                    related_object_ids=[],
                )
            )
    return candidates


def _score_transfer_challenges(rooms: list[Room]) -> list[HazardCandidate]:
    candidates: list[HazardCandidate] = []

    for room in rooms:
        for obj in room.objects:
            category = obj.category.lower()
            description = obj.description.lower()

            if category == "bed":
                reasons: list[str] = []
                bed_height = obj.dimensions.height
                support_available = _has_stable_bedside_support(obj, room.objects)

                if bed_height < 0.45:
                    reasons.append(f"Bed height is low at about {int(bed_height * 100)}cm")
                elif bed_height > 0.65:
                    reasons.append(f"Bed height is high at about {int(bed_height * 100)}cm")
                elif bed_height < 0.58 and not support_available:
                    reasons.append(
                        f"Bed height is borderline low at about {int(bed_height * 100)}cm"
                    )

                if not support_available:
                    reasons.append(
                        "there is no stable support surface within reach for sit-to-stand transfers"
                    )

                if reasons:
                    sentence_parts = [reasons[0].capitalize()]
                    sentence_parts.extend(
                        reason[:1].upper() + reason[1:] if reason else reason for reason in reasons[1:]
                    )
                    explanation = ". ".join(sentence_parts) + "."
                    explanation += " Transfers are harder and less stable with a walker."
                    candidates.append(
                        HazardCandidate(
                            hazard_class="transfer_challenge",
                            specific_score=2,
                            explanation=explanation,
                            related_object_ids=[obj.object_id],
                        )
                    )

            if category in {"chair", "other"} and (
                (obj.armrests is False and _mentions_any(description, "couch", "chair", "seat"))
                or _mentions_any(description, "no armrest", "without armrest")
            ):
                candidates.append(
                    HazardCandidate(
                        hazard_class="transfer_challenge",
                        specific_score=2,
                        explanation=(
                            f"Seat in the {room.room_type} has no armrests to push from during transfers. "
                            "That can make standing up less stable."
                        ),
                        related_object_ids=[obj.object_id],
                    )
                )
    return candidates


def _score_bathroom_risks(rooms: list[Room], observations: list[str]) -> list[HazardCandidate]:
    candidates: list[HazardCandidate] = []
    combined_observations = " ".join(observations)

    for room in rooms:
        if room.room_type.lower() != "bathroom":
            continue

        toilets = [obj for obj in room.objects if obj.category.lower() == "toilet"]
        tubs = [obj for obj in room.objects if obj.category.lower() in {"bathtub", "shower"}]
        grab_bars = [obj for obj in room.objects if obj.category.lower() == "grab_bar"]
        bathroom_text = _combined_text(
            combined_observations,
            room.notes,
            *[obj.description for obj in room.objects],
        )

        if toilets and not _has_grab_bar_or_support(toilets[0], room.objects, grab_bars):
            candidates.append(
                HazardCandidate(
                    hazard_class="bathroom_risk",
                    specific_score=3,
                    explanation=(
                        "Toilet area has no nearby grab bar or support surface for a safe transfer. "
                        "Bathroom transfers are a high fall-risk moment."
                    ),
                    related_object_ids=[toilets[0].object_id],
                )
            )

        if tubs and not _has_grab_bar_or_support(tubs[0], room.objects, grab_bars):
            candidates.append(
                HazardCandidate(
                    hazard_class="bathroom_risk",
                    specific_score=3,
                    explanation=(
                        f"No grab bar or stable support was detected near the {tubs[0].category}. "
                        "Stepping in and out is an urgent fall risk."
                    ),
                    related_object_ids=[tubs[0].object_id],
                )
            )

        if (room.floor_type or "").lower() == "tile":
            related_ids = [obj.object_id for obj in tubs[:1] or toilets[:1]]
            candidates.append(
                HazardCandidate(
                    hazard_class="bathroom_risk",
                    specific_score=2,
                    explanation=(
                        "Bathroom floor is tile, which becomes slippery when wet. "
                        "A flat non-slip surface is important for recovery."
                    ),
                    related_object_ids=related_ids,
                )
            )

        non_slip_visible = bool(room.metadata.get("non_slip_surface")) or _mentions_any(
            bathroom_text, "non-slip", "bath mat", "shower mat", "grip mat"
        )
        if tubs and not non_slip_visible:
            candidates.append(
                HazardCandidate(
                    hazard_class="bathroom_risk",
                    specific_score=2,
                    explanation=(
                        f"No non-slip surface is visible in the {tubs[0].category} area. "
                        "Wet surfaces can lead to slips."
                    ),
                    related_object_ids=[tubs[0].object_id],
                )
            )

        if (room.threshold_height_m or 0.0) > 0.025 or _mentions_any(
            combined_observations, "threshold", "lip", "catch walker wheels"
        ):
            related_ids = [obj.object_id for obj in room.objects if obj.category.lower() == "door"]
            candidates.append(
                HazardCandidate(
                    hazard_class="bathroom_risk",
                    specific_score=2,
                    explanation=(
                        "Bathroom threshold could catch walker wheels during entry. "
                        "A raised lip increases the chance of a misstep."
                    ),
                    related_object_ids=related_ids,
                )
            )
    return candidates


def _score_reachability_issues(
    rooms: list[Room], profile: RecoveryProfile, observations: list[str]
) -> list[HazardCandidate]:
    candidates: list[HazardCandidate] = []
    no_bending = "no_bending" in profile.constraints
    combined_observations = " ".join(observations)

    for room in rooms:
        for obj in room.objects:
            description = _combined_text(obj.description, obj.relative_position)
            category = obj.category.lower()
            holds_essentials = bool(obj.metadata.get("contains_essentials")) or _mentions_any(
                description, *ESSENTIAL_KEYWORDS
            )

            if category in {"shelf", "cabinet"} and obj.position.y > 1.5 and holds_essentials:
                candidates.append(
                    HazardCandidate(
                        hazard_class="reachability_issue",
                        specific_score=2,
                        explanation=(
                            f"Essential items appear to be stored high on a {category} in the {room.room_type}. "
                            "Reaching overhead is unsafe during recovery."
                        ),
                        related_object_ids=[obj.object_id],
                    )
                )
                continue

            if no_bending and obj.position.y <= 0.2 and holds_essentials:
                candidates.append(
                    HazardCandidate(
                        hazard_class="reachability_issue",
                        specific_score=2,
                        explanation=(
                            f"Essential items are stored low to the floor in the {room.room_type}. "
                            "That setup requires bending during recovery."
                        ),
                        related_object_ids=[obj.object_id],
                    )
                )
                continue

        beds = [obj for obj in room.objects if obj.category.lower() == "bed"]
        if no_bending and beds and not _has_accessible_bedside_surface(beds[0], room.objects):
            candidates.append(
                HazardCandidate(
                    hazard_class="reachability_issue",
                    specific_score=2,
                    explanation=(
                        "There is no accessible bedside surface for daily essentials. "
                        "The patient should not have to bend or walk for basics at night."
                    ),
                    related_object_ids=[beds[0].object_id],
                )
            )

        if no_bending and _mentions_any(combined_observations, "on floor", "stored low"):
            candidates.append(
                HazardCandidate(
                    hazard_class="reachability_issue",
                    specific_score=2,
                    explanation=(
                        "Vision notes suggest some daily essentials are stored low to the floor. "
                        "That creates an avoidable bending risk."
                    ),
                    related_object_ids=[],
                )
            )
    return candidates


def _score_lighting_issues(rooms: list[Room]) -> list[HazardCandidate]:
    candidates: list[HazardCandidate] = []

    for room in rooms:
        if room.room_type.lower() not in {"bedroom", "hallway", "bathroom"}:
            continue

        lighting = (room.lighting_quality or "").lower()
        light_sources = [obj for obj in room.objects if obj.category.lower() in LIGHT_SOURCE_CATEGORIES]
        reasons: list[str] = []
        score = 0

        if lighting in {"dark", "dim"}:
            reasons.append(f"{_title_case(room.room_type)} lighting is {lighting}")
            score = 3 if lighting == "dark" else 2

        if room.room_type.lower() == "hallway" and not light_sources:
            reasons.append("no visible light source is present on the hallway route")
            score = max(score, 3)

        if reasons:
            candidates.append(
                HazardCandidate(
                    hazard_class="lighting_issue",
                    specific_score=max(score, 2),
                    explanation=(
                        f"{'. '.join(reason.capitalize() for reason in reasons)}. "
                        "Nighttime trips to the bathroom are a major fall-risk scenario."
                    ),
                    related_object_ids=[obj.object_id for obj in light_sources],
                )
            )

    bedroom = next((room for room in rooms if room.room_type.lower() == "bedroom"), None)
    if bedroom is not None:
        beds = [obj for obj in bedroom.objects if obj.category.lower() == "bed"]
        has_bedside_lamp = False
        if beds:
            for obj in bedroom.objects:
                if obj.category.lower() != "lamp":
                    continue
                if _distance_between_boxes(beds[0], obj) <= 1.0:
                    has_bedside_lamp = True
                    break
        if beds and not has_bedside_lamp:
            candidates.append(
                HazardCandidate(
                    hazard_class="lighting_issue",
                    specific_score=2,
                    explanation=(
                        "No lamp is within easy reach of the bed. "
                        "The room should be lit before the patient stands up at night."
                    ),
                    related_object_ids=[beds[0].object_id],
                )
            )

    bathroom = next((room for room in rooms if room.room_type.lower() == "bathroom"), None)
    if bathroom is not None and bathroom.metadata.get("overhead_only") and not bathroom.metadata.get(
        "night_light_path"
    ):
        candidates.append(
            HazardCandidate(
                hazard_class="lighting_issue",
                specific_score=2,
                explanation=(
                    "Bathroom appears to rely on a single overhead light with no night-light path. "
                    "That can leave the route too dark for quick nighttime trips."
                ),
                related_object_ids=[],
            )
        )

    return candidates


def _score_wound_care_issues(
    rooms: list[Room], profile: RecoveryProfile, observations: list[str]
) -> list[HazardCandidate]:
    if "wound_care" not in profile.constraints:
        return []

    combined_observations = " ".join(observations)
    bathroom = next((room for room in rooms if room.room_type.lower() == "bathroom"), None)
    if bathroom is None:
        return []

    clean_counter_available = any(
        obj.category.lower() == "counter"
        and obj.dimensions.height >= 0.7
        and bool(obj.metadata.get("clean", True))
        for obj in bathroom.objects
    )
    supplies_visible = _mentions_any(combined_observations, "wound care", "dressing", "bandage", "supplies")

    if clean_counter_available and supplies_visible:
        return []

    return [
        HazardCandidate(
            hazard_class="wound_care_issue",
            specific_score=1,
            explanation=(
                "No clearly accessible clean setup was found for wound care supplies. "
                "A dedicated surface helps keep hygiene tasks organized."
            ),
            related_object_ids=[obj.object_id for obj in bathroom.objects if obj.category.lower() == "counter"],
        )
    ]


def _dedupe_candidates(candidates: list[HazardCandidate]) -> list[HazardCandidate]:
    best_by_key: dict[tuple[str, tuple[str, ...], str], HazardCandidate] = {}
    for candidate in candidates:
        key = (
            candidate.hazard_class,
            tuple(sorted(candidate.related_object_ids)),
            candidate.explanation,
        )
        current = best_by_key.get(key)
        if current is None or candidate.specific_score > current.specific_score:
            best_by_key[key] = candidate
    return list(best_by_key.values())


def _is_floor_level_object(obj: RoomObject) -> bool:
    if obj.floor_level is not None:
        return obj.floor_level
    if obj.category.lower() in {"rug", "cord", "clutter"}:
        return True
    return obj.position.y <= 0.2 or obj.dimensions.height <= 0.2


def _distance_to_primary_path(obj: RoomObject) -> float:
    metadata_distance = obj.metadata.get("distance_to_primary_path_m")
    if metadata_distance is not None:
        return float(metadata_distance)
    return 0.0 if obj.on_primary_path else 1.0


def _path_clearance(obj: RoomObject) -> float | None:
    if obj.path_clearance_m is not None:
        return obj.path_clearance_m
    if obj.metadata.get("path_clearance_m") is not None:
        return float(obj.metadata["path_clearance_m"])
    return None


def _has_stable_bedside_support(bed: RoomObject, objects: list[RoomObject]) -> bool:
    for obj in objects:
        if obj.object_id == bed.object_id:
            continue
        if obj.category.lower() not in SUPPORT_SURFACE_CATEGORIES:
            continue
        if obj.supportive is False:
            continue
        if not 0.65 <= obj.dimensions.height <= 1.1 and obj.supportive is not True:
            continue
        if _distance_between_boxes(bed, obj) <= 0.5:
            return True
    return False


def _has_grab_bar_or_support(
    anchor: RoomObject, objects: list[RoomObject], grab_bars: list[RoomObject]
) -> bool:
    for bar in grab_bars:
        if _distance_between_boxes(anchor, bar) <= 0.75:
            return True
    for obj in objects:
        if obj.object_id == anchor.object_id:
            continue
        if obj.category.lower() not in {"counter", "cabinet", "nightstand"}:
            continue
        if _distance_between_boxes(anchor, obj) <= 0.75:
            return True
    return False


def _has_accessible_bedside_surface(bed: RoomObject, objects: list[RoomObject]) -> bool:
    for obj in objects:
        if obj.object_id == bed.object_id:
            continue
        if obj.category.lower() not in {"nightstand", "table", "counter", "cabinet"}:
            continue
        if not 0.5 <= obj.dimensions.height <= 1.0:
            continue
        if _distance_between_boxes(bed, obj) <= 1.0:
            return True
    return False


def _distance_between_boxes(a: RoomObject, b: RoomObject) -> float:
    ax1, az1, ax2, az2 = _box_bounds(a)
    bx1, bz1, bx2, bz2 = _box_bounds(b)

    dx = max(ax1 - bx2, bx1 - ax2, 0.0)
    dz = max(az1 - bz2, bz1 - az2, 0.0)
    return sqrt(dx * dx + dz * dz)


def _box_bounds(obj: RoomObject) -> tuple[float, float, float, float]:
    return (
        obj.position.x,
        obj.position.z,
        obj.position.x + obj.dimensions.width,
        obj.position.z + obj.dimensions.depth,
    )


def _combined_text(*parts: str) -> str:
    return " ".join(part for part in parts if part).lower()


def _mentions_any(text: str, *keywords: str) -> bool:
    return any(keyword in text for keyword in keywords)


def _title_case(text: str) -> str:
    return text.replace("_", " ").title()
