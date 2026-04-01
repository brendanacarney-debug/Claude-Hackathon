import { Text } from "@react-three/drei";

import type { Hazard, RoomObject } from "@/lib/types";

const defaultColors: Record<string, string> = {
  rug: "#b45309",
  bed: "#93c5fd",
  chair: "#818cf8",
  table: "#fbbf24",
  door: "#64748b",
  toilet: "#e2e8f0",
  shelf: "#d4a574",
  nightstand: "#c08457",
  lamp: "#fde68a",
  grab_bar: "#34d399",
  bathtub: "#bfdbfe",
  counter: "#cbd5e1",
};

const severityColors = {
  urgent: "#ef4444",
  moderate: "#f59e0b",
  low: "#10b981",
} as const;

export function RoomObjectMesh({
  object,
  worldPosition,
  hazard,
}: {
  object: RoomObject;
  worldPosition: [number, number, number];
  hazard?: Hazard;
}) {
  const color = hazard
    ? severityColors[hazard.severity]
    : defaultColors[object.category] ?? "#cbd5e1";
  const meshHeight = object.category === "rug" ? 0.03 : object.dimensions.height;
  const label = object.category.replace(/_/g, " ");

  return (
    <group
      position={[
        worldPosition[0] + object.dimensions.width / 2,
        worldPosition[1] + meshHeight / 2,
        worldPosition[2] + object.dimensions.depth / 2,
      ]}
    >
      <mesh castShadow receiveShadow>
        <boxGeometry
          args={[object.dimensions.width, meshHeight, object.dimensions.depth]}
        />
        <meshStandardMaterial color={color} transparent opacity={hazard ? 0.88 : 0.58} />
      </mesh>

      {hazard?.severity === "urgent" ? (
        <mesh>
          <boxGeometry
            args={[
              object.dimensions.width + 0.12,
              meshHeight + 0.12,
              object.dimensions.depth + 0.12,
            ]}
          />
          <meshStandardMaterial
            color={color}
            emissive={color}
            emissiveIntensity={0.65}
            transparent
            opacity={0.18}
          />
        </mesh>
      ) : null}

      <Text
        position={[0, meshHeight / 2 + 0.22, 0]}
        fontSize={0.14}
        color={hazard ? color : "#475569"}
        anchorX="center"
      >
        {label}
      </Text>
    </group>
  );
}
