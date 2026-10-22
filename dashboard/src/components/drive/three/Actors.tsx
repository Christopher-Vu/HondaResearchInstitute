import { useFrame } from "@react-three/fiber";
import { useRef } from "react";
import type { Group } from "three";
import { pedestrianHasAppeared, stepOutProgress } from "../game";
import type { CarState, Scenario } from "../physics";
import { CAR, LANE_HALF_WIDTH, noseZ, PEDESTRIAN_START_X, VAN } from "./layout";
import type { Palette } from "./palette";

const WHEEL_SPOTS = [
  [-0.86, 0.85],
  [0.86, 0.85],
  [-0.86, 3.55],
  [0.86, 3.55],
] as const;

export function Car({ z, paint, braking, palette }: { z: number; paint: string; braking: boolean; palette: Palette }) {
  return (
    <group position={[0, 0, z]}>
      <mesh position={[0, 0.62, CAR.length / 2]} castShadow>
        <boxGeometry args={[CAR.width, 0.66, CAR.length]} />
        <meshStandardMaterial color={paint} roughness={0.35} metalness={0.2} />
      </mesh>
      <mesh position={[0, 1.2, CAR.length / 2 + 0.25]} castShadow>
        <boxGeometry args={[1.62, 0.56, 2.3]} />
        <meshStandardMaterial color={palette["blue-deep"]} roughness={0.15} metalness={0.4} />
      </mesh>
      {WHEEL_SPOTS.map(([x, wheelZ]) => (
        <mesh key={`${x}-${wheelZ}`} position={[x, 0.34, wheelZ]} rotation={[0, 0, Math.PI / 2]} castShadow>
          <cylinderGeometry args={[0.34, 0.34, 0.26, 16]} />
          <meshStandardMaterial color={palette.ink} roughness={0.9} />
        </mesh>
      ))}
      {[-0.66, 0.66].map((x) => (
        <mesh key={x} position={[x, 0.78, CAR.length + 0.01]}>
          <boxGeometry args={[0.42, 0.14, 0.04]} />
          <meshStandardMaterial
            color={palette.crash}
            emissive={palette.crash}
            emissiveIntensity={braking ? 2.4 : 0.15}
          />
        </mesh>
      ))}
    </group>
  );
}

export function ParkedVan({ scenario, palette }: { scenario: Scenario; palette: Palette }) {
  const farEnd = noseZ(scenario.pedestrianY - 0.5);
  return (
    <group position={[VAN.x, 0, farEnd + VAN.length / 2]}>
      <mesh position={[0, VAN.height / 2 + 0.25, 0]} castShadow receiveShadow>
        <boxGeometry args={[VAN.width, VAN.height, VAN.length]} />
        <meshStandardMaterial color={palette.paper} roughness={0.5} />
      </mesh>
      <mesh position={[0, VAN.height * 0.72, -VAN.length / 2 - 0.01]}>
        <boxGeometry args={[VAN.width * 0.86, 0.7, 0.04]} />
        <meshStandardMaterial color={palette["blue-deep"]} roughness={0.15} metalness={0.4} />
      </mesh>
      {[-1.7, 1.7].map((wheelZ) =>
        [-0.95, 0.95].map((x) => (
          <mesh key={`${x}-${wheelZ}`} position={[x, 0.36, wheelZ]} rotation={[0, 0, Math.PI / 2]}>
            <cylinderGeometry args={[0.36, 0.36, 0.24, 14]} />
            <meshStandardMaterial color={palette.ink} roughness={0.9} />
          </mesh>
        )),
      )}
    </group>
  );
}

export function Pedestrian({ scenario, time, palette }: { scenario: Scenario; time: number; palette: Palette }) {
  const body = useRef<Group>(null);
  const progress = stepOutProgress(time, scenario);
  const eased = progress * (2 - progress);
  const x = PEDESTRIAN_START_X + (0 - PEDESTRIAN_START_X) * eased;
  const walking = progress > 0 && progress < 1;
  useFrame(({ clock }) => {
    if (body.current) body.current.position.y = walking ? Math.abs(Math.sin(clock.elapsedTime * 11)) * 0.06 : 0;
  });
  if (!pedestrianHasAppeared(time, scenario)) return null;
  return (
    <group position={[x, 0, noseZ(scenario.pedestrianY) - 0.3]} rotation={[0, Math.PI / 2, 0]}>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.04, 0]}>
        <ringGeometry args={[0.75, 1.05, 40]} />
        <meshStandardMaterial color={palette.gold} emissive={palette.gold} emissiveIntensity={0.9} />
      </mesh>
      <group ref={body}>
        <mesh position={[0, 0.45, 0]} castShadow>
          <boxGeometry args={[0.36, 0.9, 0.24]} />
          <meshStandardMaterial color={palette.ink} roughness={0.8} />
        </mesh>
        <mesh position={[0, 1.22, 0]} castShadow>
          <capsuleGeometry args={[0.24, 0.42, 4, 10]} />
          <meshStandardMaterial color={palette["gold-deep"]} roughness={0.7} />
        </mesh>
        <mesh position={[0, 1.74, 0]} castShadow>
          <sphereGeometry args={[0.17, 16, 12]} />
          <meshStandardMaterial color={palette.paper} roughness={0.6} />
        </mesh>
      </group>
    </group>
  );
}

export function Impact({ z, palette }: { z: number; palette: Palette }) {
  const burst = useRef<Group>(null);
  useFrame(({ clock }) => {
    if (!burst.current) return;
    const pulse = 1 + Math.sin(clock.elapsedTime * 9) * 0.12;
    burst.current.scale.setScalar(pulse);
    burst.current.rotation.y += 0.02;
  });
  return (
    <group ref={burst} position={[0, 1.1, z]}>
      <mesh>
        <octahedronGeometry args={[0.55, 0]} />
        <meshStandardMaterial color={palette.crash} emissive={palette.crash} emissiveIntensity={1.6} />
      </mesh>
      <mesh rotation={[Math.PI / 2, 0, 0]}>
        <torusGeometry args={[0.95, 0.07, 8, 32]} />
        <meshStandardMaterial color={palette.crash} emissive={palette.crash} emissiveIntensity={1.2} />
      </mesh>
    </group>
  );
}

export function StopLine({ z, palette }: { z: number; palette: Palette }) {
  return (
    <mesh position={[0, 0.03, z - 0.5]}>
      <boxGeometry args={[LANE_HALF_WIDTH * 2, 0.02, 0.45]} />
      <meshStandardMaterial color={palette.gold} emissive={palette.gold} emissiveIntensity={0.6} />
    </mesh>
  );
}

export function LaneActors({
  car,
  paint,
  braking,
  scenario,
  time,
  palette,
  showImpact,
}: {
  car: CarState;
  paint: string;
  braking: boolean;
  scenario: Scenario;
  time: number;
  palette: Palette;
  showImpact: boolean;
}) {
  const z = noseZ(car.y);
  return (
    <group>
      <ParkedVan scenario={scenario} palette={palette} />
      <Pedestrian scenario={scenario} time={time} palette={palette} />
      <Car z={z} paint={paint} braking={braking} palette={palette} />
      {showImpact && car.outcome === "hit" && <Impact z={z - 0.2} palette={palette} />}
      {car.outcome === "stopped" && <StopLine z={z} palette={palette} />}
    </group>
  );
}
