import { Line, Text } from "@react-three/drei";

import type { SafePath } from "@/lib/types";

export function SafePathLine({
  safePath,
  points,
}: {
  safePath: SafePath;
  points: Array<{ point: [number, number, number]; label?: string }>;
}) {
  if (points.length < 2) {
    return null;
  }

  const pointValues = points.map(({ point }) => [
    point[0],
    0.06,
    point[2],
  ] as [number, number, number]);
  const midPoint = pointValues[Math.floor(pointValues.length / 2)];

  return (
    <group>
      <Line points={pointValues} color="#10b981" lineWidth={4} />
      <Line
        points={pointValues}
        color="#10b981"
        lineWidth={12}
        transparent
        opacity={0.22}
      />

      {points.map(({ point, label }, index) => (
        <group
          key={`${label ?? "waypoint"}-${index}`}
          position={[point[0], 0.06, point[2]]}
        >
          <mesh>
            <sphereGeometry args={[0.08]} />
            <meshStandardMaterial
              color="#10b981"
              emissive="#10b981"
              emissiveIntensity={0.4}
            />
          </mesh>
          {label ? (
            <Text position={[0, 0.24, 0]} fontSize={0.12} color="#10b981">
              {label.replace(/_/g, " ")}
            </Text>
          ) : null}
        </group>
      ))}

      {!safePath.width_ok ? (
        <Text position={[midPoint[0], 0.5, midPoint[2]]} fontSize={0.15} color="#ef4444">
          {`Path: ${(safePath.min_width_m * 100).toFixed(0)}cm (need 90cm+)`}
        </Text>
      ) : null}
    </group>
  );
}
