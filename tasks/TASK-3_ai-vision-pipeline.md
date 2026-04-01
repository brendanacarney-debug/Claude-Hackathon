# TASK 3: AI Vision Pipeline + Spatial Model

**Priority:** Start after TASK 1 scaffold exists. Can run in parallel with TASK 2.
**Estimated scope:** Claude Vision integration, photo analysis prompts, spatial room builder, path finder.
**Touches:** `backend/analysis.py`, `backend/spatial/`

---

## Why This Task Exists

This is the "magic" of the app. Raw photos go in, structured room data comes out. Claude Vision looks at the photos and identifies every object, estimates positions, and flags potential hazards. Then the spatial builder converts those relative descriptions ("rug is between the bed and the door") into absolute x/y/z coordinates that Three.js can render in 3D. Without this, we just have photos and a static fixture file.

---

## Deliverables

### 1. Claude Vision analysis (`backend/analysis.py`)

**Core function:**
```python
async def analyze_room_photos(images: list[ImageData], recovery_profile: str) -> VisionAnalysisResult:
    """
    Send room photos to Claude Vision and get structured object/room data back.
    
    Args:
        images: list of {image_bytes, room_type, upload_order}
        recovery_profile: e.g. "walker_after_fall"
    
    Returns:
        VisionAnalysisResult with detected objects, room layout, and raw observations
    """
```

**How to call Claude Vision:**

Use the Anthropic Python SDK. For each batch of photos (group by room_type), send a single message with all photos for that room:

```python
import anthropic
import base64

client = anthropic.Anthropic()

message = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=4096,
    messages=[{
        "role": "user",
        "content": [
            # Include each photo as an image block
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": base64.b64encode(image_bytes).decode()
                }
            },
            # ... more images ...
            {
                "type": "text",
                "text": ANALYSIS_PROMPT  # see below
            }
        ]
    }]
)
```

**The analysis prompt** -- this is the most important piece of engineering in the whole project. Craft it carefully:

```
You are analyzing photos of a room to help prepare it for a patient recovering at home after a fall. The patient uses a walker.

Look at these photos of a {room_type} and identify:

1. OBJECTS: List every piece of furniture, fixture, and item you can see. For each object, provide:
   - category: one of [bed, nightstand, chair, table, door, toilet, shelf, cord, clutter, lamp, grab_bar, walker, shower, bathtub, counter, cabinet, rug, other]
   - description: brief description (e.g., "small area rug with curled edges", "wooden chair with armrests")
   - relative_position: describe where it is relative to other objects and the room (e.g., "center of room floor, between bed and door", "against north wall beside bed", "mounted on wall above counter")
   - estimated_dimensions: rough size in meters (width, height, depth) -- be approximate
   - floor_level: true if the object is on or near the floor (below knee height), false otherwise
   - on_likely_walking_path: true if this object is in or near the path someone would walk through the room

2. ROOM LAYOUT:
   - approximate_dimensions: room width and length in meters (estimate from furniture scale)
   - door_positions: where are the doors/entrances relative to the room
   - floor_type: hardwood, carpet, tile, linoleum, or mixed
   - lighting_quality: bright, adequate, dim, or dark
   - overall_clutter_level: minimal, moderate, or cluttered

3. POTENTIAL HAZARDS you can see (from the perspective of a person using a walker):
   - List anything that looks like a trip risk, path obstruction, unstable surface, poor lighting, or accessibility issue
   - Be specific about what you see and where

Respond in JSON format with this structure:
{
  "objects": [...],
  "room_layout": {...},
  "observed_hazards": [...],
  "notes": "any additional observations relevant to walker safety"
}
```

**Important prompt engineering details:**
- Send all photos for one room in a single API call so Claude can triangulate object positions from multiple angles
- If there are photos labeled as different room types, make separate calls per room type
- Use `claude-sonnet-4-6` (not opus) -- faster and cheaper for vision, still very accurate
- Set `max_tokens=4096` -- the structured response can be long
- Parse the JSON response. If Claude returns it wrapped in markdown code fences, strip those first.
- If JSON parsing fails, retry once with a "please respond only in valid JSON" follow-up

**Define the return types:**

```python
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
```

### 2. Spatial room builder (`backend/spatial/room_builder.py`)

**Purpose:** Convert the relative position descriptions from Claude Vision into absolute x/y/z coordinates for Three.js rendering.

**Core function:**
```python
def build_room_model(vision_result: VisionAnalysisResult) -> Room:
    """
    Convert vision analysis into positioned Room objects.
    
    Strategy:
    1. Set room dimensions from vision_result.room_layout.approximate_dimensions
    2. Place anchor objects first (bed, door, toilet -- large/obvious items)
    3. Place remaining objects relative to anchors using heuristics
    4. Return Room with all objects positioned
    """
```

**Positioning heuristics** (these don't need to be perfect, just reasonable):

```python
# Room coordinate system:
# Origin (0,0,0) is the bottom-left corner of the room floor
# X axis: room width (left to right)
# Y axis: height (floor to ceiling)
# Z axis: room depth (front to back)

# Anchor placement rules:
PLACEMENT_RULES = {
    "bed": "against a wall, typically centered on one side of bedroom",
    "door": "flush with a wall, parse 'north wall' / 'opposite wall' from relative_position",
    "toilet": "against a wall in bathroom, usually back wall",
    "bathtub": "against a wall in bathroom, usually long wall",
    "counter": "against a wall in bathroom, usually near door",
}

# Relative placement:
# "beside bed" -> offset 0.5m from bed edge in X
# "between bed and door" -> midpoint of bed and door positions
# "against wall" -> X or Z = 0 or room_width/room_depth
# "center of room" -> room_width/2, room_depth/2
# "near door" -> within 1m of door position
# "on floor" -> y = 0
# "on wall" -> y = 1.5 (approximate wall mount height)
# "high shelf" -> y = 1.8
```

**Implementation approach:**
1. Parse the `relative_position` string for keywords (beside, between, near, against wall, center, etc.)
2. Place anchor objects first using room_type conventions
3. Place remaining objects relative to the nearest anchor mentioned in their relative_position
4. If nothing matches, use a grid fallback (spread unplaced objects evenly in empty space)
5. Assign UUIDs to each object
6. Set `on_primary_path` based on whether the object is within 0.5m of the line between the bed/chair and the nearest door

### 3. Path finder (`backend/spatial/path_finder.py`)

**Purpose:** Given positioned objects, compute a safe walking path from bed to bathroom.

**Core function:**
```python
def compute_safe_path(rooms: list[Room], profile: RecoveryProfile) -> SafePath:
    """
    Find a clear walking path from the bed (or primary chair) to the bathroom door.
    
    Returns waypoints and whether the path width is adequate for the profile.
    """
```

**Algorithm (keep it simple):**

1. Identify start point: center of bed's front edge (the side facing the room)
2. Identify end point: center of bathroom door
3. If they're in the same room: draw a straight line, check if any object bounding box intersects it
4. If objects block the straight line: add one waypoint to route around (offset perpendicular to the line by the object width + 0.5m)
5. If they're in different rooms: route through the connecting doors (bed -> bedroom_door -> hallway -> bathroom_door)
6. For each path segment, calculate the minimum clear width (distance from path centerline to nearest object on either side)
7. Compare min clear width to `profile.min_path_width_m` (0.9m for walker)
8. Set `width_ok` accordingly

**Don't overthink this.** A straight line with 1-2 dodge waypoints is fine. The visual impact of a glowing path on the 3D floor is what matters, not A* pathfinding.

### 4. Ghost rearrangement generator (`backend/spatial/rearrangements.py`)

```python
def suggest_rearrangements(rooms: list[Room], hazards: list[Hazard], recommendations: list[Recommendation]) -> list[GhostRearrangement]:
    """
    For hazards with 'remove' or 'move' recommendations, calculate where objects
    should go (or that they should disappear).
    """
```

Rules:
- If recommendation.category == "remove" (e.g., remove rug): return `action="remove"`, `new_position={0,0,0}`
- If recommendation.category == "move" (e.g., move chair): calculate a new position that clears the path. Simple approach: move the object perpendicular to the safe path until it's 0.5m away from the path edge
- Only generate rearrangements for objects that have a matching recommendation. Don't invent moves.

### 5. Wire into the analysis endpoint

Create an orchestrator function that TASK 2's `/analyze` route will call:

```python
# backend/pipeline.py

async def run_full_analysis(session_id: str, images: list[ImageData], recovery_profile: str) -> Session:
    """
    Full analysis pipeline:
    1. Send images to Claude Vision -> get detected objects per room
    2. Build spatial model -> get positioned Room objects
    3. Run hazard rules engine (TASK 4) -> get scored hazards
    4. Generate recommendations (TASK 4) -> get prioritized actions  
    5. Compute safe path -> get waypoints
    6. Generate rearrangements -> get ghost moves
    7. Generate checklist via Claude API (TASK 4) -> get first_night + first_48_hours
    8. Assemble and return full Session object
    """
```

For steps that depend on TASK 4 (rules engine, checklist generation), stub them to return fixture data for now. The pipeline should work end-to-end with stubs, then TASK 4 fills in the real logic.

---

## Files to create

```
backend/
  analysis.py              # Claude Vision integration
  pipeline.py              # Full analysis orchestrator
  spatial/
    __init__.py
    room_builder.py        # Vision output -> positioned 3D objects
    path_finder.py         # Compute safe walking path
    rearrangements.py      # Ghost rearrangement suggestions
```

---

## Definition of Done

- [ ] `analyze_room_photos()` sends images to Claude Vision and returns parsed structured JSON with objects, layout, and hazards
- [ ] `build_room_model()` converts relative position descriptions into x/y/z coordinates that make visual sense
- [ ] `compute_safe_path()` returns waypoints from bed to bathroom with min width calculation
- [ ] `suggest_rearrangements()` returns remove/move suggestions for hazardous objects
- [ ] `run_full_analysis()` chains all steps and returns a complete Session object (with stubs for rules engine and checklist)
- [ ] Can manually test by calling the pipeline with sample images and inspecting the output JSON
- [ ] The pipeline handles errors gracefully (bad image, Claude Vision timeout, malformed JSON response) without crashing the server
