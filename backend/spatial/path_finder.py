"""
Compute a safe walking path from the bed to the bathroom door.

Algorithm:
  1. Start = centre of bed's front edge.
  2. End   = centre of bathroom door.
  3. If the two rooms are different, route via the bedroom door first.
  4. Check whether any object blocks the straight line in the start room.
  5. If blocked, add one perpendicular dodge waypoint around the first blocker.
  6. Calculate minimum clear width along the full path.
"""

import math
from dataclasses import dataclass

from .room_builder import Room, PositionedObject


@dataclass
class Waypoint:
    x: float
    y: float
    z: float
    label: str
    room_id: str | None = None


@dataclass
class SafePath:
    waypoints: list[Waypoint]
    width_ok: bool
    min_width_m: float


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _segment_hits_box(
    sx: float, sz: float,
    ex: float, ez: float,
    obj: PositionedObject,
    margin: float = 0.1,
) -> bool:
    """
    Return True if the line segment (sx,sz)→(ex,ez) passes through the object's
    axis-aligned bounding box (expanded by margin on every side).

    Doors are excluded — the walker passes through them.
    """
    if obj.category == "door":
        return False

    ox0 = obj.position["x"] - margin
    oz0 = obj.position["z"] - margin
    ox1 = obj.position["x"] + obj.dimensions["width"]  + margin
    oz1 = obj.position["z"] + obj.dimensions["depth"]  + margin

    # Parametric slab intersection
    t_min, t_max = 0.0, 1.0
    for s, e, b0, b1 in ((sx, ex, ox0, ox1), (sz, ez, oz0, oz1)):
        d = e - s
        if abs(d) < 1e-9:
            if s < b0 or s > b1:
                return False
        else:
            t0, t1 = (b0 - s) / d, (b1 - s) / d
            if t0 > t1:
                t0, t1 = t1, t0
            t_min = max(t_min, t0)
            t_max = min(t_max, t1)
            if t_min > t_max:
                return False
    return True


def _min_clear_width(
    waypoints_2d: list[tuple[float, float]],
    objects: list[PositionedObject],
) -> float:
    """
    For each path segment, find the minimum perpendicular distance from the
    segment centreline to any non-door object's edge.
    """
    min_w = float("inf")

    for i in range(len(waypoints_2d) - 1):
        sx, sz = waypoints_2d[i]
        ex, ez = waypoints_2d[i + 1]
        dx, dz = ex - sx, ez - sz
        length = math.hypot(dx, dz)
        if length < 1e-6:
            continue
        # Unit perpendicular
        px, pz = -dz / length, dx / length
        mx, mz = (sx + ex) / 2, (sz + ez) / 2

        for obj in objects:
            if obj.category == "door":
                continue
            cx = obj.position["x"] + obj.dimensions["width"] / 2
            cz = obj.position["z"] + obj.dimensions["depth"] / 2
            # Signed perpendicular distance from midpoint to object centre
            perp_dist = abs((cx - mx) * px + (cz - mz) * pz)
            obj_half = max(obj.dimensions["width"], obj.dimensions["depth"]) / 2
            clear = perp_dist - obj_half
            if 0.0 < clear < min_w:
                min_w = clear

    return round(min_w if min_w != float("inf") else 2.0, 2)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_safe_path(rooms: list[Room], profile_min_width: float = 0.9) -> SafePath:
    """
    Find a clear walking path from the bed (or primary chair) to the bathroom door.

    Args:
        rooms:               All positioned rooms from the spatial model.
        profile_min_width:   Minimum required clear width (metres). Default 0.9 m for walker.

    Returns:
        SafePath with waypoints, width_ok flag, and measured min_width_m.
    """
    # ------------------------------------------------------------------ #
    # 1. Locate bed and bathroom door                                      #
    # ------------------------------------------------------------------ #
    bed = bed_room = None
    for room in rooms:
        for obj in room.objects:
            if obj.category == "bed":
                bed, bed_room = obj, room
                break
        if bed:
            break

    bath_door = bath_room = None
    for room in rooms:
        if room.room_type == "bathroom":
            for obj in room.objects:
                if obj.category == "door":
                    bath_door, bath_room = obj, room
                    break
        if bath_door:
            break

    # Fallback: first door in any room that isn't the bed room
    if not bath_door:
        for room in rooms:
            if room is bed_room:
                continue
            for obj in room.objects:
                if obj.category == "door":
                    bath_door, bath_room = obj, room
                    break
            if bath_door:
                break

    # Last resort: any door
    if not bath_door:
        for room in rooms:
            for obj in room.objects:
                if obj.category == "door":
                    bath_door, bath_room = obj, room
                    break
            if bath_door:
                break

    if not bed:
        return SafePath(waypoints=[], width_ok=False, min_width_m=0.0)

    # ------------------------------------------------------------------ #
    # 2. Start point: front-centre of the bed                             #
    # ------------------------------------------------------------------ #
    start_x = bed.position["x"] + bed.dimensions["width"] / 2
    start_z = bed.position["z"] + bed.dimensions["depth"]
    waypoints: list[Waypoint] = [
        Waypoint(
            x=round(start_x, 2),
            y=0.0,
            z=round(start_z, 2),
            label="bed_exit",
            room_id=bed_room.room_id if bed_room else None,
        )
    ]
    path_2d: list[tuple[float, float]] = [(start_x, start_z)]

    if not bath_door:
        return SafePath(waypoints=waypoints, width_ok=False, min_width_m=0.0)

    end_x = bath_door.position["x"] + bath_door.dimensions["width"] / 2
    end_z = bath_door.position["z"]

    # ------------------------------------------------------------------ #
    # 3. Obstacle check and optional dodge in the bed room                #
    # ------------------------------------------------------------------ #
    bed_room_objects = bed_room.objects if bed_room else []
    blockers = [
        obj for obj in bed_room_objects
        if obj.category not in ("door", "bed")
        and _segment_hits_box(start_x, start_z, end_x, end_z, obj)
    ]

    if blockers:
        blocker = blockers[0]
        bx = blocker.position["x"] + blocker.dimensions["width"] / 2
        bz = blocker.position["z"] + blocker.dimensions["depth"] / 2

        dx, dz = end_x - start_x, end_z - start_z
        length = math.hypot(dx, dz)
        px, pz = -dz / length, dx / length   # perpendicular unit vector

        offset = max(blocker.dimensions["width"], blocker.dimensions["depth"]) / 2 + 0.5
        dodge_x = round(bx + px * offset, 2)
        dodge_z = round(bz + pz * offset, 2)

        waypoints.append(
            Waypoint(
                x=dodge_x,
                y=0.0,
                z=dodge_z,
                label="dodge",
                room_id=bed_room.room_id if bed_room else None,
            )
        )
        path_2d.append((dodge_x, dodge_z))

    # ------------------------------------------------------------------ #
    # 4. Multi-room routing: add bedroom door waypoint                    #
    # ------------------------------------------------------------------ #
    if bed_room and bath_room and bed_room.room_id != bath_room.room_id:
        bedroom_door = next(
            (o for o in bed_room.objects if o.category == "door"), None
        )
        if bedroom_door:
            dcx = round(bedroom_door.position["x"] + bedroom_door.dimensions["width"] / 2, 2)
            dcz = round(bedroom_door.position["z"], 2)
            waypoints.append(
                Waypoint(
                    x=dcx,
                    y=0.0,
                    z=dcz,
                    label="bedroom_door",
                    room_id=bed_room.room_id,
                )
            )
            path_2d.append((dcx, dcz))

        hallway_room = next(
            (
                room
                for room in rooms
                if room.room_type == "hallway"
                and room is not bed_room
                and room is not bath_room
            ),
            None,
        )
        if hallway_room:
            hx = round(hallway_room.dimensions["width"] / 2, 2)
            hz = round(hallway_room.dimensions["length"] / 2, 2)
            waypoints.append(
                Waypoint(
                    x=hx,
                    y=0.0,
                    z=hz,
                    label="hallway_mid",
                    room_id=hallway_room.room_id,
                )
            )
            path_2d.append((hx, hz))

    # ------------------------------------------------------------------ #
    # 5. Final waypoint: bathroom door                                    #
    # ------------------------------------------------------------------ #
    waypoints.append(
        Waypoint(
            x=round(end_x, 2),
            y=0.0,
            z=round(end_z, 2),
            label="bathroom_door",
            room_id=bath_room.room_id if bath_room else None,
        )
    )
    path_2d.append((round(end_x, 2), round(end_z, 2)))

    # ------------------------------------------------------------------ #
    # 6. Measure minimum clear width                                      #
    # ------------------------------------------------------------------ #
    all_objects = [obj for room in rooms for obj in room.objects]
    min_w = _min_clear_width(path_2d, all_objects)

    return SafePath(
        waypoints=waypoints,
        width_ok=min_w >= profile_min_width,
        min_width_m=min_w,
    )
