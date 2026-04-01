# TASK 6: 3D Room Visualization + Demo Polish

**Priority:** Start after TASK 1 and TASK 5 have the basic frontend scaffold running. This is the "wow" layer.
**Estimated scope:** Three.js room renderer, hazard overlays, safe path, ghost rearrangement, deployment.
**Touches:** `web-app/src/components/RoomViewer3D.tsx` and related 3D components, deployment config.

---

## Why This Task Exists

This is the visual centerpiece of the demo. When judges see a 3D room with red-glowing hazards, a green safe path on the floor, and translucent "ghost" furniture showing where to move things -- that's the moment that makes the project memorable. Without this, we have a text-based hazard list (useful but not impressive). With this, we have a spatial risk visualization that immediately communicates the product's value.

Also handles final deployment config and demo-day resilience.

---

## Deliverables

### 1. Room Viewer 3D (`web-app/src/components/RoomViewer3D.tsx`)

**Props:**
```typescript
interface RoomViewer3DProps {
  session: Session;
  showHazards: boolean;      // toggle hazard overlays
  showSafePath: boolean;     // toggle safe path line
  showRearrangements: boolean; // toggle ghost suggestions
}
```

**Implementation using `@react-three/fiber` and `@react-three/drei`:**

```tsx
import { Canvas } from '@react-three/fiber';
import { OrbitControls, Text, Line } from '@react-three/drei';

export function RoomViewer3D({ session, showHazards, showSafePath, showRearrangements }: RoomViewer3DProps) {
  return (
    <div className="w-full h-[400px] md:h-[500px] rounded-lg overflow-hidden bg-slate-900">
      <Canvas camera={{ position: [5, 6, 5], fov: 50 }}>
        <ambientLight intensity={0.6} />
        <directionalLight position={[5, 10, 5]} intensity={0.8} />
        
        <OrbitControls 
          enablePan={true}
          enableZoom={true}
          maxPolarAngle={Math.PI / 2.1}  // prevent going below floor
        />
        
        {/* Render each room */}
        {session.rooms.map(room => (
          <RoomFloor key={room.room_id} room={room} />
        ))}
        
        {/* Render objects */}
        {session.rooms.flatMap(room => room.objects).map(obj => (
          <RoomObject 
            key={obj.object_id} 
            object={obj}
            hazard={showHazards ? findHazardForObject(obj.object_id, session.hazards) : null}
          />
        ))}
        
        {/* Safe path */}
        {showSafePath && <SafePathLine path={session.safe_path} />}
        
        {/* Ghost rearrangements */}
        {showRearrangements && session.ghost_rearrangements.map(gr => (
          <GhostObject key={gr.object_id} rearrangement={gr} originalObject={findObject(gr.object_id, session)} />
        ))}
      </Canvas>
    </div>
  );
}
```

### 2. Room floor plane (`RoomFloor` component)

Render each room as a flat colored plane on the ground:

```tsx
function RoomFloor({ room }: { room: Room }) {
  // Room dimensions from objects (estimate from object spread)
  // Or use a default: bedroom 5x4m, bathroom 3x2.5m, hallway 3x1.2m
  const ROOM_SIZES = {
    bedroom: [5, 4],
    bathroom: [3, 2.5],
    hallway: [3, 1.2]
  };
  
  const ROOM_COLORS = {
    bedroom: '#E8F0FE',   // light blue
    bathroom: '#E6F4EA',  // light green  
    hallway: '#FEF3E2'    // light warm
  };

  // Offset rooms so they connect (bedroom on left, hallway in middle, bathroom on right)
  const ROOM_OFFSETS = {
    bedroom: [0, 0, 0],
    hallway: [5.5, 0, 1.4],   // offset to connect to bedroom door
    bathroom: [9, 0, 0.7]     // offset to connect to hallway end
  };

  const [width, depth] = ROOM_SIZES[room.room_type] || [4, 3];
  const [ox, oy, oz] = ROOM_OFFSETS[room.room_type] || [0, 0, 0];

  return (
    <group position={[ox, 0, oz]}>
      {/* Floor */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[width/2, -0.01, depth/2]}>
        <planeGeometry args={[width, depth]} />
        <meshStandardMaterial color={ROOM_COLORS[room.room_type]} />
      </mesh>
      
      {/* Room label */}
      <Text
        position={[width/2, 0.01, depth/2]}
        rotation={[-Math.PI/2, 0, 0]}
        fontSize={0.3}
        color="#94A3B8"
      >
        {room.room_type}
      </Text>
      
      {/* Simple walls (thin boxes along edges, semi-transparent) */}
      <WallSegments width={width} depth={depth} doorPositions={getDoors(room)} />
    </group>
  );
}
```

**Walls:** Render as thin semi-transparent boxes along the room perimeter. Leave gaps where doors are detected. Don't stress about perfect wall layout -- the floor color already defines the room area. Walls are just for visual context.

### 3. Room objects (`RoomObject` component)

Render each detected object as a colored box with a label:

```tsx
function RoomObject({ object, hazard }: { object: RoomObject; hazard: Hazard | null }) {
  // Color based on hazard status
  const color = hazard 
    ? hazard.severity === 'urgent' ? '#EF4444'   // red
    : hazard.severity === 'moderate' ? '#F59E0B'  // amber
    : '#10B981'                                   // green
    : '#CBD5E1';                                  // slate-300 (no hazard)
  
  const opacity = hazard ? 0.85 : 0.5;
  
  // Object-specific visual tweaks
  const VISUAL_OVERRIDES: Record<string, any> = {
    rug:    { scaleY: 0.02, color: hazard ? color : '#B45309' },  // very flat
    bed:    { color: hazard ? color : '#93C5FD' },                // blue-ish
    chair:  { color: hazard ? color : '#A78BFA' },                // purple-ish
    table:  { color: hazard ? color : '#FCD34D' },                // yellow
    door:   { color: '#64748B', scaleY: 2.1 },                   // gray, tall
    toilet: { color: hazard ? color : '#E2E8F0' },                // white-ish
    shelf:  { color: hazard ? color : '#D4A574' },                // wood-ish
  };
  
  const override = VISUAL_OVERRIDES[object.category] || {};
  const finalColor = override.color || color;
  
  return (
    <group position={[object.position.x, object.position.y + (object.dimensions.height / 2), object.position.z]}>
      {/* Object mesh */}
      <mesh>
        <boxGeometry args={[
          object.dimensions.width,
          override.scaleY || object.dimensions.height,
          object.dimensions.depth
        ]} />
        <meshStandardMaterial 
          color={finalColor} 
          transparent 
          opacity={opacity}
        />
      </mesh>
      
      {/* Hazard glow effect */}
      {hazard && hazard.severity === 'urgent' && (
        <mesh>
          <boxGeometry args={[
            object.dimensions.width + 0.1,
            (override.scaleY || object.dimensions.height) + 0.1,
            object.dimensions.depth + 0.1
          ]} />
          <meshStandardMaterial 
            color={color} 
            transparent 
            opacity={0.2}
            emissive={color}
            emissiveIntensity={0.5}
          />
        </mesh>
      )}
      
      {/* Label floating above object */}
      <Text
        position={[0, (override.scaleY || object.dimensions.height) / 2 + 0.3, 0]}
        fontSize={0.15}
        color={hazard ? finalColor : '#475569'}
        anchorX="center"
      >
        {object.category}
      </Text>
    </group>
  );
}
```

### 4. Safe path overlay (`SafePathLine` component)

A glowing green line on the floor showing the recommended walking route:

```tsx
import { Line } from '@react-three/drei';

function SafePathLine({ path }: { path: SafePath }) {
  const points = path.waypoints.map(wp => [wp.x, 0.05, wp.z] as [number, number, number]);
  
  return (
    <group>
      {/* Main path line */}
      <Line
        points={points}
        color="#10B981"
        lineWidth={4}
      />
      
      {/* Wider glow underneath */}
      <Line
        points={points}
        color="#10B981"
        lineWidth={12}
        transparent
        opacity={0.2}
      />
      
      {/* Waypoint markers */}
      {path.waypoints.map((wp, i) => (
        <group key={i} position={[wp.x, 0.05, wp.z]}>
          <mesh>
            <sphereGeometry args={[0.08]} />
            <meshStandardMaterial color="#10B981" emissive="#10B981" emissiveIntensity={0.3} />
          </mesh>
          {wp.label && (
            <Text position={[0, 0.25, 0]} fontSize={0.12} color="#10B981">
              {wp.label.replace(/_/g, ' ')}
            </Text>
          )}
        </group>
      ))}
      
      {/* Path width indicator */}
      {!path.width_ok && (
        <Text
          position={[points[Math.floor(points.length/2)][0], 0.5, points[Math.floor(points.length/2)][2]]}
          fontSize={0.15}
          color="#EF4444"
        >
          {`Path: ${(path.min_width_m * 100).toFixed(0)}cm (need 90cm+)`}
        </Text>
      )}
    </group>
  );
}
```

### 5. Ghost rearrangement overlays (`GhostObject` component)

Show where objects should be moved (translucent, with dashed outline feel):

```tsx
function GhostObject({ rearrangement, originalObject }: { rearrangement: GhostRearrangement; originalObject: RoomObject }) {
  if (rearrangement.action === 'remove') {
    // Show a red X or strikethrough on the original object position
    return (
      <group position={[originalObject.position.x, originalObject.dimensions.height + 0.3, originalObject.position.z]}>
        <Text fontSize={0.4} color="#EF4444">
          REMOVE
        </Text>
      </group>
    );
  }
  
  // action === 'move': show ghost at new position
  return (
    <group>
      {/* Ghost at new position (translucent green) */}
      <group position={[
        rearrangement.new_position.x, 
        rearrangement.new_position.y + originalObject.dimensions.height / 2, 
        rearrangement.new_position.z
      ]}>
        <mesh>
          <boxGeometry args={[originalObject.dimensions.width, originalObject.dimensions.height, originalObject.dimensions.depth]} />
          <meshStandardMaterial color="#10B981" transparent opacity={0.3} />
        </mesh>
        <Text position={[0, originalObject.dimensions.height / 2 + 0.2, 0]} fontSize={0.12} color="#10B981">
          move here
        </Text>
      </group>
      
      {/* Arrow from old to new position */}
      <Line
        points={[
          [originalObject.position.x, 0.3, originalObject.position.z],
          [rearrangement.new_position.x, 0.3, rearrangement.new_position.z]
        ]}
        color="#10B981"
        lineWidth={2}
        dashed
        dashSize={0.1}
        gapSize={0.05}
      />
    </group>
  );
}
```

### 6. Toggle controls above the 3D viewer

In the results page, above the Canvas:

```tsx
const [showHazards, setShowHazards] = useState(true);
const [showSafePath, setShowSafePath] = useState(true);
const [showRearrangements, setShowRearrangements] = useState(false);

<div className="flex gap-2 mb-2">
  <ToggleButton active={showHazards} onClick={() => setShowHazards(!showHazards)} color="red">
    Hazards
  </ToggleButton>
  <ToggleButton active={showSafePath} onClick={() => setShowSafePath(!showSafePath)} color="green">
    Safe Path
  </ToggleButton>
  <ToggleButton active={showRearrangements} onClick={() => setShowRearrangements(!showRearrangements)} color="blue">
    Suggested Changes
  </ToggleButton>
</div>

<RoomViewer3D 
  session={session}
  showHazards={showHazards}
  showSafePath={showSafePath}
  showRearrangements={showRearrangements}
/>
```

### 7. Deployment config

**Frontend (Vercel):**
- `web-app/vercel.json` if needed (usually just `vercel --prod` works with Next.js)
- Set env vars in Vercel dashboard: `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_DEMO_MODE`

**Backend (Railway or Render):**

`backend/Dockerfile`:
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

`docker-compose.yml` (repo root, for local dev):
```yaml
version: '3.8'
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    env_file:
      - ./backend/.env
    volumes:
      - ./backend:/app
      - ./shared:/app/shared
      - ./fixtures:/app/fixtures
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload

  frontend:
    build: ./web-app
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000
    volumes:
      - ./web-app:/app
      - /app/node_modules
    command: npm run dev
```

`DEPLOY.md` at repo root:
```markdown
# Deployment

## Quick start (local)
./scripts/dev.sh

## Backend (Railway)
1. Connect GitHub repo
2. Set root directory: backend/
3. Set env vars: ANTHROPIC_API_KEY, SUPABASE_URL, SUPABASE_ANON_KEY
4. Deploy

## Frontend (Vercel)  
1. Connect GitHub repo
2. Set root directory: web-app/
3. Set env vars: NEXT_PUBLIC_API_URL=<railway-url>, NEXT_PUBLIC_DEMO_MODE=false
4. Deploy

## Demo mode
Set NEXT_PUBLIC_DEMO_MODE=true to bypass backend entirely.
The /demo page always uses fixture data regardless of this setting.
```

### 8. Final polish checklist

Before demo day, verify:
- [ ] 3D viewer renders correctly on Chrome, Safari, and Firefox
- [ ] Orbit controls work on both mouse and touch
- [ ] Toggle buttons visibly change the 3D scene
- [ ] Ghost rearrangements are clearly distinguishable from real objects
- [ ] Safe path is visible against all floor colors
- [ ] The scene loads in under 2 seconds (no heavy assets)
- [ ] `/demo` page loads instantly with fixture data
- [ ] Backend is deployed and accessible from the frontend's deployed URL
- [ ] Export/print checklist produces a clean page

---

## Files to create/modify

```
web-app/src/components/
  RoomViewer3D.tsx           # REPLACE placeholder from TASK 5
  RoomFloor.tsx              # Room floor plane
  RoomObjectMesh.tsx         # Individual object renderer
  SafePathLine.tsx           # Safe path overlay
  GhostObject.tsx            # Rearrangement overlay
  ToggleButton.tsx           # 3D view toggle controls

backend/
  Dockerfile

docker-compose.yml           # Repo root
DEPLOY.md                    # Repo root
```

---

## Definition of Done

- [ ] 3D viewer renders all rooms (bedroom, hallway, bathroom) with correct floor planes and room labels
- [ ] All detected objects render as colored boxes at their positions
- [ ] Hazardous objects glow red/amber based on severity when "Hazards" toggle is on
- [ ] Safe path shows as a green line on the floor with waypoint labels when "Safe Path" toggle is on
- [ ] Ghost rearrangements show translucent green boxes at new positions with arrows when "Suggested Changes" toggle is on
- [ ] "REMOVE" label appears over objects flagged for removal
- [ ] Orbit controls allow rotating, zooming, and panning the 3D view
- [ ] The 3D scene renders at 60fps on a modern laptop (no performance issues)
- [ ] Works on both `/results/[id]` and `/demo` pages
- [ ] Backend Dockerfile builds and runs correctly
- [ ] docker-compose starts both services for local development
- [ ] DEPLOY.md has clear, correct deployment instructions
