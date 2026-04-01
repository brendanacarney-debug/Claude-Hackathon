"""
Convert Claude Vision's relative position descriptions into absolute x/y/z coordinates.

Coordinate system:
  Origin (0, 0, 0) = bottom-left corner of the room floor
  X = room width  (left → right)
  Y = height      (floor → ceiling)
  Z = room depth  (front → back)
"""

import math
import uuid
from dataclasses import dataclass

from ..analysis import DetectedObject, VisionAnalysisResult

# Categories treated as anchors — placed first using room-type conventions.
ANCHOR_CATEGORIES = frozenset(
    {"bed", "door", "toilet", "bathtub", "shower", "counter"}
)

# Fallback dimensions by category (meters).
DEFAULT_DIMS: dict[str, dict] = {
    "bed":        {"width": 1.6,  "height": 0.55, "depth": 2.0},
    "nightstand": {"width": 0.5,  "height": 0.6,  "depth": 0.4},
    "chair":      {"width": 0.6,  "height": 0.85, "depth": 0.6},
    "table":      {"width": 1.0,  "height": 0.75, "depth": 0.6},
    "door":       {"width": 0.9,  "height": 2.1,  "depth": 0.05},
    "toilet":     {"width": 0.4,  "height": 0.4,  "depth": 0.65},
    "shelf":      {"width": 1.0,  "height": 0.3,  "depth": 0.25},
    "cord":       {"width": 0.02, "height": 0.01, "depth": 1.0},
    "clutter":    {"width": 0.5,  "height": 0.3,  "depth": 0.5},
    "lamp":       {"width": 0.3,  "height": 0.5,  "depth": 0.3},
    "grab_bar":   {"width": 0.6,  "height": 0.05, "depth": 0.05},
    "walker":     {"width": 0.6,  "height": 0.9,  "depth": 0.5},
    "shower":     {"width": 0.9,  "height": 2.0,  "depth": 0.9},
    "bathtub":    {"width": 0.7,  "height": 0.5,  "depth": 1.5},
    "counter":    {"width": 1.0,  "height": 0.85, "depth": 0.5},
    "cabinet":    {"width": 0.6,  "height": 1.8,  "depth": 0.5},
    "rug":        {"width": 1.2,  "height": 0.01, "depth": 0.8},
    "other":      {"width": 0.5,  "height": 0.5,  "depth": 0.5},
}


@dataclass
class PositionedObject:
    object_id: str
    category: str
    description: str
    position: dict      # {x, y, z}
    dimensions: dict    # {width, height, depth}
    on_primary_path: bool
    floor_level: bool   # True if object is at or near floor height (needed by TASK 4 rules engine)
    confidence: float
    relative_position: str  # preserved for TASK 4 recommendation template slot-filling


@dataclass
class Room:
    room_id: str
    room_type: str
    objects: list[PositionedObject]
    dimensions: dict        # {width, length}
    # Layout metadata carried from VisionAnalysisResult — used by TASK 4 rules engine
    floor_type: str         # hardwood | carpet | tile | linoleum | mixed | unknown
    lighting_quality: str   # bright | adequate | dim | dark
    overall_clutter_level: str  # minimal | moderate | cluttered


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _dims(obj: DetectedObject) -> dict:
    d = obj.estimated_dimensions
    if d and d.get("width") and d.get("height") and d.get("depth"):
        return d
    return dict(DEFAULT_DIMS.get(obj.category, DEFAULT_DIMS["other"]))


def _clamp(val: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, val))


def _wall_hints(text: str, room_w: float, room_d: float) -> tuple[float | None, float | None]:
    """
    Parse wall keywords from a position string and return (x_hint, z_hint).
    None means no constraint was detected for that axis.
    """
    t = text.lower()
    x: float | None = None
    z: float | None = None

    if any(k in t for k in ("north wall", "back wall", "far wall")):
        z = room_d - 0.1
    elif any(k in t for k in ("south wall", "front wall", "near wall", "entrance wall")):
        z = 0.1

    if any(k in t for k in ("west wall", "left wall")):
        x = 0.1
    elif any(k in t for k in ("east wall", "right wall")):
        x = room_w - 0.1

    # Generic "against a wall" with no direction → default to back wall
    if "against" in t and "wall" in t and x is None and z is None:
        z = room_d - 0.1

    return x, z


# ---------------------------------------------------------------------------
# Anchor placement
# ---------------------------------------------------------------------------

def _place_anchor(
    category: str,
    room_type: str,
    room_w: float,
    room_d: float,
    dims: dict,
    rel_pos: str,
) -> tuple[float, float, float]:
    wx, wz = _wall_hints(rel_pos, room_w, room_d)

    if category == "bed":
        if wz is not None:
            return room_w / 2 - dims["width"] / 2, 0.0, wz
        # Default: against the left wall, centered depth-wise
        return 0.1, 0.0, room_d / 2 - dims["depth"] / 2

    if category == "door":
        if wz is not None:
            return room_w / 2 - dims["width"] / 2, 0.0, wz
        if wx is not None:
            return wx, 0.0, room_d / 2
        # Default: right wall mid-depth
        return room_w - dims["width"], 0.0, room_d / 2

    if category == "toilet":
        return 0.5, 0.0, room_d - dims["depth"] - 0.1

    if category == "bathtub":
        return room_w - dims["width"] - 0.1, 0.0, 0.1

    if category == "shower":
        return room_w - dims["width"] - 0.1, 0.0, room_d - dims["depth"] - 0.1

    if category == "counter":
        return 0.1, 0.0, room_d / 2

    # Fallback anchor centre
    return room_w / 2 - dims["width"] / 2, 0.0, room_d / 2 - dims["depth"] / 2


# ---------------------------------------------------------------------------
# Relative placement
# ---------------------------------------------------------------------------

def _ref_object(rel_pos: str, placed: list[PositionedObject]) -> PositionedObject | None:
    """Find the first placed object whose category appears in the position string."""
    t = rel_pos.lower()
    for obj in placed:
        if obj.category in t:
            return obj
    return None


def _place_relative(
    obj: DetectedObject,
    dims: dict,
    placed: list[PositionedObject],
    room_w: float,
    room_d: float,
    fallback_index: int,
) -> tuple[float, float, float]:
    t = obj.relative_position.lower()

    # ---------- Y (height) ----------
    y = 0.0
    if obj.floor_level:
        y = 0.0
    elif any(k in t for k in ("mounted", "hung", "hang", "on wall")):
        y = 1.5
    elif "high shelf" in t or ("shelf" in t and "high" in t):
        y = 1.8
    elif "shelf" in t:
        y = 1.5

    # ---------- Reference object ----------
    ref = _ref_object(t, placed)
    if ref:
        rx = ref.position["x"]
        rz = ref.position["z"]
        rw = ref.dimensions["width"]
        rd = ref.dimensions["depth"]
        rh = ref.dimensions["height"]

        if "between" in t:
            refs = [o for o in placed if o.category in t]
            if len(refs) >= 2:
                x = (refs[0].position["x"] + refs[1].position["x"]) / 2
                z = (refs[0].position["z"] + refs[1].position["z"]) / 2
            else:
                x = rx + rw + 0.4
                z = rz + rd / 2
        elif any(k in t for k in ("beside", "next to", "adjacent")):
            x = rx + rw + dims["width"] / 2 + 0.05
            z = rz
        elif any(k in t for k in ("in front of", "facing")):
            x = rx
            z = rz + rd + dims["depth"] / 2 + 0.3
        elif "behind" in t:
            x = rx
            z = rz - dims["depth"] / 2 - 0.3
        elif any(k in t for k in ("above", "on top")):
            x = rx
            z = rz
            y = rh
        elif any(k in t for k in ("near", "close", "by the")):
            x = rx + rw + 0.3
            z = rz
        else:
            x = rx + rw + 0.3
            z = rz

        x = _clamp(x, 0.0, room_w - dims["width"])
        z = _clamp(z, 0.0, room_d - dims["depth"])
        return x, y, z

    # ---------- Keyword-only fallbacks ----------
    if "center" in t:
        return room_w / 2 - dims["width"] / 2, y, room_d / 2 - dims["depth"] / 2

    if "corner" in t:
        return 0.1, y, 0.1

    wx, wz = _wall_hints(t, room_w, room_d)
    if wx is not None or wz is not None:
        x = wx if wx is not None else room_w / 2
        z = wz if wz is not None else room_d / 2
        return _clamp(x, 0.0, room_w - dims["width"]), y, _clamp(z, 0.0, room_d - dims["depth"])

    # ---------- Grid fallback ----------
    cols = max(1, int(room_w / 1.5))
    col = fallback_index % cols
    row = fallback_index // cols
    x = _clamp(0.5 + col * 1.5, 0.0, room_w - dims["width"])
    z = _clamp(0.5 + row * 1.5, 0.0, room_d - dims["depth"])
    return x, y, z


# ---------------------------------------------------------------------------
# Path proximity
# ---------------------------------------------------------------------------

def _near_path(
    pos: dict,
    dims: dict,
    path_start: tuple[float, float],
    path_end: tuple[float, float],
    threshold: float = 0.5,
) -> bool:
    """True if object centre is within `threshold` metres of the bed→door line segment."""
    cx = pos["x"] + dims["width"] / 2
    cz = pos["z"] + dims["depth"] / 2
    sx, sz = path_start
    ex, ez = path_end

    dx, dz = ex - sx, ez - sz
    length_sq = dx * dx + dz * dz
    if length_sq < 1e-6:
        dist = math.hypot(cx - sx, cz - sz)
    else:
        t = _clamp(((cx - sx) * dx + (cz - sz) * dz) / length_sq, 0.0, 1.0)
        dist = math.hypot(cx - (sx + t * dx), cz - (sz + t * dz))

    return dist < threshold


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_room_model(vision_result: VisionAnalysisResult) -> Room:
    """
    Convert a VisionAnalysisResult into a Room with all objects placed at
    absolute x/y/z coordinates.

    Strategy:
      1. Read room dimensions from the layout.
      2. Place anchor objects (bed, door, toilet, …) using room-type conventions.
      3. Place remaining objects relative to the nearest referenced anchor.
      4. Mark objects that lie within 0.5 m of the bed→door line as on_primary_path.
    """
    layout = vision_result.room_layout
    room_w = float(layout.approximate_dimensions.get("width", 4.0))
    room_d = float(layout.approximate_dimensions.get("length", 5.0))

    placed: list[PositionedObject] = []

    anchors = [o for o in vision_result.objects if o.category in ANCHOR_CATEGORIES]
    others  = [o for o in vision_result.objects if o.category not in ANCHOR_CATEGORIES]

    for obj in anchors:
        dims = _dims(obj)
        x, y, z = _place_anchor(
            obj.category, vision_result.room_type, room_w, room_d, dims, obj.relative_position
        )
        placed.append(
            PositionedObject(
                object_id=str(uuid.uuid4()),
                category=obj.category,
                description=obj.description,
                position={"x": round(x, 2), "y": round(y, 2), "z": round(z, 2)},
                dimensions=dims,
                on_primary_path=bool(obj.on_likely_walking_path),
                floor_level=obj.floor_level,
                confidence=0.85,
                relative_position=obj.relative_position,
            )
        )

    for idx, obj in enumerate(others):
        dims = _dims(obj)
        x, y, z = _place_relative(obj, dims, placed, room_w, room_d, idx)
        placed.append(
            PositionedObject(
                object_id=str(uuid.uuid4()),
                category=obj.category,
                description=obj.description,
                position={"x": round(x, 2), "y": round(y, 2), "z": round(z, 2)},
                dimensions=dims,
                on_primary_path=bool(obj.on_likely_walking_path),
                floor_level=obj.floor_level,
                confidence=0.80,
                relative_position=obj.relative_position,
            )
        )

    # Mark on_primary_path using bed→door line
    bed  = next((o for o in placed if o.category == "bed"),  None)
    door = next((o for o in placed if o.category == "door"), None)

    if bed and door:
        start = (
            bed.position["x"] + bed.dimensions["width"] / 2,
            bed.position["z"] + bed.dimensions["depth"],
        )
        end = (
            door.position["x"] + door.dimensions["width"] / 2,
            door.position["z"],
        )
        for obj in placed:
            obj.on_primary_path = obj.on_primary_path or _near_path(
                obj.position, obj.dimensions, start, end
            )

    return Room(
        room_id=str(uuid.uuid4()),
        room_type=vision_result.room_type,
        objects=placed,
        dimensions={"width": room_w, "length": room_d},
        floor_type=layout.floor_type,
        lighting_quality=layout.lighting_quality,
        overall_clutter_level=layout.overall_clutter_level,
    )
