# TASK 4: Hazard Rules Engine + Checklist Generation

**Priority:** Start after TASK 1 scaffold exists. Can run in parallel with TASK 2 and TASK 3.
**Estimated scope:** Hazard scoring rules, recommendation templates, Claude-powered checklist prose.
**Touches:** `backend/rules/`, `backend/checklist.py`

---

## Why This Task Exists

This is the brain of the product. The rules engine takes the objects detected by Claude Vision and scores them as hazards based on the recovery profile. A rug on the floor is harmless for a healthy person but an urgent trip hazard for someone using a walker. This context-dependent hazard interpretation is what makes the app useful -- not just "we see objects" but "we understand what those objects mean for YOUR recovery."

The checklist generator then turns the structured hazards into plain-language, actionable text that a stressed caregiver can follow at 10pm the night before their parent comes home.

---

## Deliverables

### 1. Recovery profiles (`backend/rules/profiles.py`)

Define the profiles as Python dataclasses or pydantic models:

```python
PROFILES = {
    "walker_after_fall": RecoveryProfile(
        profile_id="walker_after_fall",
        label="Walker after fall or fracture",
        constraints=["no_bending", "needs_walker_clearance", "fall_risk", "night_bathroom_risk"],
        min_path_width_m=0.9,
        hazard_weights={
            "floor_obstacle": 5,
            "path_obstruction": 5,
            "transfer_challenge": 4,
            "bathroom_risk": 5,
            "reachability_issue": 3,
            "lighting_issue": 4,
            "wound_care_issue": 2,
        }
    ),
    # Stretch: add more profiles later
    # "crutches_after_fracture": ...
    # "post_c_section": ...
    # "dizziness_fall_risk": ...
}
```

### 2. Hazard scoring engine (`backend/rules/engine.py`)

**Core function:**
```python
def score_hazards(
    rooms: list[Room],
    profile: RecoveryProfile,
    vision_hazards: list[str],  # raw hazard observations from Claude Vision
) -> list[Hazard]:
```

**Hazard detection rules -- implement ALL of these:**

#### Rule 1: Floor obstacles (class: `floor_obstacle`)
```
Trigger: any object where:
  - category in [rug, cord, clutter, other] AND
  - floor_level == true AND
  - on_primary_path == true (or within 0.5m of primary path)

Severity for walker_after_fall: URGENT (weight 5)

Special cases:
  - rug: always urgent if on path, regardless of size
  - cord: urgent if crossing path, moderate if beside path
  - clutter: urgent if on path, low if off path but in room
  - shoes/objects mentioned in vision_hazards: moderate
```

#### Rule 2: Path obstructions (class: `path_obstruction`)
```
Trigger: any object where:
  - on_primary_path == true AND
  - category in [chair, table, cabinet, other] AND
  - the path width at that point < profile.min_path_width_m (0.9m)

Severity: URGENT if path width < 0.7m, MODERATE if 0.7-0.9m

Also trigger if:
  - A doorway width < profile.min_path_width_m
  - Any furniture creates a "squeeze point" on the route
```

#### Rule 3: Transfer challenges (class: `transfer_challenge`)
```
Trigger: 
  - bed height < 0.45m (too low for easy sit-to-stand with walker)
  - bed height > 0.65m (too high, risk of falling when sitting down)
  - no stable object within 0.5m of bed edge for support during transfer
  - couch/chair with no armrests mentioned

Severity: MODERATE (weight 4)
```

#### Rule 4: Bathroom risks (class: `bathroom_risk`)
```
Trigger:
  - room_type == "bathroom" AND no grab_bar detected near toilet or bathtub
  - bathroom floor_type == "tile" (slip risk when wet)
  - bathtub/shower without visible non-slip surface
  - toilet without adjacent support surface within arm's reach
  - bathroom doorway threshold that could catch walker wheels

Severity: URGENT for no-support scenarios, MODERATE for surface risks
```

#### Rule 5: Reachability issues (class: `reachability_issue`)
```
Trigger:
  - any object with y position > 1.5m that likely contains essentials
    (shelf, cabinet at height)
  - essentials described as "on floor" or "low" (requires bending)
  - profile constraint includes "no_bending"
  - no nightstand or accessible surface beside bed

Severity: MODERATE (weight 3)
```

#### Rule 6: Lighting issues (class: `lighting_issue`)
```
Trigger:
  - any room on the bed-to-bathroom path where lighting_quality == "dim" or "dark"
  - hallway with no visible light source
  - no lamp within 1m of bed (nighttime reach)
  - bathroom with single overhead light and no night-light path

Severity: URGENT for dark route segments, MODERATE for dim
```

#### Rule 7: Wound care / hygiene setup (class: `wound_care_issue`)
```
Trigger:
  - profile constraint includes "wound_care" AND
  - no clean counter/surface detected in bathroom at appropriate height
  - supplies not visible near primary care area

Severity: LOW for walker_after_fall (weight 2), would be higher for surgical profiles
```

**Scoring and sorting:**
```python
def calculate_severity(hazard_class: str, profile: RecoveryProfile, specific_score: int) -> str:
    weight = profile.hazard_weights[hazard_class]
    combined = weight * specific_score  # specific_score: 1-3 from rule logic
    if combined >= 12:
        return "urgent"
    elif combined >= 6:
        return "moderate"
    else:
        return "low"
```

Sort final hazards: urgent first, then moderate, then low. Within same severity, sort by weight.

### 3. Recommendation templates (`backend/rules/recommendations.py`)

**Core function:**
```python
def generate_recommendations(hazards: list[Hazard], rooms: list[Room], profile: RecoveryProfile) -> list[Recommendation]:
```

Map each hazard to a recommendation. Use templates with slot-filling:

```python
RECOMMENDATION_TEMPLATES = {
    "floor_obstacle": {
        "rug": {
            "category": "remove",
            "text": "Remove the {description} from {location}. If it must stay, secure all edges flat with double-sided carpet tape.",
            "expected_benefit": "Eliminates trip hazard on {path_description}"
        },
        "cord": {
            "category": "move",
            "text": "Route the {description} along the wall or under furniture, away from the walking path. Use cord covers if it must cross a walkway.",
            "expected_benefit": "Clears trip hazard from {path_description}"
        },
        "clutter": {
            "category": "remove",
            "text": "Clear the {description} from the floor in {location}. Store items in a bin or on a shelf.",
            "expected_benefit": "Opens floor space for safe walker navigation"
        }
    },
    "path_obstruction": {
        "default": {
            "category": "move",
            "text": "Move the {description} to {suggested_new_location} to open at least {min_width}cm of clear width for the walker.",
            "expected_benefit": "Restores safe walker clearance on {path_description}"
        }
    },
    "transfer_challenge": {
        "low_bed": {
            "category": "professional",
            "text": "The bed appears low for safe sit-to-stand transfers. Consider bed risers or discuss with an occupational therapist. A stable chair or grab handle beside the bed can also help.",
            "expected_benefit": "Safer transfers, especially in early recovery days"
        }
    },
    "bathroom_risk": {
        "no_grab_bar": {
            "category": "professional",
            "text": "No grab bar detected near the {fixture}. A temporary clamp-on grab bar can be installed without drilling. Discuss permanent installation with your care team.",
            "expected_benefit": "Provides stable support during bathroom transfers"
        },
        "slip_surface": {
            "category": "add",
            "text": "Place a non-slip bath mat on the {surface_type} floor near the {fixture}. Ensure it has rubber backing and lies completely flat.",
            "expected_benefit": "Reduces slip risk on wet bathroom surfaces"
        }
    },
    "reachability_issue": {
        "high_items": {
            "category": "move",
            "text": "Move {items} from the high {surface} down to {accessible_surface} within arm's reach of the {reference_point}. Nothing essential should require reaching above shoulder height.",
            "expected_benefit": "Prevents unsafe reaching and reduces need to stand for basic items"
        },
        "low_items": {
            "category": "move",
            "text": "Move {items} from the floor up to {accessible_surface} at waist height. Bending to the floor increases fall risk.",
            "expected_benefit": "Eliminates bending requirement for daily essentials"
        }
    },
    "lighting_issue": {
        "dark_route": {
            "category": "add",
            "text": "Place a plug-in night light or motion-activated light in the {location}. The bathroom route must be visible without needing to find a switch at night.",
            "expected_benefit": "Reduces nighttime misstep risk on the bathroom route"
        },
        "no_bedside_lamp": {
            "category": "add",
            "text": "Place a lamp or touch-activated light within arm's reach of the bed. The patient should be able to light the room before standing up.",
            "expected_benefit": "Safe transition from lying down to standing"
        }
    },
    "wound_care_issue": {
        "default": {
            "category": "adjust",
            "text": "Set up a clean, accessible surface near {location} for wound care supplies. Keep dressings, antiseptic, and instructions together in a small tray or caddy.",
            "expected_benefit": "Organized wound care reduces infection risk and awkward positioning"
        }
    }
}
```

**Slot filling:**
- Parse the hazard explanation and related objects to fill `{description}`, `{location}`, etc.
- Set priority = index in the sorted hazard list (1 = highest priority)
- If a hazard doesn't match any specific template, use the "default" template for that class

### 4. Checklist generation via Claude API (`backend/checklist.py`)

**Core function:**
```python
async def generate_checklist(
    hazards: list[Hazard],
    recommendations: list[Recommendation],
    profile: RecoveryProfile
) -> Checklist:
```

**Implementation:**

```python
import anthropic

client = anthropic.Anthropic()

async def generate_checklist(hazards, recommendations, profile) -> Checklist:
    # Build context for Claude
    hazard_summary = "\n".join([
        f"- [{h.severity.upper()}] {h.explanation}" for h in hazards
    ])
    rec_summary = "\n".join([
        f"- Priority {r.priority}: {r.text}" for r in recommendations
    ])
    
    prompt = f"""You are a home safety advisor helping a caregiver prepare their home for a patient coming home from the hospital.

Patient profile: {profile.label}
Constraints: {', '.join(profile.constraints)}

Detected hazards:
{hazard_summary}

Recommendations:
{rec_summary}

Create two checklists:

1. FIRST NIGHT CHECKLIST: Things that MUST be done before the patient sleeps at home tonight. These should be quick, doable actions (15 minutes or less each). Focus on removing immediate dangers and setting up the essentials within reach.

2. FIRST 48 HOURS CHECKLIST: Things to do within the first two days. These can be slightly more involved (buying a night light, rearranging furniture, consulting a therapist).

Rules:
- Write in plain, direct language a stressed caregiver can follow
- Each item should be a single concrete action, not a vague suggestion
- Do not use medical jargon
- Do not give medical advice or mention specific medications
- Include 6-10 items in each checklist
- Start each item with an action verb (Remove, Move, Place, Check, etc.)

Respond in this exact JSON format:
{{
  "first_night": ["item1", "item2", ...],
  "first_48_hours": ["item1", "item2", ...]
}}"""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}]
    )
    
    # Parse JSON from response
    response_text = message.content[0].text
    # Strip markdown code fences if present
    if "```" in response_text:
        response_text = response_text.split("```")[1]
        if response_text.startswith("json"):
            response_text = response_text[4:]
    
    data = json.loads(response_text)
    return Checklist(
        first_night=data["first_night"],
        first_48_hours=data["first_48_hours"]
    )
```

**Fallback:** If the Claude API call fails (rate limit, timeout, etc.), return a pre-written generic checklist based on the profile. NEVER let the checklist generation break the whole analysis pipeline.

```python
FALLBACK_CHECKLISTS = {
    "walker_after_fall": Checklist(
        first_night=[
            "Remove all loose rugs from the path between bed and bathroom",
            "Clear the walking path of any furniture, shoes, or clutter",
            "Place the walker within arm's reach of the bed",
            "Put a night light in the hallway and bathroom",
            "Move water, medications, phone, and charger to the nightstand",
            "Make sure all doors on the bathroom route are fully open",
            "Place a non-slip mat in the bathroom if the floor is tile",
            "Test that the patient can reach the light switch from bed"
        ],
        first_48_hours=[
            "Install or arrange a grab bar near the toilet",
            "Practice the bed-to-bathroom route together during daytime",
            "Route all cords along walls, not across walking paths",
            "Check if the bed height is comfortable for sit-to-stand transfers",
            "Set up a bedside caddy with all daily essentials in one place",
            "Confirm the patient can reach the phone or call button from bed at night"
        ]
    )
}
```

---

## Files to create

```
backend/
  rules/
    __init__.py
    profiles.py          # Recovery profile definitions
    engine.py            # Hazard detection and scoring
    recommendations.py   # Recommendation templates and generation
  checklist.py           # Claude API checklist generation + fallback
```

---

## Definition of Done

- [ ] `score_hazards()` takes a list of Room objects with positioned objects and returns correctly classified hazards for the walker_after_fall profile
- [ ] A rug on the primary path scores as urgent floor_obstacle
- [ ] A chair narrowing the path below 0.9m scores as urgent path_obstruction
- [ ] A dark hallway on the route scores as urgent lighting_issue
- [ ] High shelf items score as moderate reachability_issue
- [ ] Low bed scores as moderate transfer_challenge
- [ ] `generate_recommendations()` returns one recommendation per hazard with filled-in templates (no `{placeholder}` text in output)
- [ ] `generate_checklist()` calls Claude API and returns parsed first_night + first_48_hours arrays
- [ ] If Claude API fails, the fallback checklist is returned and the pipeline doesn't crash
- [ ] All hazards are sorted by severity (urgent first), recommendations are numbered by priority
- [ ] Test with the fixture objects from `fixtures/demo_session.json` and verify the output matches the expected 5 hazards
