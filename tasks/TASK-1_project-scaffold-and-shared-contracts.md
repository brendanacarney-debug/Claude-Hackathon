# TASK 1: Project Scaffold + Shared Contracts

**Priority:** Do this FIRST -- everything else depends on it.
**Estimated scope:** Repo skeleton, shared TypeScript + Python types, fixture data, dev scripts, config files.
**Touches:** Root, `shared/`, `backend/`, `web-app/`, `fixtures/`, `scripts/`

---

## Why This Task Exists

Agents building the backend and frontend need to agree on data shapes before writing a single line of logic. This task creates the shared contracts (TypeScript types AND Python pydantic models), scaffolds both projects so they can run hello-world, creates realistic fixture/mock data so the frontend can develop without a live backend, and sets up the dev tooling so `scripts/dev.sh` starts everything.

---

## Deliverables

### 1. Root-level repo setup

**`.gitignore`** -- must cover:
```
# Python
__pycache__/
*.pyc
.venv/
backend/.env

# Node
node_modules/
.next/
web-app/.env.local
web-app/.env.production

# General
.DS_Store
*.log
.env
```

**`CLAUDE.md`** -- project conventions for Claude Code sessions:
```markdown
# HomeRecover Scan

## Project structure
- `backend/` -- FastAPI (Python 3.11+), run with `uvicorn backend.main:app --reload`
- `web-app/` -- Next.js 14 (TypeScript + Tailwind), run with `cd web-app && npm run dev`
- `shared/` -- Shared type definitions (TypeScript + Python pydantic)
- `fixtures/` -- Demo data and sample sessions
- `scripts/` -- Dev and test helper scripts

## Conventions
- All API responses follow the session JSON contract in `shared/`
- Backend uses pydantic models from `shared/schemas.py`
- Frontend uses TypeScript types from `shared/types.ts`
- Every API response includes a `disclaimer` field
- No medical language that implies diagnosis or clearance
- Mobile-first responsive design
- Colors: Blue-600 primary, Amber-500 warnings, Red-500 urgent, Green-500 safe
```

### 2. Shared type definitions

**`shared/types.ts`** -- TypeScript types used by the frontend:

Must define these exact interfaces (matching the contract from `AGENT_BUILD_PLAN.md`):
- `RecoveryProfile` -- profile_id, label, constraints (string array), min_path_width_m, hazard_weights (record of hazard class to number)
- `RoomObject` -- object_id, category (enum: rug, bed, chair, table, door, toilet, shelf, cord, clutter, lamp, grab_bar, walker, nightstand, shower, bathtub, counter, cabinet, other), position ({x,y,z}), dimensions ({width,height,depth}), on_primary_path (boolean), confidence (number)
- `Room` -- room_id, room_type (enum: bedroom, bathroom, hallway), objects (RoomObject array)
- `HazardClass` -- enum: floor_obstacle, path_obstruction, transfer_challenge, bathroom_risk, reachability_issue, lighting_issue, wound_care_issue
- `Severity` -- enum: urgent, moderate, low
- `Hazard` -- hazard_id, class (HazardClass), severity (Severity), explanation (string), related_object_ids (string array), recommendation_ids (string array)
- `RecommendationCategory` -- enum: remove, move, add, adjust, professional
- `Recommendation` -- recommendation_id, priority (number), category (RecommendationCategory), text (string), target_location (string), expected_benefit (string)
- `SafePath` -- waypoints (array of {x,y,z,label}), width_ok (boolean), min_width_m (number)
- `GhostRearrangement` -- object_id, action (enum: remove, move), new_position ({x,y,z}), reason (string)
- `Checklist` -- first_night (string array), first_48_hours (string array)
- `SessionStatus` -- enum: created, uploading, analyzing, analyzed, error
- `Session` -- session_id, created_at (string), recovery_profile (string), status (SessionStatus), rooms (Room array), hazards (Hazard array), recommendations (Recommendation array), safe_path (SafePath), checklist (Checklist), ghost_rearrangements (GhostRearrangement array), images ({originals: string[], annotated: string[]}), disclaimer (string)

**`shared/schemas.py`** -- Python pydantic v2 models mirroring the exact same shapes:

Same types as above but using:
- `from pydantic import BaseModel`
- `from enum import Enum`
- Python enums for HazardClass, Severity, SessionStatus, RecommendationCategory, ObjectCategory
- All field names use snake_case (same as the JSON keys)
- Include a `model_config = ConfigDict(from_attributes=True)` on each model

### 3. Scaffold the backend

**`backend/requirements.txt`:**
```
fastapi==0.115.0
uvicorn[standard]==0.30.0
anthropic==0.40.0
supabase==2.10.0
python-multipart==0.0.12
pydantic==2.9.0
python-dotenv==1.0.1
```

**`backend/.env.example`:**
```
ANTHROPIC_API_KEY=sk-ant-...
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-key
```

**`backend/config.py`:**
- Load env vars from `.env` using python-dotenv
- Export `ANTHROPIC_API_KEY`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`
- Raise clear errors if required vars are missing

**`backend/main.py`** -- minimal working FastAPI app:
- CORS middleware allowing all origins (`*`) -- it's a hackathon
- Health check endpoint `GET /health` returning `{"status": "ok"}`
- Stub routes for all 6 endpoints (return 501 Not Implemented with correct path):
  - `POST /sessions`
  - `POST /sessions/{session_id}/upload`
  - `POST /sessions/{session_id}/analyze`
  - `GET /sessions/{session_id}`
  - `GET /sessions/{session_id}/export`
  - `GET /profiles`
- Import models from `shared/schemas.py` (use `sys.path` or relative import)

### 4. Scaffold the frontend

Run inside repo root:
```bash
npx create-next-app@latest web-app --typescript --tailwind --eslint --app --src-dir --no-git
```

Then install additional dependencies:
```bash
cd web-app && npm install three @react-three/fiber @react-three/drei framer-motion
npm install -D @types/three
```

**`web-app/.env.example`:**
```
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_DEMO_MODE=false
```

**`web-app/src/lib/types.ts`:**
- Re-export all types from `../../shared/types.ts`, or copy them if the import path is annoying in Next.js. Just keep them in sync.

**`web-app/src/lib/api.ts`** -- typed API client stub:
```typescript
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function createSession(profileId: string): Promise<{session_id: string}> { ... }
export async function uploadPhotos(sessionId: string, photos: File[], roomTypes: string[]): Promise<void> { ... }
export async function analyzeSession(sessionId: string): Promise<void> { ... }
export async function getSession(sessionId: string): Promise<Session> { ... }
export async function getProfiles(): Promise<RecoveryProfile[]> { ... }
export async function exportChecklist(sessionId: string): Promise<string> { ... }
```
Each function does a `fetch()` to the backend. For now they can return mock data if `NEXT_PUBLIC_DEMO_MODE=true`.

**`web-app/src/lib/mockData.ts`:**
- Import and re-export the fixture session (see section 5 below)
- This is what the frontend uses during development

### 5. Create fixture / demo data

**`fixtures/demo_session.json`** -- a COMPLETE analyzed session JSON. This is critical. It must be realistic enough to power the entire frontend during development and serve as the demo-day backup.

Contents:
```json
{
  "session_id": "demo-session-001",
  "created_at": "2026-04-01T14:30:00Z",
  "recovery_profile": "walker_after_fall",
  "status": "analyzed",
  "rooms": [
    {
      "room_id": "room-bedroom-001",
      "room_type": "bedroom",
      "objects": [
        {"object_id": "obj-001", "category": "bed", "position": {"x": 1.0, "y": 0.0, "z": 0.5}, "dimensions": {"width": 1.6, "height": 0.55, "depth": 2.0}, "on_primary_path": false, "confidence": 0.95},
        {"object_id": "obj-002", "category": "nightstand", "position": {"x": 2.7, "y": 0.0, "z": 0.5}, "dimensions": {"width": 0.5, "height": 0.6, "depth": 0.4}, "on_primary_path": false, "confidence": 0.90},
        {"object_id": "obj-003", "category": "rug", "position": {"x": 2.5, "y": 0.0, "z": 2.0}, "dimensions": {"width": 1.2, "height": 0.01, "depth": 0.8}, "on_primary_path": true, "confidence": 0.88},
        {"object_id": "obj-004", "category": "chair", "position": {"x": 3.5, "y": 0.0, "z": 1.5}, "dimensions": {"width": 0.6, "height": 0.85, "depth": 0.6}, "on_primary_path": true, "confidence": 0.92},
        {"object_id": "obj-005", "category": "door", "position": {"x": 4.5, "y": 0.0, "z": 2.0}, "dimensions": {"width": 0.9, "height": 2.1, "depth": 0.05}, "on_primary_path": true, "confidence": 0.97},
        {"object_id": "obj-006", "category": "lamp", "position": {"x": 2.7, "y": 0.6, "z": 0.5}, "dimensions": {"width": 0.3, "height": 0.5, "depth": 0.3}, "on_primary_path": false, "confidence": 0.85},
        {"object_id": "obj-007", "category": "shelf", "position": {"x": 0.2, "y": 1.8, "z": 2.5}, "dimensions": {"width": 1.0, "height": 0.3, "depth": 0.25}, "on_primary_path": false, "confidence": 0.80}
      ]
    },
    {
      "room_id": "room-hallway-001",
      "room_type": "hallway",
      "objects": [
        {"object_id": "obj-008", "category": "door", "position": {"x": 0.0, "y": 0.0, "z": 0.0}, "dimensions": {"width": 0.9, "height": 2.1, "depth": 0.05}, "on_primary_path": true, "confidence": 0.95},
        {"object_id": "obj-009", "category": "door", "position": {"x": 3.0, "y": 0.0, "z": 0.0}, "dimensions": {"width": 0.85, "height": 2.1, "depth": 0.05}, "on_primary_path": true, "confidence": 0.95}
      ]
    },
    {
      "room_id": "room-bathroom-001",
      "room_type": "bathroom",
      "objects": [
        {"object_id": "obj-010", "category": "toilet", "position": {"x": 0.5, "y": 0.0, "z": 0.5}, "dimensions": {"width": 0.4, "height": 0.4, "depth": 0.65}, "on_primary_path": false, "confidence": 0.95},
        {"object_id": "obj-011", "category": "bathtub", "position": {"x": 1.5, "y": 0.0, "z": 0.0}, "dimensions": {"width": 0.7, "height": 0.5, "depth": 1.5}, "on_primary_path": false, "confidence": 0.93},
        {"object_id": "obj-012", "category": "counter", "position": {"x": 0.0, "y": 0.0, "z": 1.5}, "dimensions": {"width": 1.0, "height": 0.85, "depth": 0.5}, "on_primary_path": false, "confidence": 0.90}
      ]
    }
  ],
  "hazards": [
    {
      "hazard_id": "haz-001",
      "class": "floor_obstacle",
      "severity": "urgent",
      "explanation": "Loose area rug on the direct path between bed and bedroom door. High trip risk when using a walker, especially at night.",
      "related_object_ids": ["obj-003"],
      "recommendation_ids": ["rec-001"]
    },
    {
      "hazard_id": "haz-002",
      "class": "path_obstruction",
      "severity": "urgent",
      "explanation": "Chair partially blocks the walking path from bed to door, narrowing the usable width below the 90cm minimum needed for safe walker navigation.",
      "related_object_ids": ["obj-004"],
      "recommendation_ids": ["rec-002"]
    },
    {
      "hazard_id": "haz-003",
      "class": "lighting_issue",
      "severity": "urgent",
      "explanation": "Hallway between bedroom and bathroom has no visible light source. Nighttime bathroom trips are a primary fall risk scenario.",
      "related_object_ids": ["obj-008", "obj-009"],
      "recommendation_ids": ["rec-003"]
    },
    {
      "hazard_id": "haz-004",
      "class": "transfer_challenge",
      "severity": "moderate",
      "explanation": "Bed height appears low (approximately 55cm). Without a stable surface at the right height beside the bed, sit-to-stand transfers are more difficult and dangerous with a walker.",
      "related_object_ids": ["obj-001", "obj-002"],
      "recommendation_ids": ["rec-005"]
    },
    {
      "hazard_id": "haz-005",
      "class": "reachability_issue",
      "severity": "moderate",
      "explanation": "Wall shelf at 1.8m height stores items that may include medications or daily essentials. Reaching overhead is risky for a fall-recovery patient and may require unsafe stretching.",
      "related_object_ids": ["obj-007"],
      "recommendation_ids": ["rec-004"]
    }
  ],
  "recommendations": [
    {
      "recommendation_id": "rec-001",
      "priority": 1,
      "category": "remove",
      "text": "Remove the loose rug between the bed and bedroom door before tonight. If the rug must stay, secure it completely flat with double-sided carpet tape on all edges.",
      "target_location": "Bedroom floor, between bed and door",
      "expected_benefit": "Eliminates the primary trip hazard on the nighttime bathroom route"
    },
    {
      "recommendation_id": "rec-002",
      "priority": 2,
      "category": "move",
      "text": "Move the chair against the wall or into the corner to open at least 90cm of clear walking width on the path to the door. The walker needs unobstructed straight-line passage.",
      "target_location": "Bedroom, currently blocking path near door",
      "expected_benefit": "Restores safe walker clearance on the primary route"
    },
    {
      "recommendation_id": "rec-003",
      "priority": 3,
      "category": "add",
      "text": "Place a plug-in night light or motion-activated light in the hallway between the bedroom and bathroom. The route must be visible without needing to find a switch.",
      "target_location": "Hallway between bedroom and bathroom doors",
      "expected_benefit": "Reduces nighttime misstep risk on the most-used recovery route"
    },
    {
      "recommendation_id": "rec-004",
      "priority": 4,
      "category": "move",
      "text": "Move medications, phone charger, water bottle, and any daily essentials from the high shelf down to the nightstand or a surface within arm's reach of the bed. Nothing essential should require reaching above shoulder height.",
      "target_location": "Move from wall shelf to nightstand beside bed",
      "expected_benefit": "Prevents unsafe reaching and reduces need to stand up for basic items"
    },
    {
      "recommendation_id": "rec-005",
      "priority": 5,
      "category": "professional",
      "text": "Consider adding a bed rail or a stable grab handle beside the bed to assist with sit-to-stand transfers. If the bed is too low, bed risers may help. Discuss with an occupational therapist if possible.",
      "target_location": "Beside bed, on the side the patient gets in/out",
      "expected_benefit": "Safer sit-to-stand transfers, especially in the first few days of recovery"
    }
  ],
  "safe_path": {
    "waypoints": [
      {"x": 2.0, "y": 0.0, "z": 1.0, "label": "bed_exit"},
      {"x": 3.0, "y": 0.0, "z": 2.0, "label": "mid_bedroom"},
      {"x": 4.5, "y": 0.0, "z": 2.0, "label": "bedroom_door"},
      {"x": 1.5, "y": 0.0, "z": 0.0, "label": "hallway_mid"},
      {"x": 0.0, "y": 0.0, "z": 0.0, "label": "bathroom_door"}
    ],
    "width_ok": false,
    "min_width_m": 0.65
  },
  "checklist": {
    "first_night": [
      "Remove the loose rug between the bed and the bathroom-side door",
      "Move the chair against the wall to clear the walker path",
      "Place a night light in the hallway so the bathroom route is visible",
      "Move medications, water, and phone charger to the nightstand",
      "Position the walker within arm's reach of the bed",
      "Make sure the bathroom light switch is easy to find from the doorway",
      "Place a non-slip mat inside the bathroom if the floor is tile",
      "Keep the hallway and bedroom doors fully open, not half-closed"
    ],
    "first_48_hours": [
      "Ask a therapist or nurse about a bed rail or bed risers if sit-to-stand feels unsafe",
      "Install a grab bar near the toilet if there isn't one already",
      "Check that all cords (lamp, charger, extension) are routed against walls, not across the floor",
      "Set up a small caddy or tray on the nightstand with all daily essentials in one place",
      "Practice the bed-to-bathroom route with the patient during daytime first",
      "Confirm the patient can reach the phone/call button from the bed at night"
    ]
  },
  "ghost_rearrangements": [
    {
      "object_id": "obj-003",
      "action": "remove",
      "new_position": {"x": 0.0, "y": 0.0, "z": 0.0},
      "reason": "Remove rug to eliminate trip hazard on primary path"
    },
    {
      "object_id": "obj-004",
      "action": "move",
      "new_position": {"x": 4.2, "y": 0.0, "z": 0.3},
      "reason": "Move chair against far wall to widen walker path to 90cm+"
    }
  ],
  "images": {
    "originals": [],
    "annotated": []
  },
  "disclaimer": "This tool provides environmental suggestions to support recovery at home. It is not medical advice and does not replace guidance from your doctor, occupational therapist, or care team. It may miss hazards. If you have safety concerns, contact your healthcare provider."
}
```

**`fixtures/demo_profiles.json`:**
```json
[
  {
    "profile_id": "walker_after_fall",
    "label": "Walker after fall or fracture",
    "constraints": ["no_bending", "needs_walker_clearance", "fall_risk", "night_bathroom_risk"],
    "min_path_width_m": 0.9,
    "hazard_weights": {
      "floor_obstacle": 5,
      "path_obstruction": 5,
      "transfer_challenge": 4,
      "bathroom_risk": 5,
      "reachability_issue": 3,
      "lighting_issue": 4,
      "wound_care_issue": 2
    }
  }
]
```

### 6. Dev scripts

**`scripts/dev.sh`:**
```bash
#!/usr/bin/env bash
# Start backend and frontend in parallel
trap 'kill 0' EXIT

echo "Starting backend on :8000..."
cd backend && uvicorn main:app --reload --port 8000 &

echo "Starting frontend on :3000..."
cd web-app && npm run dev &

wait
```

**`scripts/test_flow.sh`:**
```bash
#!/usr/bin/env bash
# Quick smoke test of the API flow
API=http://localhost:8000

echo "1. Health check..."
curl -s $API/health | python3 -m json.tool

echo "2. Get profiles..."
curl -s $API/profiles | python3 -m json.tool

echo "3. Create session..."
SESSION=$(curl -s -X POST $API/sessions -H 'Content-Type: application/json' -d '{"recovery_profile":"walker_after_fall"}')
echo $SESSION | python3 -m json.tool
# Extract session_id for further steps...

echo "Done."
```

Make both scripts executable with `chmod +x`.

---

## Definition of Done

- [ ] `git clone` + `cd backend && pip install -r requirements.txt && uvicorn main:app` starts a server that responds to `GET /health`
- [ ] `cd web-app && npm install && npm run dev` starts a Next.js app on localhost:3000
- [ ] `shared/types.ts` and `shared/schemas.py` both define the full Session contract with all nested types
- [ ] `fixtures/demo_session.json` is valid JSON, matches the Session type, and contains 5 hazards + 5 recommendations with realistic content
- [ ] `scripts/dev.sh` starts both backend and frontend
- [ ] `.gitignore` prevents `node_modules/`, `.env`, `__pycache__/`, `.next/` from being committed
