import json
import base64
import logging
import os
import re
from dataclasses import dataclass

try:
    import anthropic
except ImportError:  # pragma: no cover - depends on local environment
    anthropic = None

log = logging.getLogger(__name__)

_async_client = None

# Supported MIME types for Anthropic Vision API
_MEDIA_TYPES = {
    b"\xff\xd8": "image/jpeg",
    b"\x89P":    "image/png",
    b"RIFF":     "image/webp",
    b"GIF8":     "image/gif",
}

ANALYSIS_PROMPT = """\
You are analyzing photos of a {room_type} to help prepare it for a patient recovering at home \
after a fall. The patient uses a walker.

Look at these photos and identify:

1. OBJECTS: List every piece of furniture, fixture, and item you can see. For each object:
   - category: one of [bed, nightstand, chair, table, door, toilet, shelf, cord, clutter, \
lamp, grab_bar, walker, shower, bathtub, counter, cabinet, rug, other]
   - description: brief description (e.g. "small area rug with curled edges")
   - relative_position: where it is relative to other objects and the room \
(e.g. "center of room floor, between bed and door", "against north wall beside bed")
   - estimated_dimensions: rough size in meters as {{width, height, depth}}
   - floor_level: true if on or near the floor (below knee height), false otherwise
   - on_likely_walking_path: true if in or near the path someone would walk through the room

2. ROOM LAYOUT:
   - approximate_dimensions: room width and length in meters (estimate from furniture scale)
   - door_positions: where doors/entrances are relative to the room
   - floor_type: hardwood, carpet, tile, linoleum, or mixed
   - lighting_quality: bright, adequate, dim, or dark
   - overall_clutter_level: minimal, moderate, or cluttered

3. POTENTIAL HAZARDS (from the perspective of a person using a walker):
   - List anything that looks like a trip risk, path obstruction, unstable surface, \
poor lighting, or accessibility issue
   - Be specific about what you see and where

Respond ONLY in valid JSON with this exact structure (no markdown, no code fences):
{{
  "objects": [
    {{
      "category": "...",
      "description": "...",
      "relative_position": "...",
      "estimated_dimensions": {{"width": 0.0, "height": 0.0, "depth": 0.0}},
      "floor_level": true,
      "on_likely_walking_path": false
    }}
  ],
  "room_layout": {{
    "approximate_dimensions": {{"width": 0.0, "length": 0.0}},
    "door_positions": ["..."],
    "floor_type": "...",
    "lighting_quality": "...",
    "overall_clutter_level": "..."
  }},
  "observed_hazards": ["..."],
  "notes": "..."
}}\
"""

RETRY_PROMPT = (
    "Please respond only in valid JSON with no markdown formatting, "
    "no code fences — just the raw JSON object as specified."
)


@dataclass
class DetectedObject:
    category: str
    description: str
    relative_position: str
    estimated_dimensions: dict  # {width, height, depth}
    floor_level: bool
    on_likely_walking_path: bool


@dataclass
class RoomLayout:
    approximate_dimensions: dict  # {width, length}
    door_positions: list[str]
    floor_type: str
    lighting_quality: str
    overall_clutter_level: str


@dataclass
class VisionAnalysisResult:
    room_type: str
    objects: list[DetectedObject]
    room_layout: RoomLayout
    observed_hazards: list[str]
    notes: str


@dataclass
class ImageData:
    image_bytes: bytes
    room_type: str
    upload_order: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _detect_media_type(image_bytes: bytes) -> str:
    """
    Detect MIME type from magic bytes.
    Falls back to image/jpeg for unrecognized formats (Anthropic's most tolerant type).
    """
    header = image_bytes[:4]
    for magic, mime in _MEDIA_TYPES.items():
        if header[: len(magic)] == magic:
            return mime
    return "image/jpeg"


def _strip_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _parse_response(raw: str, room_type: str) -> VisionAnalysisResult:
    data = json.loads(_strip_fences(raw))

    objects = [
        DetectedObject(
            category=obj.get("category", "other"),
            description=obj.get("description", ""),
            relative_position=obj.get("relative_position", ""),
            estimated_dimensions=obj.get(
                "estimated_dimensions", {"width": 0.5, "height": 0.5, "depth": 0.5}
            ),
            floor_level=bool(obj.get("floor_level", False)),
            on_likely_walking_path=bool(obj.get("on_likely_walking_path", False)),
        )
        for obj in data.get("objects", [])
    ]

    layout = data.get("room_layout", {})
    room_layout = RoomLayout(
        approximate_dimensions=layout.get(
            "approximate_dimensions", {"width": 4.0, "length": 5.0}
        ),
        door_positions=layout.get("door_positions", []),
        floor_type=layout.get("floor_type", "unknown"),
        lighting_quality=layout.get("lighting_quality", "adequate"),
        overall_clutter_level=layout.get("overall_clutter_level", "minimal"),
    )

    return VisionAnalysisResult(
        room_type=room_type,
        objects=objects,
        room_layout=room_layout,
        observed_hazards=data.get("observed_hazards", []),
        notes=data.get("notes", ""),
    )


def _build_content(images: list[ImageData], room_type: str) -> list[dict]:
    content: list[dict] = []
    for img in images:
        media_type = _detect_media_type(img.image_bytes)
        content.append(
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": base64.b64encode(img.image_bytes).decode(),
                },
            }
        )
    content.append(
        {"type": "text", "text": ANALYSIS_PROMPT.format(room_type=room_type)}
    )
    return content


def _get_async_client():
    global _async_client

    if anthropic is None:
        raise RuntimeError(
            "The anthropic SDK is not installed. Install backend requirements to run vision analysis."
        )

    if _async_client is None:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set.")
        _async_client = anthropic.AsyncAnthropic(api_key=api_key)

    return _async_client


async def _analyze_room(images: list[ImageData], room_type: str) -> VisionAnalysisResult:
    """
    Send all photos for one room to Claude Vision and parse the result.

    Retries once with a strict JSON-only instruction if the first response
    cannot be parsed. Raises on second failure.
    """
    content = _build_content(images, room_type)

    client = _get_async_client()

    response = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        messages=[{"role": "user", "content": content}],
    )
    raw = response.content[0].text

    try:
        return _parse_response(raw, room_type)
    except (json.JSONDecodeError, KeyError) as first_err:
        log.warning(
            "Vision response for room_type=%r was not valid JSON; retrying. Error: %s",
            room_type,
            first_err,
        )
        retry_response = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            messages=[
                {"role": "user", "content": content},
                {"role": "assistant", "content": raw},
                {"role": "user", "content": RETRY_PROMPT},
            ],
        )
        # Let the parse error propagate on second failure — caller handles it
        return _parse_response(retry_response.content[0].text, room_type)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def analyze_room_photos(
    images: list[ImageData], recovery_profile: str
) -> list[VisionAnalysisResult]:
    """
    Send room photos to Claude Vision and get structured object/room data back.

    Groups images by room_type and sends each group as a single API call so
    Claude can triangulate object positions from multiple angles.

    Per-room failures are logged and re-raised with room context so TASK 2's
    error handler can set session status to "error" with a useful message.

    Args:
        images:           list of ImageData (image_bytes, room_type, upload_order).
                          Must be non-empty.
        recovery_profile: e.g. "walker_after_fall" (reserved for future prompt tuning).

    Returns:
        One VisionAnalysisResult per distinct room_type, in the order rooms
        were first encountered in the images list.

    Raises:
        ValueError:            if images is empty.
        json.JSONDecodeError:  if Claude returns unparseable JSON after retry.
        anthropic.APIError:    on API-level failures (auth, rate limit, timeout).
    """
    if not images:
        raise ValueError("analyze_room_photos requires at least one image")

    # Group by room_type, preserving first-encounter order
    by_room: dict[str, list[ImageData]] = {}
    for img in images:
        by_room.setdefault(img.room_type, []).append(img)

    results: list[VisionAnalysisResult] = []
    for room_type, room_images in by_room.items():
        room_images.sort(key=lambda i: i.upload_order)
        try:
            result = await _analyze_room(room_images, room_type)
            results.append(result)
        except Exception as exc:
            log.error(
                "Vision analysis failed for room_type=%r with %d image(s): %s",
                room_type,
                len(room_images),
                exc,
            )
            raise RuntimeError(
                f"Vision analysis failed for room '{room_type}': {exc}"
            ) from exc

    return results
