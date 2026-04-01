import { Text } from "@react-three/drei";

import type { Room } from "@/lib/types";

const ROOM_COLORS: Record<string, string> = {
  bedroom: "#e7eefc",
  hallway: "#f7edd9",
  bathroom: "#e4f5ea",
};

function WallSegments({
  width,
  depth,
}: {
  width: number;
  depth: number;
}) {
  return (
    <group>
      <mesh position={[width / 2, 0.55, 0]}>
        <boxGeometry args={[width, 1.1, 0.06]} />
        <meshStandardMaterial color="#cbd5e1" transparent opacity={0.3} />
      </mesh>
      <mesh position={[width / 2, 0.55, depth]}>
        <boxGeometry args={[width, 1.1, 0.06]} />
        <meshStandardMaterial color="#cbd5e1" transparent opacity={0.3} />
      </mesh>
      <mesh position={[0, 0.55, depth / 2]}>
        <boxGeometry args={[0.06, 1.1, depth]} />
        <meshStandardMaterial color="#cbd5e1" transparent opacity={0.3} />
      </mesh>
      <mesh position={[width, 0.55, depth / 2]}>
        <boxGeometry args={[0.06, 1.1, depth]} />
        <meshStandardMaterial color="#cbd5e1" transparent opacity={0.3} />
      </mesh>
    </group>
  );
}

export function RoomFloor({
  room,
  width,
  depth,
  offset,
}: {
  room: Room;
  width: number;
  depth: number;
  offset: [number, number, number];
}) {
  const floorColor = ROOM_COLORS[room.room_type] ?? "#edf2f7";

  return (
    <group position={offset}>
      <mesh
        rotation={[-Math.PI / 2, 0, 0]}
        position={[width / 2, -0.02, depth / 2]}
        receiveShadow
      >
        <planeGeometry args={[width, depth]} />
        <meshStandardMaterial color={floorColor} />
      </mesh>

      <Text
        position={[width / 2, 0.03, depth / 2]}
        rotation={[-Math.PI / 2, 0, 0]}
        fontSize={0.28}
        color="#64748b"
        anchorX="center"
      >
        {room.room_type}
      </Text>

      <WallSegments width={width} depth={depth} />
    </group>
  );
}
