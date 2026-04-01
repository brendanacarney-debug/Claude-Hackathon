# Deployment

## Local quick start

1. Install Python dependencies with `python -m pip install -r backend/requirements.txt`.
2. Install frontend dependencies with `npm install` from [web-app/package.json](/mnt/c/Users/brend/claude%20hacks/Claude-Hackathon/web-app/package.json).
3. Start the backend with `uvicorn backend.main:app --reload`.
4. Start the frontend with `npm run dev` from [web-app](/mnt/c/Users/brend/claude%20hacks/Claude-Hackathon/web-app).

Recommended frontend runtime: Node 22. The app builds on the current workspace too, but some transitive packages now advertise newer engine floors than older Node 20.x installs.

## Docker compose

Run `docker compose up --build` from the repo root.

Why the compose build context is the repo root:
Task 6's frontend and backend both rely on shared fixture data in [fixtures/demo_session.json](/mnt/c/Users/brend/claude%20hacks/Claude-Hackathon/fixtures/demo_session.json) and [fixtures/demo_profiles.json](/mnt/c/Users/brend/claude%20hacks/Claude-Hackathon/fixtures/demo_profiles.json). Building from `backend/` or `web-app/` alone would exclude those files from the image.

## Backend deployment

Deploy the repository with Dockerfile path `backend/Dockerfile`.

Required environment variables for live analysis:
- `ANTHROPIC_API_KEY`
- `HOMERECOVER_DEMO_MODE=false`

Optional environment variables:
- `CORS_ORIGINS`
- `MAX_UPLOAD_MB`
- `HOMERECOVER_RUNTIME_DIR`

If `HOMERECOVER_DEMO_MODE=true`, `POST /sessions/{id}/analyze` returns the fixture-backed demo result and still exercises the same frontend/result contract.

## Frontend deployment

Deploy the repository with Dockerfile path `web-app/Dockerfile`.

Required environment variables:
- `NEXT_PUBLIC_API_URL`
- `NEXT_PUBLIC_DEMO_MODE`

Optional but recommended for containerized deployments:
- `INTERNAL_API_URL`

For fixture-only demo mode:
- `NEXT_PUBLIC_DEMO_MODE=true`

For live backend mode:
- `NEXT_PUBLIC_DEMO_MODE=false`
- `NEXT_PUBLIC_API_URL=<deployed backend url>`
- `INTERNAL_API_URL=<private backend url>` when the frontend server can reach the backend over a private network

## Architecture notes

- The frontend reads fixture data on the server for `/demo` and as a fallback if demo mode is enabled.
- The backend uses a file-backed runtime store in `.runtime/` today, which keeps the API seam stable for later Supabase replacement.
- The safe-path payload now includes `room_id` per waypoint so the Task 6 3D viewer can place cross-room routes without brittle inference.
