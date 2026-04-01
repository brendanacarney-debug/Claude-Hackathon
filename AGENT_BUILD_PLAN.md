# HomeRecover Scan -- Agent Build Plan

## Understanding

**What we're building:** A post-discharge home safety tool. A caregiver/patient scans their room (bedroom-to-bathroom route) using their phone camera via a web app. The system detects recovery hazards (rugs, narrow paths, low beds, dark corridors, etc.), renders them visually, and generates a personalized 48-hour safety checklist. Demo persona: older adult returning home after a fall, now using a walker.

**Key pivot from original plan:** The original plan called for a native Swift/Xcode iPhone app using Apple RoomPlan + LiDAR. We are **dropping that entirely** in favor of a full web stack (VSCode + GitHub only). This means:

- No Xcode, no Swift, no RoomPlan, no ARKit
- Room capture = **guided photo upload via mobile web** (the plan's "fallback path" in section 9.2)
- Object/hazard detection = **Claude Vision API** analyzing uploaded room photos server-side
- 3D visualization = **Three.js on the web**, not RealityKit on device
- Everything runs in browser on any phone -- no LiDAR required, no app install needed

**This is still a strong hackathon entry.** The core product value is recovery-specific hazard interpretation, not the scanning tech. Claude Vision analyzing photos and mapping them to a hazard rules engine is arguably more impressive than just piping RoomPlan output through if/else rules. And "works on any phone via browser" is a better accessibility story than "requires a $1000+ LiDAR iPhone."

---

## Revised Architecture

```
[Phone Browser]                [Backend (FastAPI)]              [Database (Supabase)]
     |                               |                               |
     |-- Camera capture (6-10 photos)|                               |
     |-- Upload to API ------------->|-- Store images --------------->|
     |                               |-- Claude Vision: detect        |
     |                               |   objects, layout, hazards     |
     |                               |-- Rules engine: score hazards  |
     |                               |   per recovery profile         |
     |                               |-- Generate recommendations     |
     |                               |-- Claude API: natural-language |
     |                               |   checklist wording            |
     |                               |-- Store results --------------->|
     |<-- Return analyzed session ---|                               |
     |                               |                               |
[Web Dashboard (Next.js)]                                            |
     |-- Fetch session ------------->|------- read from ------------->|
     |-- Render 3D room (Three.js)   |                               |
     |-- Show hazard heatmap         |                               |
     |-- Show safe path overlay      |                               |
     |-- Show checklist + export     |                               |
```

### Tech Stack

| Layer | Tech | Why |
|---|---|---|
| Frontend (mobile + desktop) | Next.js 14 + TypeScript + Tailwind | Single codebase, works on phone browser and laptop, fast to build |
| 3D Visualization | Three.js (via @react-three/fiber) | Web-native 3D, no native code needed, great for room rendering |
| Backend API | FastAPI (Python) | Fast to scaffold, great for AI/ML integration, easy Claude SDK usage |
| AI - Object Detection | Claude Vision API (claude-sonnet-4-6) | Analyze room photos to detect objects, estimate layout, identify hazards |
| AI - Language Generation | Claude API (claude-sonnet-4-6) | Turn structured hazard data into caregiver-friendly checklist copy |
| Database | Supabase (Postgres + Storage) | Hosted DB + file storage for images, sessions, results. Free tier works. |
| Deployment | Vercel (frontend) + Railway/Render (backend) | Fast deploys, stable for demo day |

### Shared Data Contracts (all agents must use these)

**Session JSON** (created by backend, consumed by frontend):
```json
{
  "session_id": "uuid",
  "created_at": "ISO8601",
  "recovery_profile": "walker_after_fall",
  "status": "analyzed",
  "rooms": [
    {
      "room_id": "uuid",
      "room_type": "bedroom|bathroom|hallway",
      "objects": [
        {
          "object_id": "uuid",
          "category": "rug|bed|chair|table|door|toilet|shelf|cord|clutter",
          "position": { "x": 0.0, "y": 0.0, "z": 0.0 },
          "dimensions": { "width": 0.0, "height": 0.0, "depth": 0.0 },
          "on_primary_path": true,
          "confidence": 0.85
        }
      ]
    }
  ],
  "hazards": [
    {
      "hazard_id": "uuid",
      "class": "floor_obstacle|path_obstruction|transfer_challenge|bathroom_risk|reachability_issue|lighting_issue|wound_care_issue",
      "severity": "urgent|moderate|low",
      "explanation": "Loose rug on the path between bed and bathroom door",
      "related_object_ids": ["uuid"],
      "recommendation_ids": ["uuid"]
    }
  ],
  "recommendations": [
    {
      "recommendation_id": "uuid",
      "priority": 1,
      "category": "remove|move|add|adjust|professional",
      "text": "Remove the loose rug between the bed and bathroom door to prevent tripping",
      "target_location": "bedroom floor near bathroom door",
      "expected_benefit": "Eliminates primary trip hazard on nighttime bathroom route"
    }
  ],
  "safe_path": {
    "waypoints": [
      { "x": 0.0, "y": 0.0, "z": 0.0, "label": "bed" },
      { "x": 2.0, "y": 0.0, "z": 1.0, "label": "bathroom_door" }
    ],
    "width_ok": true,
    "min_width_m": 0.9
  },
  "checklist": {
    "first_night": ["Remove rug near bathroom door", "Move walker to bedside", "..."],
    "first_48_hours": ["Install grab bar in bathroom", "Rearrange nightstand for reach", "..."]
  },
  "ghost_rearrangements": [
    {
      "object_id": "uuid",
      "action": "remove|move",
      "new_position": { "x": 0.0, "y": 0.0, "z": 0.0 },
      "reason": "Widen walker path"
    }
  ],
  "images": {
    "originals": ["url1", "url2"],
    "annotated": ["url1"]
  }
}
```

**Recovery Profile Schema:**
```json
{
  "profile_id": "walker_after_fall",
  "label": "Walker after fall/fracture",
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
```

---

## Agent Allocation

### AGENT 1: Backend + AI Engine

**Scope:** FastAPI server, Claude Vision integration, hazard rules engine, recommendation generation, Claude language API, Supabase integration.

**Directory:** `backend/`

**Detailed instructions:**

1. **Scaffold FastAPI project**
   - `backend/main.py` -- FastAPI app with CORS (allow all origins for hackathon)
   - `backend/requirements.txt` -- fastapi, uvicorn, anthropic, supabase, python-multipart, pydantic
   - Use pydantic models matching the shared JSON contracts above

2. **Implement these endpoints** (from plan section 17):

   | Endpoint | Method | What it does |
   |---|---|---|
   | `POST /sessions` | Create session | Accept `recovery_profile` string, return `session_id` |
   | `POST /sessions/{id}/upload` | Upload photos | Accept multipart images (6-10 photos) + room_type labels. Store to Supabase Storage. |
   | `POST /sessions/{id}/analyze` | Run analysis | This is the big one -- see step 3 below |
   | `GET /sessions/{id}` | Get results | Return the full analyzed session JSON |
   | `GET /sessions/{id}/export` | Export checklist | Return a printable HTML or text checklist |
   | `GET /profiles` | List profiles | Return available recovery profiles with their constraints/weights |

3. **The analysis pipeline** (`POST /sessions/{id}/analyze`):
   - Fetch the uploaded images from Supabase Storage
   - Send each image to **Claude Vision** (claude-sonnet-4-6) with a carefully crafted prompt that asks it to:
     - Identify all objects in the room (furniture, rugs, cords, clutter, doors, lighting fixtures)
     - Estimate approximate relative positions (near/far from bed, on floor, on wall, blocking path, etc.)
     - Identify the room type if not already labeled
     - Rate lighting quality (bright/dim/dark)
     - Identify floor surface type (hardwood/carpet/tile)
     - Note any visible trip hazards, narrow passages, or accessibility issues
   - The Claude Vision response should be structured JSON (use tool_use or JSON mode)
   - Feed the structured object list into the **rules engine**

4. **Rules engine** (`backend/rules/engine.py`):
   - Implement the exact hazard rules from plan section 10.1:
     - `walker_after_fall` + rug on path = urgent floor_obstacle
     - `walker_after_fall` + narrow path segment = urgent path_obstruction
     - `no_bending` + essentials stored low = moderate reachability_issue
     - `dizziness` + dim lighting on route = urgent lighting_issue
     - Bathroom without nearby support surface = urgent bathroom_risk
     - Low bed without stable adjacent surface = moderate transfer_challenge
     - Wound care supplies not on clean accessible surface = low wound_care_issue
   - Score each hazard: severity (urgent/moderate/low) based on profile weights
   - Generate recommendations from templates (plan section 10.1 examples)
   - Compute safe path waypoints (from bed/chair to bathroom, avoiding hazards)
   - Generate ghost rearrangement suggestions (move table to widen path, remove rug, etc.)

5. **Checklist generation** (use Claude API):
   - Take the structured hazards + recommendations
   - Send to Claude with a prompt like: "You are a home safety advisor helping a caregiver prepare for a patient returning home after a fall. Convert these hazards and recommendations into a clear, actionable first-night checklist and 48-hour checklist. Use plain language. Do not give medical advice. Include a note that this does not replace professional guidance."
   - Parse the response into `first_night` and `first_48_hours` arrays

6. **Supabase setup:**
   - Table: `sessions` (session_id, created_at, recovery_profile, status, result_json)
   - Storage bucket: `room-scans` for uploaded images
   - Storage bucket: `annotated` for any processed images
   - Provide the Supabase URL and anon key as env vars

7. **Create fixture data:**
   - `backend/fixtures/sample_session.json` -- a complete analyzed session with realistic data for a bedroom-to-bathroom scan of someone with walker_after_fall profile
   - This is critical for frontend development and demo backup
   - Include 5 hazards: loose rug (urgent), narrow doorway approach (urgent), low bed (moderate), dark hallway (urgent), medications on high shelf (moderate)
   - Include 5 recommendations matching those hazards
   - Include realistic room object positions for Three.js rendering

8. **Ethics/safety in API responses:**
   - Every session response must include a `disclaimer` field: "This tool provides environmental suggestions only. It is not medical advice and does not replace guidance from your care team."
   - Never use language that implies diagnosis or medical clearance

**Files to create:**
```
backend/
  main.py              # FastAPI app, routes, CORS
  models.py            # Pydantic models matching shared contracts
  analysis.py          # Claude Vision integration, image analysis pipeline
  rules/
    engine.py          # Hazard scoring rules engine
    profiles.py        # Recovery profile definitions and weights
    recommendations.py # Recommendation templates
  checklist.py         # Claude API checklist generation
  database.py          # Supabase client setup
  config.py            # Env vars, API keys
  requirements.txt
  fixtures/
    sample_session.json
    sample_profile.json
  .env.example         # Template for required env vars
```

---

### AGENT 2: Frontend Web App + 3D Visualization

**Scope:** Next.js app with mobile-first camera capture, Three.js 3D room visualization, hazard display, checklist UI, export. This is both the mobile capture interface AND the desktop demo dashboard.

**Directory:** `web-app/`

**Detailed instructions:**

1. **Scaffold Next.js 14 project** (App Router, TypeScript, Tailwind CSS):
   - `npx create-next-app@latest web-app --typescript --tailwind --eslint --app --src-dir`
   - Install: `three @react-three/fiber @react-three/drei framer-motion`
   - Mobile-first responsive design throughout

2. **Pages/routes to build:**

   | Route | Purpose |
   |---|---|
   | `/` | Landing page -- "Prepare your home for recovery" with start button |
   | `/scan/profile` | Recovery profile selection (walker after fall is default/only for MVP) |
   | `/scan/capture` | Camera capture page -- the main mobile experience |
   | `/scan/[id]/analyzing` | Loading/progress screen while backend processes |
   | `/results/[id]` | Full results page -- 3D view, hazards, checklist (this is the WOW page) |
   | `/results/[id]/checklist` | Printable/exportable checklist view |

3. **Landing page (`/`):**
   - Clean, medical-feeling design (blues, whites, gentle greens -- NOT tech-bro)
   - Headline: "HomeRecover Scan"
   - Subhead: "Prepare your home for a safe recovery"
   - Brief explanation: scan your room, get a safety plan for the first 48 hours
   - Big CTA button: "Start Scan"
   - Small disclaimer footer: "Environmental guidance only. Not medical advice."

4. **Profile selection (`/scan/profile`):**
   - Fetch from `GET /profiles` API
   - For MVP, show the `walker_after_fall` profile prominently
   - Show what constraints it includes (fall risk, needs walker clearance, etc.)
   - Optional: checkboxes for additional constraints (lives alone, dizziness, no bending)
   - "Continue to Scan" button

5. **Camera capture (`/scan/capture`)** -- THIS IS CRITICAL:
   - Use the browser `navigator.mediaDevices.getUserMedia` API for camera access
   - Guide the user through capturing 6-10 photos with prompts:
     1. "Photo 1: Stand at the bed, face the bathroom door"
     2. "Photo 2: The floor between the bed and door"
     3. "Photo 3: The bathroom entrance/threshold"
     4. "Photo 4: Inside the bathroom"
     5. "Photo 5: The bedside area (nightstand, lamp, essentials)"
     6. "Photo 6: Any rugs, cords, or obstacles on the floor"
     7. (Optional) "Photo 7+: Anything else that concerns you"
   - Show a thumbnail strip of captured photos at the bottom
   - Allow retaking individual photos
   - Label each photo with its room_type (bedroom/bathroom/hallway)
   - "Upload & Analyze" button at the end
   - POST images to `/sessions/{id}/upload`, then trigger `/sessions/{id}/analyze`

6. **Analyzing screen (`/scan/[id]/analyzing`):**
   - Animated loading state with progress steps:
     - "Uploading photos..." -> "Detecting room layout..." -> "Identifying hazards..." -> "Generating safety plan..."
   - Poll `GET /sessions/{id}` until status = "analyzed"
   - Auto-redirect to results page

7. **Results page (`/results/[id]`)** -- THE WOW PAGE:
   This is a single scrollable page with multiple sections. On desktop, use a two-column layout (3D left, info right). On mobile, stack vertically.

   **Section A: Room risk summary**
   - Overall risk score badge (High/Medium/Low with color)
   - Count of hazards by severity (e.g., "3 urgent, 2 moderate")
   - Recovery profile shown

   **Section B: 3D Room Visualization (Three.js)**
   - Render a simplified 3D room using `@react-three/fiber`:
     - Floor plane (colored by room type)
     - Simple box geometries for detected furniture (bed = large box, table = small box, etc.)
     - Color-code objects: red = urgent hazard, yellow = moderate, green = safe
     - Draw a glowing line on the floor for the safe path (bed to bathroom)
     - Orbit controls so user can rotate/zoom the view
   - **Toggle buttons above the 3D view:**
     - "Hazards" (default on) -- show red/yellow markers on hazardous objects
     - "Safe Path" -- show/hide the path overlay
     - "Suggested Changes" -- toggle ghost rearrangement (show translucent objects in new positions, strikethrough objects to remove)
   - If Three.js proves too complex for time, fall back to a **2D top-down SVG floor plan** with the same overlays. This is still good.

   **Section C: Hazard list**
   - Cards sorted by severity (urgent first)
   - Each card: hazard icon, severity badge, explanation text, recommendation
   - Example: "URGENT: Loose rug on path to bathroom -- Remove or secure this rug before the first night home"

   **Section D: First-night checklist**
   - Interactive checkbox list from `checklist.first_night`
   - "Before the patient arrives home tonight:"
   - Each item is checkable (state stored in localStorage)

   **Section E: 48-hour checklist**
   - Same format, from `checklist.first_48_hours`
   - "Within the first two days:"

   **Section F: Disclaimer banner**
   - Yellow/amber banner at bottom:
   - "This tool provides environmental suggestions to support recovery at home. It does not replace guidance from your doctor, occupational therapist, or care team. If you have concerns about safety, contact your healthcare provider."

   **Section G: Actions**
   - "Print Checklist" button (opens `/results/[id]/checklist` which is print-optimized)
   - "Share with Caregiver" button (copy link)
   - "Start New Scan" button

8. **Checklist export page (`/results/[id]/checklist`):**
   - Clean, print-optimized layout (use `@media print` CSS)
   - Patient info header (recovery profile, date)
   - First-night and 48-hour checklists as checkbox lists
   - Disclaimer at bottom
   - "Print" button that triggers `window.print()`

9. **Design system:**
   - Colors: Blue-600 primary (#2563EB), Amber-500 for warnings, Red-500 for urgent, Green-500 for safe, neutral grays
   - Font: System font stack (clean, medical-feeling)
   - Cards with subtle shadows, rounded corners
   - Generous spacing -- this is for stressed caregivers, not power users

10. **API integration:**
    - Create `web-app/src/lib/api.ts` with typed fetch wrappers for all backend endpoints
    - Backend URL from `NEXT_PUBLIC_API_URL` env var
    - For development before backend is ready, use the fixture JSON from `backend/fixtures/sample_session.json` as mock data

**Files to create:**
```
web-app/
  src/
    app/
      page.tsx                    # Landing
      scan/
        profile/page.tsx          # Profile selection
        capture/page.tsx          # Camera capture (the phone experience)
        [id]/analyzing/page.tsx   # Loading/progress
      results/
        [id]/page.tsx             # Main results (3D + hazards + checklist)
        [id]/checklist/page.tsx   # Print-friendly checklist
      layout.tsx                  # Root layout with nav, disclaimer
      globals.css                 # Tailwind + custom styles
    components/
      RoomViewer3D.tsx            # Three.js room renderer
      HazardCard.tsx              # Individual hazard display card
      ChecklistPanel.tsx          # Interactive checklist
      CaptureGuide.tsx            # Camera capture step-by-step UI
      ProfileSelector.tsx         # Recovery profile picker
      SafePathOverlay.tsx         # 3D path line component
      GhostRearrangement.tsx      # Translucent moved-object overlay
      RiskBadge.tsx               # Severity badge component
      DisclaimerBanner.tsx        # Ethics/limitation banner
    lib/
      api.ts                      # Backend API client
      types.ts                    # TypeScript types matching shared contracts
      mockData.ts                 # Fixture data for development
    hooks/
      useCamera.ts                # Camera capture hook
      useSession.ts               # Session polling hook
  public/
    icons/                        # Hazard class icons
  .env.example
```

---

### AGENT 3: Integration, Demo Data, Polish, and Mobile Web Capture Fallback

**Scope:** Wire everything together end-to-end, create realistic demo data, handle deployment config, build the photo-to-room-model bridge, and ensure the demo runs flawlessly. Also owns the "manual hazard marking" feature and share/export flows.

**Directory:** Works across all directories -- `backend/`, `web-app/`, and root-level config.

**Detailed instructions:**

1. **Create the shared type definitions and contracts:**
   - `shared/types.ts` -- TypeScript types (copy of the JSON contracts above)
   - `shared/schemas.py` -- Python pydantic models (same contracts)
   - These are the single source of truth that Agent 1 and Agent 2 build against

2. **Build the photo-to-spatial-model bridge** (`backend/spatial/`):
   - This is the critical piece that turns Claude Vision's object detection output into positioned 3D objects for Three.js
   - `backend/spatial/room_builder.py`:
     - Take Claude Vision's object list (with relative positions like "rug is between bed and door", "nightstand is beside bed on left")
     - Convert into absolute x/y/z coordinates in a normalized room space (e.g., 5m x 4m room)
     - Use simple heuristics: bed goes against a wall, bathroom door on opposite wall, objects placed relative to landmarks
     - Output the `rooms[].objects[]` array with positions and dimensions
   - `backend/spatial/path_finder.py`:
     - Given object positions, compute the safe path from bed to bathroom door
     - Simple: straight line, then dodge around obstacles
     - Output `safe_path.waypoints` array
   - This doesn't need to be perfect -- reasonable approximate positions from photo context are fine for a hackathon

3. **Create comprehensive demo fixtures:**
   - `fixtures/demo_bedroom_bathroom/` directory:
     - 6-8 actual photos of a bedroom and bathroom (take these yourself or use royalty-free stock)
     - `raw_vision_output.json` -- what Claude Vision would return for these photos
     - `analyzed_session.json` -- complete session with all hazards, recommendations, paths, checklists
     - This lets the frontend demo work even if the backend is down
   - `fixtures/demo_session_preloaded.json` -- a session that's already "analyzed" and can be loaded directly into the results page
   - The demo fixture should contain exactly these hazards:
     1. **Loose area rug** between bed and bathroom door (urgent, floor_obstacle)
     2. **Narrow passage** where a chair blocks the walker path (urgent, path_obstruction)
     3. **Low bed** without a stable surface nearby for sit-to-stand (moderate, transfer_challenge)
     4. **Dark hallway** to bathroom with no night light (urgent, lighting_issue)
     5. **Medications on high shelf** requiring reaching above head (moderate, reachability_issue)
   - And these recommendations:
     1. Remove the rug before tonight (priority 1)
     2. Move the chair against the wall to widen the path to 90cm+ (priority 2)
     3. Place a night light along the hallway to bathroom (priority 3)
     4. Move medications to the nightstand within arm's reach (priority 4)
     5. Add a stable chair or grab-rail near the bed for sit-to-stand support (priority 5, professional)

4. **End-to-end integration testing:**
   - Write a script `scripts/test_flow.sh` that:
     - Starts the backend locally
     - Creates a session via API
     - Uploads sample photos
     - Triggers analysis
     - Fetches results
     - Verifies the response matches expected schema
   - Write `scripts/dev.sh` that starts both backend and frontend in parallel

5. **Deployment configuration:**
   - `docker-compose.yml` at repo root for local development (backend + frontend)
   - `backend/Dockerfile` for backend deployment
   - `web-app/.env.production` template pointing to deployed backend URL
   - `vercel.json` if needed for frontend deployment
   - `railway.toml` or `render.yaml` for backend deployment
   - Document deployment steps in `DEPLOY.md`

6. **Demo-day resilience:**
   - Add a `/demo` route to the frontend that loads the preloaded fixture session directly (no API call needed)
   - This is the backup path if backend/network fails during judging
   - The `/demo` page should look identical to `/results/[id]` but pulls from local fixture JSON
   - Add an environment variable `NEXT_PUBLIC_DEMO_MODE=true` that makes the app use fixtures everywhere

7. **Manual hazard marking** (from plan section 19):
   - Add a "Mark a hazard" button on the results page
   - Simple modal: click on a photo or area, type a description, select hazard class
   - POST to `POST /sessions/{id}/hazards` to add a manual hazard
   - This shows judges that the app doesn't pretend to catch everything

8. **Share/export features:**
   - "Copy link" button that copies the `/results/[id]` URL
   - PDF export: use the browser print dialog on the checklist page (simple, reliable)
   - Optional: generate a shareable image/card summarizing the top 3 hazards

9. **Root-level repo setup:**
   - `.gitignore` covering Python, Node, env files
   - Root `README.md` with project overview, setup instructions, architecture diagram
   - `CLAUDE.md` with project conventions for future Claude Code sessions

**Files to create:**
```
shared/
  types.ts
  schemas.py
backend/
  spatial/
    room_builder.py
    path_finder.py
fixtures/
  demo_bedroom_bathroom/
    photo_1_bed_to_door.jpg     (placeholder or real)
    photo_2_floor_path.jpg
    ...
    raw_vision_output.json
    analyzed_session.json
  demo_session_preloaded.json
scripts/
  test_flow.sh
  dev.sh
docker-compose.yml
DEPLOY.md
CLAUDE.md
.gitignore
README.md (updated)
```

---

## Dependency Graph Between Agents

```
Agent 1 (Backend)        Agent 2 (Frontend)        Agent 3 (Integration)
     |                        |                          |
     |  <-- shared contracts from Agent 3 -->            |
     |                        |                          |
     v                        v                          v
  Build API routes      Build UI pages          Create shared types
  Build Vision pipeline Build 3D renderer       Create fixture data
  Build rules engine    Build camera capture    Build spatial bridge
  Build checklist gen   Build checklist UI      Wire end-to-end
     |                        |                  Deploy config
     |                        |                  Demo resilience
     +------- integrate and test together -------+
```

**Agents 1 and 2 can work fully in parallel** because Agent 3 provides the shared contracts and fixture data up front. Agent 3 starts with contracts/fixtures (enabling the others), then moves to integration work once 1 and 2 have initial code.

---

## Build Order

### Phase 1: Scaffold (all agents, parallel)
- Agent 3: Create shared types, fixture data, repo setup, .gitignore, scripts
- Agent 1: Scaffold FastAPI, implement `/profiles` and `/sessions` CRUD
- Agent 2: Scaffold Next.js, build landing page, profile selection, camera capture UI

### Phase 2: Core features (all agents, parallel)
- Agent 1: Implement Claude Vision pipeline, rules engine, recommendation generation
- Agent 2: Build 3D room viewer, hazard cards, checklist panels (using fixture data)
- Agent 3: Build spatial room_builder and path_finder, integration scripts

### Phase 3: Integration (sequential)
- Agent 3: Wire frontend to real backend, test full flow end-to-end
- Agent 1: Fix any API issues found during integration
- Agent 2: Fix any UI issues found during integration

### Phase 4: Polish (all agents, parallel)
- Agent 1: Tune Claude Vision prompts for accuracy, add export endpoint
- Agent 2: Ghost rearrangement toggle, print stylesheet, responsive polish
- Agent 3: Demo mode, deployment, manual hazard marking, share features

---

## What We Dropped vs. Original Plan

| Original Plan Feature | Status | Why |
|---|---|---|
| Native Swift/Xcode iOS app | DROPPED | User requirement: VSCode/GitHub only |
| RoomPlan / ARKit / LiDAR scanning | DROPPED | Requires Xcode + native iOS |
| RealityKit on-device visualization | REPLACED | Three.js on web instead |
| Guided photo capture (fallback) | PROMOTED to primary | Now the main capture method |
| Backend hazard rules engine | KEPT | Unchanged |
| Claude API for checklist language | KEPT | Unchanged |
| Web dashboard | PROMOTED | Now the entire frontend, not just a secondary view |
| 3D visualization | KEPT | Three.js instead of RealityKit |
| Supabase storage | KEPT | Unchanged |
| Ethical disclaimers | KEPT | Unchanged |
| TestFlight distribution | DROPPED | Not needed -- it's a web app, just share the URL |

**Net effect:** Simpler deployment story (URL, not app install), broader device support (any phone), faster to build (no Swift learning curve), same core product value.
