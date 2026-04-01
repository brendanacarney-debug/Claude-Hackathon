"use client";

import { OrbitControls } from "@react-three/drei";
import { Canvas } from "@react-three/fiber";

import { GhostObject } from "@/components/GhostObject";
import { RoomFloor } from "@/components/RoomFloor";
import { RoomObjectMesh } from "@/components/RoomObjectMesh";
import { SafePathLine } from "@/components/SafePathLine";
import {
  buildRoomSceneLayout,
  findObjectById,
  findRoomForObject,
  ghostWorldPosition,
  safePathPointsWithRooms,
  toWorldPosition,
} from "@/lib/scene";
import type { Hazard, Session } from "@/lib/types";

export function RoomViewer3D({
  session,
  showHazards,
  showSafePath,
  showRearrangements,
}: {
  session: Session;
  showHazards: boolean;
  showSafePath: boolean;
  showRearrangements: boolean;
}) {
  const roomLayout = buildRoomSceneLayout(session);
  const objectHazards = new Map<string, Hazard>();

  if (showHazards) {
    for (const hazard of session.hazards) {
      for (const objectId of hazard.related_object_ids) {
        const existing = objectHazards.get(objectId);
        if (
          !existing ||
          (existing.severity === "moderate" && hazard.severity === "urgent") ||
          (existing.severity === "low" && hazard.severity !== "low")
        ) {
          objectHazards.set(objectId, hazard);
        }
      }
    }
  }

  const pathPoints = safePathPointsWithRooms(session, roomLayout).map(
    ({ point, waypoint }) => ({
      point,
      label: waypoint.label,
    }),
  );

  return (
    <div className="h-[440px] overflow-hidden rounded-[1.8rem] border border-[var(--app-line)] bg-[linear-gradient(180deg,#edf3fb_0%,#dce7f4_100%)]">
      <Canvas camera={{ position: [9.5, 7.2, 10.5], fov: 42 }} shadows>
        <color attach="background" args={["#edf3fb"]} />
        <ambientLight intensity={0.75} />
        <directionalLight castShadow position={[10, 14, 8]} intensity={1.2} />
        <hemisphereLight args={["#ffffff", "#dbeafe", 0.55]} />
        <gridHelper args={[36, 36, "#cbd5e1", "#dbe4f0"]} position={[9, 0, 4]} />

        <OrbitControls
          enablePan
          enableZoom
          minDistance={4}
          maxDistance={28}
          maxPolarAngle={Math.PI / 2.08}
        />

        {Object.values(roomLayout).map(({ room, width, depth, offset }) => (
          <RoomFloor
            key={room.room_id}
            room={room}
            width={width}
            depth={depth}
            offset={offset}
          />
        ))}

        {session.rooms.flatMap((room) =>
          room.objects.map((object) => (
            <RoomObjectMesh
              key={object.object_id}
              object={object}
              worldPosition={toWorldPosition(object.position, room.room_id, roomLayout)}
              hazard={objectHazards.get(object.object_id)}
            />
          )),
        )}

        {showSafePath ? (
          <SafePathLine safePath={session.safe_path} points={pathPoints} />
        ) : null}

        {showRearrangements
          ? session.ghost_rearrangements.map((rearrangement) => {
              const originalObject = findObjectById(session, rearrangement.object_id);
              const room = findRoomForObject(session, rearrangement.object_id);
              if (!originalObject || !room) {
                return null;
              }

              const origin = toWorldPosition(
                originalObject.position,
                room.room_id,
                roomLayout,
              );
              const destination = ghostWorldPosition(
                rearrangement,
                room.room_id,
                roomLayout,
              );

              return (
                <GhostObject
                  key={`${rearrangement.object_id}-${rearrangement.action}`}
                  rearrangement={rearrangement}
                  originalObject={originalObject}
                  origin={origin}
                  destination={destination}
                />
              );
            })
          : null}
      </Canvas>
    </div>
  );
}
