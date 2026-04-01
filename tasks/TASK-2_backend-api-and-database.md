# TASK 2: Backend API + Database Layer

**Priority:** Start after TASK 1 is done (needs the shared schemas and scaffold).
**Estimated scope:** FastAPI route implementations, Supabase client, session CRUD, file upload handling.
**Touches:** `backend/`

---

## Why This Task Exists

The backend is the spine of the app. Every user action on the frontend (create session, upload photos, trigger analysis, fetch results) goes through these API routes. This task builds the plumbing -- the routes, the database client, the file storage -- so that TASK 3 (AI pipeline) and TASK 4 (rules engine) can plug their logic into a working server.

---

## Deliverables

### 1. Supabase setup

Create these resources in Supabase (document the setup steps so a teammate can replicate):

**Table: `sessions`**
```sql
CREATE TABLE sessions (
  session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at TIMESTAMPTZ DEFAULT now(),
  recovery_profile TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'created',  -- created | uploading | analyzing | analyzed | error
  result_json JSONB,                       -- full analyzed session payload stored here
  error_message TEXT
);
```

**Table: `session_images`**
```sql
CREATE TABLE session_images (
  image_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID REFERENCES sessions(session_id),
  room_type TEXT NOT NULL,           -- bedroom | bathroom | hallway
  storage_path TEXT NOT NULL,        -- path in Supabase Storage bucket
  upload_order INTEGER NOT NULL,     -- 1, 2, 3... preserves capture sequence
  created_at TIMESTAMPTZ DEFAULT now()
);
```

**Storage bucket: `room-scans`**
- Public read (for serving images to frontend), authenticated write
- Max file size: 10MB per image
- Allowed MIME types: image/jpeg, image/png, image/webp

### 2. Database client (`backend/database.py`)

```python
# Must provide these functions:

async def create_session(recovery_profile: str) -> str:
    """Insert a new session row, return session_id."""

async def get_session(session_id: str) -> dict | None:
    """Fetch a session row by ID. Return None if not found."""

async def update_session_status(session_id: str, status: str, error_message: str | None = None):
    """Update the status field (and optionally error_message)."""

async def store_session_result(session_id: str, result_json: dict):
    """Store the full analyzed result JSON and set status to 'analyzed'."""

async def save_image_record(session_id: str, room_type: str, storage_path: str, upload_order: int):
    """Insert a row into session_images."""

async def get_session_images(session_id: str) -> list[dict]:
    """Return all image records for a session, ordered by upload_order."""

async def upload_image_to_storage(session_id: str, filename: str, file_bytes: bytes, content_type: str) -> str:
    """Upload raw image bytes to Supabase Storage bucket 'room-scans'. 
    Store at path: {session_id}/{filename}
    Return the public URL."""
```

Use the `supabase` Python client. Initialize it once in module scope from `config.py` env vars.

### 3. Implement all API routes (`backend/main.py`)

**`GET /health`**
- Return `{"status": "ok", "version": "0.1.0"}`

**`GET /profiles`**
- Return the list of recovery profiles from `backend/rules/profiles.py` (or just hardcode the walker_after_fall profile for now)
- Response: `[{profile_id, label, constraints, min_path_width_m, hazard_weights}]`

**`POST /sessions`**
- Request body: `{"recovery_profile": "walker_after_fall"}`
- Validate that the profile_id is recognized
- Call `create_session()` in database
- Return: `{"session_id": "uuid"}`
- Set status to `created`

**`POST /sessions/{session_id}/upload`**
- Accept `multipart/form-data`:
  - `photos`: list of image files (UploadFile)
  - `room_types`: JSON string array matching photo order, e.g. `["bedroom","bedroom","bathroom","hallway"]`
- For each photo:
  - Read bytes
  - Upload to Supabase Storage via `upload_image_to_storage()`
  - Save metadata via `save_image_record()`
- Update session status to `uploading` then `uploaded` when done
- Return: `{"uploaded": N, "session_id": "uuid"}`
- Error handling:
  - 404 if session not found
  - 400 if no photos provided
  - 400 if room_types length doesn't match photos length
  - 413 if any individual photo > 10MB

**`POST /sessions/{session_id}/analyze`**
- This route kicks off the analysis. For now, implement the skeleton:
  - Set status to `analyzing`
  - Fetch image records for the session
  - Call the analysis pipeline (TASK 3 will implement the actual logic -- for now, return the fixture data)
  - Store results via `store_session_result()`
  - Set status to `analyzed`
- Return: `{"status": "analyzing", "session_id": "uuid"}`
- For the initial implementation, just load `fixtures/demo_session.json` and store it as the result. TASK 3 will replace this with the real pipeline.

**`GET /sessions/{session_id}`**
- Fetch session from database
- If status is `analyzed`, return the `result_json` field (which is the full Session contract)
- If status is anything else, return `{"session_id": "...", "status": "...", "recovery_profile": "..."}`
- 404 if not found

**`GET /sessions/{session_id}/export`**
- Fetch the analyzed session
- Generate a simple HTML page with:
  - Title: "HomeRecover Scan - Recovery Safety Checklist"
  - Date and recovery profile
  - "First Night" checklist as bullet points
  - "First 48 Hours" checklist as bullet points
  - Disclaimer at bottom
- Return as `text/html` content type
- This lets the frontend open it in a new tab and print it

**`POST /sessions/{session_id}/hazards`** (manual hazard marking)
- Request body: `{"class": "floor_obstacle", "severity": "moderate", "explanation": "I noticed a loose cord behind the door"}`
- Fetch current result_json
- Append a new hazard to the hazards array with a generated ID and `related_object_ids: []`
- Save updated result_json
- Return the new hazard object

### 4. Error handling patterns

Every route should:
- Return proper HTTP status codes (200, 201, 400, 404, 500)
- Return JSON error responses: `{"error": "Session not found", "detail": "..."}`
- Log errors to console with enough context to debug
- Never expose stack traces to the client in production

### 5. CORS configuration

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # hackathon - open to all
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Files to create/modify

```
backend/
  main.py         # Full route implementations (expand the stubs from TASK 1)
  database.py     # Supabase client with all CRUD functions
  config.py       # Already exists from TASK 1, may need updates
  models.py       # Request/response models specific to API (CreateSessionRequest, UploadResponse, etc.)
```

---

## Definition of Done

- [ ] `POST /sessions` creates a row in Supabase and returns a session_id
- [ ] `POST /sessions/{id}/upload` with 3 test images stores them in Supabase Storage and records metadata
- [ ] `POST /sessions/{id}/analyze` sets status to analyzed and stores the fixture JSON as result
- [ ] `GET /sessions/{id}` returns the full fixture session when status is analyzed
- [ ] `GET /sessions/{id}/export` returns a printable HTML checklist
- [ ] `GET /profiles` returns the walker_after_fall profile
- [ ] `POST /sessions/{id}/hazards` appends a manual hazard to the result
- [ ] All routes return appropriate error codes for missing sessions, bad input, etc.
- [ ] Can test the full flow with `curl` commands from `scripts/test_flow.sh`
