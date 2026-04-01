from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ObjectCategory(str, Enum):
    RUG = "rug"
    BED = "bed"
    CHAIR = "chair"
    TABLE = "table"
    DOOR = "door"
    TOILET = "toilet"
    SHELF = "shelf"
    CORD = "cord"
    CLUTTER = "clutter"
    LAMP = "lamp"
    GRAB_BAR = "grab_bar"
    WALKER = "walker"
    NIGHTSTAND = "nightstand"
    SHOWER = "shower"
    BATHTUB = "bathtub"
    COUNTER = "counter"
    CABINET = "cabinet"
    OTHER = "other"


class HazardClass(str, Enum):
    FLOOR_OBSTACLE = "floor_obstacle"
    PATH_OBSTRUCTION = "path_obstruction"
    TRANSFER_CHALLENGE = "transfer_challenge"
    BATHROOM_RISK = "bathroom_risk"
    REACHABILITY_ISSUE = "reachability_issue"
    LIGHTING_ISSUE = "lighting_issue"
    WOUND_CARE_ISSUE = "wound_care_issue"


class Severity(str, Enum):
    URGENT = "urgent"
    MODERATE = "moderate"
    LOW = "low"


class RecommendationCategory(str, Enum):
    REMOVE = "remove"
    MOVE = "move"
    ADD = "add"
    ADJUST = "adjust"
    PROFESSIONAL = "professional"


@dataclass(slots=True)
class Vector3:
    x: float
    y: float
    z: float

    @classmethod
    def from_dict(cls, data: Any) -> "Vector3":
        return cls(
            x=float(_read(data, "x", 0.0)),
            y=float(_read(data, "y", 0.0)),
            z=float(_read(data, "z", 0.0)),
        )

    def to_dict(self) -> dict[str, float]:
        return {"x": self.x, "y": self.y, "z": self.z}


@dataclass(slots=True)
class Dimensions:
    width: float
    height: float
    depth: float

    @classmethod
    def from_dict(cls, data: Any) -> "Dimensions":
        return cls(
            width=float(_read(data, "width", 0.0)),
            height=float(_read(data, "height", 0.0)),
            depth=float(_read(data, "depth", 0.0)),
        )

    def to_dict(self) -> dict[str, float]:
        return {
            "width": self.width,
            "height": self.height,
            "depth": self.depth,
        }


@dataclass(slots=True)
class RoomObject:
    object_id: str
    category: str
    position: Vector3
    dimensions: Dimensions
    on_primary_path: bool = False
    confidence: float = 1.0
    description: str = ""
    relative_position: str = ""
    floor_level: bool | None = None
    supportive: bool | None = None
    armrests: bool | None = None
    path_clearance_m: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Any) -> "RoomObject":
        metadata = dict(_read(data, "metadata", {}) or {})
        return cls(
            object_id=str(_require(data, "object_id")),
            category=_normalize_value(_read(data, "category", ObjectCategory.OTHER.value)),
            position=Vector3.from_dict(_read(data, "position", {})),
            dimensions=Dimensions.from_dict(_read(data, "dimensions", {})),
            on_primary_path=bool(_read(data, "on_primary_path", False)),
            confidence=float(_read(data, "confidence", 1.0)),
            description=str(_read(data, "description", "")),
            relative_position=str(_read(data, "relative_position", "")),
            floor_level=_optional_bool(_read(data, "floor_level")),
            supportive=_optional_bool(_read(data, "supportive")),
            armrests=_optional_bool(_read(data, "armrests")),
            path_clearance_m=_optional_float(
                _read(data, "path_clearance_m", metadata.get("path_clearance_m"))
            ),
            metadata=metadata,
        )

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "object_id": self.object_id,
            "category": self.category,
            "position": self.position.to_dict(),
            "dimensions": self.dimensions.to_dict(),
            "on_primary_path": self.on_primary_path,
            "confidence": self.confidence,
        }
        if self.description:
            payload["description"] = self.description
        if self.relative_position:
            payload["relative_position"] = self.relative_position
        if self.floor_level is not None:
            payload["floor_level"] = self.floor_level
        if self.supportive is not None:
            payload["supportive"] = self.supportive
        if self.armrests is not None:
            payload["armrests"] = self.armrests
        if self.path_clearance_m is not None:
            payload["path_clearance_m"] = self.path_clearance_m
        if self.metadata:
            payload["metadata"] = self.metadata
        return payload


@dataclass(slots=True)
class Room:
    room_id: str
    room_type: str
    objects: list[RoomObject]
    floor_type: str | None = None
    lighting_quality: str | None = None
    doorway_width_m: float | None = None
    threshold_height_m: float | None = None
    notes: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Any) -> "Room":
        metadata = dict(_read(data, "metadata", {}) or {})
        return cls(
            room_id=str(_require(data, "room_id")),
            room_type=str(_require(data, "room_type")),
            objects=[RoomObject.from_dict(item) for item in _read(data, "objects", [])],
            floor_type=_optional_str(_read(data, "floor_type")),
            lighting_quality=_optional_str(_read(data, "lighting_quality")),
            doorway_width_m=_optional_float(
                _read(data, "doorway_width_m", metadata.get("doorway_width_m"))
            ),
            threshold_height_m=_optional_float(
                _read(data, "threshold_height_m", metadata.get("threshold_height_m"))
            ),
            notes=str(_read(data, "notes", "")),
            metadata=metadata,
        )

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "room_id": self.room_id,
            "room_type": self.room_type,
            "objects": [item.to_dict() for item in self.objects],
        }
        if self.floor_type:
            payload["floor_type"] = self.floor_type
        if self.lighting_quality:
            payload["lighting_quality"] = self.lighting_quality
        if self.doorway_width_m is not None:
            payload["doorway_width_m"] = self.doorway_width_m
        if self.threshold_height_m is not None:
            payload["threshold_height_m"] = self.threshold_height_m
        if self.notes:
            payload["notes"] = self.notes
        if self.metadata:
            payload["metadata"] = self.metadata
        return payload


@dataclass(slots=True)
class Hazard:
    hazard_id: str
    hazard_class: str
    severity: str
    explanation: str
    related_object_ids: list[str] = field(default_factory=list)
    recommendation_ids: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Any) -> "Hazard":
        return cls(
            hazard_id=str(_require(data, "hazard_id")),
            hazard_class=_normalize_value(
                _read(data, "class", _read(data, "hazard_class", HazardClass.FLOOR_OBSTACLE.value))
            ),
            severity=_normalize_value(_read(data, "severity", Severity.LOW.value)),
            explanation=str(_read(data, "explanation", "")),
            related_object_ids=[str(item) for item in _read(data, "related_object_ids", [])],
            recommendation_ids=[str(item) for item in _read(data, "recommendation_ids", [])],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "hazard_id": self.hazard_id,
            "class": self.hazard_class,
            "severity": self.severity,
            "explanation": self.explanation,
            "related_object_ids": list(self.related_object_ids),
            "recommendation_ids": list(self.recommendation_ids),
        }


@dataclass(slots=True)
class Recommendation:
    recommendation_id: str
    priority: int
    category: str
    text: str
    target_location: str
    expected_benefit: str

    @classmethod
    def from_dict(cls, data: Any) -> "Recommendation":
        return cls(
            recommendation_id=str(_require(data, "recommendation_id")),
            priority=int(_read(data, "priority", 0)),
            category=_normalize_value(_read(data, "category", RecommendationCategory.ADJUST.value)),
            text=str(_read(data, "text", "")),
            target_location=str(_read(data, "target_location", "")),
            expected_benefit=str(_read(data, "expected_benefit", "")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "recommendation_id": self.recommendation_id,
            "priority": self.priority,
            "category": self.category,
            "text": self.text,
            "target_location": self.target_location,
            "expected_benefit": self.expected_benefit,
        }


@dataclass(slots=True)
class Checklist:
    first_night: list[str]
    first_48_hours: list[str]

    @classmethod
    def from_dict(cls, data: Any) -> "Checklist":
        return cls(
            first_night=[str(item) for item in _read(data, "first_night", [])],
            first_48_hours=[str(item) for item in _read(data, "first_48_hours", [])],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "first_night": list(self.first_night),
            "first_48_hours": list(self.first_48_hours),
        }


@dataclass(slots=True)
class RecoveryProfile:
    profile_id: str
    label: str
    constraints: list[str]
    min_path_width_m: float
    hazard_weights: dict[str, int]

    @classmethod
    def from_dict(cls, data: Any) -> "RecoveryProfile":
        return cls(
            profile_id=str(_require(data, "profile_id")),
            label=str(_require(data, "label")),
            constraints=[str(item) for item in _read(data, "constraints", [])],
            min_path_width_m=float(_read(data, "min_path_width_m", 0.0)),
            hazard_weights={
                str(key): int(value)
                for key, value in dict(_read(data, "hazard_weights", {}) or {}).items()
            },
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "label": self.label,
            "constraints": list(self.constraints),
            "min_path_width_m": self.min_path_width_m,
            "hazard_weights": dict(self.hazard_weights),
        }


def coerce_room(value: Room | dict[str, Any]) -> Room:
    return value if isinstance(value, Room) else Room.from_dict(value)


def coerce_rooms(values: list[Room] | list[dict[str, Any]]) -> list[Room]:
    return [coerce_room(value) for value in values]


def coerce_hazard(value: Hazard | dict[str, Any]) -> Hazard:
    return value if isinstance(value, Hazard) else Hazard.from_dict(value)


def coerce_hazards(values: list[Hazard] | list[dict[str, Any]]) -> list[Hazard]:
    return [coerce_hazard(value) for value in values]


def coerce_recommendation(value: Recommendation | dict[str, Any]) -> Recommendation:
    return value if isinstance(value, Recommendation) else Recommendation.from_dict(value)


def coerce_recommendations(
    values: list[Recommendation] | list[dict[str, Any]]
) -> list[Recommendation]:
    return [coerce_recommendation(value) for value in values]


def coerce_profile(value: RecoveryProfile | dict[str, Any]) -> RecoveryProfile:
    return value if isinstance(value, RecoveryProfile) else RecoveryProfile.from_dict(value)


def _read(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(key, default)
    return getattr(value, key, default)


def _require(value: Any, key: str) -> Any:
    if isinstance(value, dict):
        return value[key]
    return getattr(value, key)


def _normalize_value(value: Any) -> str:
    if isinstance(value, Enum):
        return value.value
    return str(value)


def _optional_bool(value: Any) -> bool | None:
    if value is None:
        return None
    return bool(value)


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
