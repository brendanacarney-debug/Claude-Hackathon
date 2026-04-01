# TASK 5: Frontend UI + Camera Capture

**Priority:** Start after TASK 1 scaffold exists. Can run in parallel with backend tasks.
**Estimated scope:** All Next.js pages, camera capture flow, hazard display, checklist UI.
**Touches:** `web-app/src/`

---

## Why This Task Exists

This is everything the user sees and touches. The caregiver opens the app on their phone, selects a recovery profile, takes guided photos of their home, waits for analysis, and then sees the results with hazards and a checklist. It also needs to look great on a projector for demo day. Every page must work mobile-first but also display well on desktop.

---

## Deliverables

### 1. Root layout (`web-app/src/app/layout.tsx`)

```tsx
// Minimal shell:
// - <html> with system font stack
// - Small top bar with "HomeRecover Scan" text logo (no image needed)
// - Main content area
// - No heavy nav -- this is a linear flow app, not a multi-tab dashboard
```

Design tokens to set up in `globals.css` or as Tailwind config:
- Primary: `#2563EB` (blue-600)
- Urgent: `#EF4444` (red-500)
- Warning: `#F59E0B` (amber-500)
- Safe: `#10B981` (green-500)
- Background: `#F8FAFC` (slate-50)
- Card background: `#FFFFFF`
- Text: `#1E293B` (slate-800)
- Muted text: `#64748B` (slate-500)

### 2. Landing page (`/`) -- `web-app/src/app/page.tsx`

A clean, trust-building page. Think "medical app" not "tech startup."

**Layout (mobile):**
```
[Top padding]

[Icon or simple illustration -- could be just a large shield/heart/home icon via unicode or SVG]

HomeRecover Scan
Prepare your home for a safe recovery

Scan your room with your phone camera.
Get a personalized safety plan for the 
first 48 hours after coming home.

[   Start Scan   ]  <-- large blue button, full width on mobile

Designed for caregivers and patients
preparing for post-discharge recovery.

---
Environmental guidance only. 
Not medical advice.
```

**Implementation details:**
- The "Start Scan" button links to `/scan/profile`
- Use `framer-motion` for a subtle fade-in on load (nothing flashy)
- Disclaimer text in small muted gray at bottom

### 3. Profile selection (`/scan/profile`) -- `web-app/src/app/scan/profile/page.tsx`

**Layout:**
```
Choose Recovery Profile

[CARD - selected state]
  Walker after fall or fracture
  "For patients using a walker after a fall, 
   hip fracture, or similar mobility event"
  
  Constraints considered:
  * Fall risk
  * Walker clearance (90cm+ paths)
  * No bending
  * Nighttime bathroom safety
[/CARD]

[Optional additional constraints]
  [ ] Patient lives alone
  [ ] Dizziness / balance issues  
  [ ] Wound care needed
  
[  Continue to Scan  ]
```

**Implementation details:**
- Fetch profiles from `GET /profiles` (or use mock data in demo mode)
- For MVP, only show the `walker_after_fall` profile, pre-selected
- Store selected profile in React state (or URL params)
- On "Continue", call `POST /sessions` to create a session, then navigate to `/scan/capture?session={id}`
- The optional checkboxes are stretch -- just the profile card and continue button are enough for MVP

### 4. Camera capture (`/scan/capture`) -- `web-app/src/app/scan/capture/page.tsx`

**THIS IS THE MOST CRITICAL FRONTEND PAGE.** This is the "scan" experience that replaces LiDAR.

**State machine:**
```
READY -> CAPTURING (camera active) -> REVIEWING (photo taken) -> NEXT_PROMPT -> ... -> ALL_DONE
```

**Capture prompts** (guide the user through 6 required + optional bonus photos):

```typescript
const CAPTURE_STEPS = [
  {
    id: 1,
    prompt: "Stand at the bed and face the door",
    detail: "Show the walking path from bed to the door",
    room_type: "bedroom",
    required: true
  },
  {
    id: 2,
    prompt: "Look down at the floor path",
    detail: "Capture any rugs, cords, or obstacles between bed and door",
    room_type: "bedroom",
    required: true
  },
  {
    id: 3,
    prompt: "The bedroom doorway or hallway",
    detail: "Show the threshold and the hallway toward the bathroom",
    room_type: "hallway",
    required: true
  },
  {
    id: 4,
    prompt: "The bathroom entrance",
    detail: "Show the bathroom door, threshold, and what's visible inside",
    room_type: "bathroom",
    required: true
  },
  {
    id: 5,
    prompt: "Inside the bathroom",
    detail: "Show the toilet, tub/shower, and any grab bars or supports",
    room_type: "bathroom",
    required: true
  },
  {
    id: 6,
    prompt: "The bedside area",
    detail: "Show the nightstand, lamp, and anything within reach of the bed",
    room_type: "bedroom",
    required: true
  },
  {
    id: 7,
    prompt: "Anything else that concerns you",
    detail: "Optional: rugs, dark corners, high shelves, cluttered areas",
    room_type: "bedroom",
    required: false
  }
];
```

**Camera UI layout (mobile, portrait):**
```
[Step 3 of 6]
[Progress bar ████████░░░░░░]

"The bedroom doorway or hallway"
Show the threshold and the hallway
toward the bathroom

[=========================]
[                         ]
[    CAMERA VIEWFINDER    ]  <-- live video feed, full width
[                         ]
[=========================]

[  Retake  ]    [ Capture ]    [ Skip ]
                  (big)        (if not required)

[Thumbnail strip of captured photos]
[ img1 ][ img2 ][ img3 ]
```

**Camera implementation** (`web-app/src/hooks/useCamera.ts`):

```typescript
export function useCamera() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [isReady, setIsReady] = useState(false);

  const startCamera = async () => {
    const mediaStream = await navigator.mediaDevices.getUserMedia({
      video: { 
        facingMode: "environment",  // rear camera on phone
        width: { ideal: 1920 },
        height: { ideal: 1080 }
      }
    });
    if (videoRef.current) {
      videoRef.current.srcObject = mediaStream;
    }
    setStream(mediaStream);
    setIsReady(true);
  };

  const capturePhoto = (): Blob | null => {
    if (!videoRef.current) return null;
    const canvas = document.createElement("canvas");
    canvas.width = videoRef.current.videoWidth;
    canvas.height = videoRef.current.videoHeight;
    canvas.getContext("2d")?.drawImage(videoRef.current, 0, 0);
    // Convert to blob
    return new Promise(resolve => canvas.toBlob(resolve, "image/jpeg", 0.85));
  };

  const stopCamera = () => {
    stream?.getTracks().forEach(t => t.stop());
    setStream(null);
    setIsReady(false);
  };

  return { videoRef, startCamera, capturePhoto, stopCamera, isReady };
}
```

**On completion (all 6 photos captured):**
- Show a review screen: thumbnail grid of all photos, each labeled with room_type
- "Upload & Analyze" button
- On tap: POST to `/sessions/{id}/upload` with all photos as multipart form data
- Then POST to `/sessions/{id}/analyze`
- Navigate to `/scan/[id]/analyzing`

**Error handling:**
- Camera permission denied: show a clear message with instructions to enable in browser settings, plus a manual file upload fallback (`<input type="file" accept="image/*" capture="environment">`)
- Upload failure: retry button, don't lose the captured photos

### 5. Analyzing screen (`/scan/[id]/analyzing`) -- `web-app/src/app/scan/[id]/analyzing/page.tsx`

**Layout:**
```
[Pulsing animation or spinner]

Analyzing your home...

[Step indicators, animate through:]
  ✓ Photos uploaded
  ● Detecting room layout...
  ○ Identifying hazards
  ○ Generating safety plan

This usually takes 15-30 seconds.
```

**Implementation:**
- Poll `GET /sessions/{id}` every 2 seconds
- When `status === "analyzed"`, redirect to `/results/{id}`
- If `status === "error"`, show error message with retry option
- Timeout after 120 seconds and show "Taking longer than expected, please wait or try again"

### 6. Results page (`/results/[id]`) -- `web-app/src/app/results/[id]/page.tsx`

**This is the WOW page for demo day.** Sections in order:

**Section A: Risk summary header**
```
[Red/Yellow/Green circle badge]
  HIGH RISK
  3 urgent hazards found

Profile: Walker after fall
Scanned: Bedroom → Hallway → Bathroom
```

Component: `RiskBadge.tsx`
- Count hazards by severity
- If any urgent: show "HIGH RISK" in red
- If moderate only: show "MODERATE RISK" in amber
- If only low: show "LOW RISK" in green

**Section B: 3D Room Viewer**

This is TASK 6 -- for now, render a placeholder:
```
[Gray box with text "3D Room View"]
[Toggle buttons: Hazards | Safe Path | Suggested Changes]
```

The 3D component will be dropped in by TASK 6. Just leave a `<RoomViewer3D session={session} />` component call with a placeholder implementation.

**Section C: Hazard cards**

Component: `HazardCard.tsx`

```tsx
// Props: hazard, matchingRecommendation
<div className="border-l-4 border-red-500 bg-white p-4 rounded shadow-sm">
  <div className="flex items-center gap-2 mb-2">
    <span className="bg-red-100 text-red-700 text-xs font-bold px-2 py-0.5 rounded">URGENT</span>
    <span className="text-sm text-slate-500">Floor Obstacle</span>
  </div>
  <p className="text-slate-800 mb-3">
    Loose area rug on the direct path between bed and bathroom door. 
    High trip risk when using a walker, especially at night.
  </p>
  <div className="bg-blue-50 p-3 rounded">
    <p className="text-sm font-medium text-blue-800">Recommendation:</p>
    <p className="text-sm text-blue-700">
      Remove the loose rug between the bed and bedroom door before tonight.
    </p>
  </div>
</div>
```

- Border color: red for urgent, amber for moderate, green for low
- Sort by severity, then by priority
- Map each hazard to its matching recommendation via `recommendation_ids`

**Section D: Checklists**

Component: `ChecklistPanel.tsx`

```tsx
// Props: title, items, storageKey
// Each item is a checkbox + text
// Check state stored in localStorage so it persists across page reloads

<div>
  <h3>Before tonight</h3>
  {items.map((item, i) => (
    <label key={i} className="flex items-start gap-3 py-2">
      <input type="checkbox" checked={checked[i]} onChange={...} className="mt-1" />
      <span className={checked[i] ? "line-through text-slate-400" : "text-slate-800"}>
        {item}
      </span>
    </label>
  ))}
</div>
```

Show first_night and first_48_hours as two separate panels.

**Section E: Disclaimer banner**

Component: `DisclaimerBanner.tsx`

Amber/yellow background, always visible at bottom of results:
```
⚠ This tool provides environmental suggestions to support recovery at home. 
It does not replace guidance from your doctor, occupational therapist, or 
care team. It may miss hazards. If you have safety concerns, contact your 
healthcare provider.
```

**Section F: Action buttons**
```
[ Print Checklist ]  [ Share Link ]  [ New Scan ]
```

- Print: opens `/results/[id]/checklist` in new tab
- Share: copies current URL to clipboard, shows "Link copied!" toast
- New Scan: navigates to `/`

### 7. Printable checklist (`/results/[id]/checklist`) -- `web-app/src/app/results/[id]/checklist/page.tsx`

Clean print-optimized page:
```
HomeRecover Scan
Recovery Safety Checklist
Date: April 1, 2026
Profile: Walker after fall or fracture

BEFORE TONIGHT:
□ Remove the loose rug between the bed and the bathroom-side door
□ Move the chair against the wall to clear the walker path
□ ...

WITHIN THE FIRST 48 HOURS:
□ Ask a therapist about a bed rail or bed risers
□ ...

---
This checklist was generated by HomeRecover Scan. It provides environmental 
suggestions only and does not replace professional medical guidance.
```

Use `@media print` CSS to hide the header bar and any interactive elements. Add a "Print this page" button that calls `window.print()`.

### 8. Demo page (`/demo`) -- `web-app/src/app/demo/page.tsx`

**Critical for demo day.** This page loads the fixture session directly from `fixtures/demo_session.json` (imported as a static JSON file) and renders the results page WITHOUT hitting the backend. 

```tsx
import demoSession from '../../../../fixtures/demo_session.json';

export default function DemoPage() {
  return <ResultsView session={demoSession} />;
}
```

Extract the results page rendering logic into a shared `ResultsView` component so both `/results/[id]` and `/demo` can use it.

### 9. API client (`web-app/src/lib/api.ts`)

Typed fetch wrappers. Check `NEXT_PUBLIC_DEMO_MODE` -- if true, return mock data instead of hitting the backend.

```typescript
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const DEMO_MODE = process.env.NEXT_PUBLIC_DEMO_MODE === 'true';

export async function createSession(profileId: string): Promise<{ session_id: string }> {
  if (DEMO_MODE) return { session_id: "demo-session-001" };
  const res = await fetch(`${API_URL}/sessions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ recovery_profile: profileId })
  });
  return res.json();
}

export async function uploadPhotos(sessionId: string, photos: File[], roomTypes: string[]): Promise<void> {
  if (DEMO_MODE) return;
  const form = new FormData();
  photos.forEach(p => form.append('photos', p));
  form.append('room_types', JSON.stringify(roomTypes));
  await fetch(`${API_URL}/sessions/${sessionId}/upload`, {
    method: 'POST',
    body: form
  });
}

export async function analyzeSession(sessionId: string): Promise<void> {
  if (DEMO_MODE) return;
  await fetch(`${API_URL}/sessions/${sessionId}/analyze`, { method: 'POST' });
}

export async function getSession(sessionId: string): Promise<Session> {
  if (DEMO_MODE) return demoSession as Session;
  const res = await fetch(`${API_URL}/sessions/${sessionId}`);
  return res.json();
}

export async function getProfiles(): Promise<RecoveryProfile[]> {
  if (DEMO_MODE) return demoProfiles;
  const res = await fetch(`${API_URL}/profiles`);
  return res.json();
}
```

---

## Files to create

```
web-app/src/
  app/
    page.tsx                          # Landing
    layout.tsx                        # Root layout
    globals.css                       # Tailwind customization
    scan/
      profile/page.tsx                # Profile selection
      capture/page.tsx                # Camera capture flow
      [id]/analyzing/page.tsx         # Analysis loading screen
    results/
      [id]/page.tsx                   # Main results (uses ResultsView)
      [id]/checklist/page.tsx         # Print-friendly checklist
    demo/page.tsx                     # Demo-day backup page
  components/
    ResultsView.tsx                   # Shared results rendering (used by /results and /demo)
    HazardCard.tsx                    # Hazard display card
    ChecklistPanel.tsx                # Interactive checklist with localStorage
    RiskBadge.tsx                     # Risk level badge
    DisclaimerBanner.tsx              # Ethical disclaimer
    CaptureGuide.tsx                  # Photo capture step UI
    RoomViewer3D.tsx                  # PLACEHOLDER -- TASK 6 builds the real one
    ProfileSelector.tsx               # Profile card picker
  hooks/
    useCamera.ts                      # Camera access hook
    useSession.ts                     # Session polling hook
  lib/
    api.ts                            # Backend API client
    types.ts                          # TypeScript types (from shared/)
    mockData.ts                       # Fixture data for demo mode
```

---

## Definition of Done

- [ ] Landing page renders, "Start Scan" navigates to profile selection
- [ ] Profile selection shows walker_after_fall card, "Continue" creates a session and navigates to capture
- [ ] Camera capture shows live viewfinder on mobile, steps through 6 guided prompts, captures photos as blobs
- [ ] Captured photos can be reviewed with thumbnails, individual retake works
- [ ] Upload sends photos to backend as multipart form, navigates to analyzing screen
- [ ] Analyzing screen polls the API and redirects to results when done
- [ ] Results page shows risk badge, hazard cards sorted by severity, both checklists with working checkboxes, disclaimer
- [ ] Checklist page is print-friendly (`window.print()` produces clean output)
- [ ] `/demo` loads fixture data and renders full results without any API calls
- [ ] Entire flow works on mobile Safari and mobile Chrome (test with phone)
- [ ] All pages look good at 375px width (iPhone SE) and 1440px width (laptop)
