"""
Generate ghost rearrangement suggestions.

For each "remove" or "move" recommendation that is linked to a hazard, calculate
where the associated object(s) should go — or mark them for removal.

Rules (from TASK 3 spec):
  - remove → action="remove", new_position={0,0,0}
  - move   → action="move",   new_position pushed to the nearest wall
              (clears the primary path by putting the object out of the way)

Only objects that have a matching recommendation are rearranged.
"""

from dataclasses import dataclass

from .room_builder import Room, PositionedObject


@dataclass
class GhostRearrangement:
    object_id: str
    action: str         # "remove" | "move"
    new_position: dict  # {x, y, z}
    reason: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_object(
    rooms: list[Room], object_id: str
) -> tuple[PositionedObject | None, Room | None]:
    for room in rooms:
        for obj in room.objects:
            if obj.object_id == object_id:
                return obj, room
    return None, None


def _push_to_nearest_wall(obj: PositionedObject, room: Room) -> dict:
    """
    Move an object toward the nearest room wall, leaving 0.1 m clearance,
    so it no longer obstructs the primary walking path.
    """
    room_w = room.dimensions["width"]
    room_d = room.dimensions["length"]

    cx = obj.position["x"] + obj.dimensions["width"] / 2
    cz = obj.position["z"] + obj.dimensions["depth"] / 2
    y  = obj.position["y"]

    # Distance from object centre to each wall; pick the smallest via index
    # to avoid float-equality comparisons.
    distances = [
        cx,              # left
        room_w - cx,     # right
        cz,              # front
        room_d - cz,     # back
    ]
    nearest_idx = distances.index(min(distances))

    if nearest_idx == 0:   # left wall
        return {"x": 0.1, "y": y, "z": round(obj.position["z"], 2)}
    if nearest_idx == 1:   # right wall
        return {"x": round(room_w - obj.dimensions["width"] - 0.1, 2), "y": y, "z": round(obj.position["z"], 2)}
    if nearest_idx == 2:   # front wall
        return {"x": round(obj.position["x"], 2), "y": y, "z": 0.1}
    # nearest_idx == 3: back wall
    return {"x": round(obj.position["x"], 2), "y": y, "z": round(room_d - obj.dimensions["depth"] - 0.1, 2)}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def suggest_rearrangements(
    rooms: list[Room],
    hazards: list[dict],
    recommendations: list[dict],
) -> list[GhostRearrangement]:
    """
    For hazards with "remove" or "move" recommendations, calculate where the
    related objects should go.

    Only generates rearrangements for objects with a matching recommendation.
    Each object is processed at most once.

    Args:
        rooms:           Positioned room models from the spatial builder.
        hazards:         List of hazard dicts (keys: hazard_id, related_object_ids,
                         recommendation_ids).
        recommendations: List of recommendation dicts (keys: recommendation_id,
                         category, text).

    Returns:
        List of GhostRearrangement, one per actionable object.
    """
    # Build a map from recommendation_id → hazard so we can find related objects
    hazard_by_rec: dict[str, dict] = {}
    for haz in hazards:
        for rec_id in haz.get("recommendation_ids", []):
            hazard_by_rec[rec_id] = haz

    rearrangements: list[GhostRearrangement] = []
    seen_objects: set[str] = set()

    for rec in recommendations:
        category = rec.get("category", "")
        if category not in ("remove", "move"):
            continue

        rec_id = rec.get("recommendation_id", "")
        haz = hazard_by_rec.get(rec_id)
        if not haz:
            continue

        for object_id in haz.get("related_object_ids", []):
            if object_id in seen_objects:
                continue

            obj, room = _find_object(rooms, object_id)
            if not obj or not room:
                continue

            reason = rec.get("text", "Improve walker safety")

            if category == "remove":
                rearrangements.append(
                    GhostRearrangement(
                        object_id=object_id,
                        action="remove",
                        new_position={"x": 0.0, "y": 0.0, "z": 0.0},
                        reason=reason,
                    )
                )
            else:  # "move"
                new_pos = _push_to_nearest_wall(obj, room)
                rearrangements.append(
                    GhostRearrangement(
                        object_id=object_id,
                        action="move",
                        new_position=new_pos,
                        reason=reason,
                    )
                )

            seen_objects.add(object_id)

    return rearrangements
