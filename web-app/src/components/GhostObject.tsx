import { Line, Text } from "@react-three/drei";

import type { GhostRearrangement, RoomObject } from "@/lib/types";

export function GhostObject({
  rearrangement,
  originalObject,
  origin,
  destination,
}: {
  rearrangement: GhostRearrangement;
  originalObject: RoomObject;
  origin: [number, number, number];
  destination: [number, number, number];
}) {
  if (rearrangement.action === "remove") {
    return (
      <group
        position={[
          origin[0] + originalObject.dimensions.width / 2,
          originalObject.dimensions.height + 0.4,
          origin[2] + originalObject.dimensions.depth / 2,
        ]}
      >
        <Text fontSize={0.32} color="#ef4444" anchorX="center">
          REMOVE
        </Text>
      </group>
    );
  }

  return (
    <group>
      <group
        position={[
          destination[0] + originalObject.dimensions.width / 2,
          destination[1] + originalObject.dimensions.height / 2,
          destination[2] + originalObject.dimensions.depth / 2,
        ]}
      >
        <mesh>
          <boxGeometry
            args={[
              originalObject.dimensions.width,
              originalObject.dimensions.height,
              originalObject.dimensions.depth,
            ]}
          />
          <meshStandardMaterial color="#10b981" transparent opacity={0.28} />
        </mesh>
        <Text
          position={[0, originalObject.dimensions.height / 2 + 0.18, 0]}
          fontSize={0.12}
          color="#10b981"
          anchorX="center"
        >
          move here
        </Text>
      </group>

      <Line
        points={[
          [
            origin[0] + originalObject.dimensions.width / 2,
            0.3,
            origin[2] + originalObject.dimensions.depth / 2,
          ],
          [
            destination[0] + originalObject.dimensions.width / 2,
            0.3,
            destination[2] + originalObject.dimensions.depth / 2,
          ],
        ]}
        color="#10b981"
        lineWidth={2}
        dashed
        dashSize={0.12}
        gapSize={0.06}
      />
    </group>
  );
}
