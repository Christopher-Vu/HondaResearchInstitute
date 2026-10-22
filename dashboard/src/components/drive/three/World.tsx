import { memo, useLayoutEffect, useMemo, useRef } from "react";
import { Color, Object3D, type InstancedMesh } from "three";
import {
  BARRIER_OFFSET,
  LANE_HALF_WIDTH,
  LANE_ORDER,
  LANE_X,
  ROAD_END_Z,
  ROAD_LENGTH,
  ROAD_START_Z,
  TRACK_LEFT,
  TRACK_RIGHT,
} from "./layout";
import type { Palette } from "./palette";

const ROAD_MID_Z = (ROAD_START_Z + ROAD_END_Z) / 2;
const SIDEWALK_WIDTH = 4;
const DASH = { length: 3, gap: 4, width: 0.14 };

interface Block {
  x: number;
  z: number;
  width: number;
  depth: number;
  height: number;
  shade: number;
}

// Deterministic so every visitor drives the same street.
function seeded(seed: number) {
  let state = seed;
  return () => {
    state = (state * 1664525 + 1013904223) % 4294967296;
    return state / 4294967296;
  };
}

function buildBlocks(side: -1 | 1, random: () => number): Block[] {
  const blocks: Block[] = [];
  const edge = side < 0 ? TRACK_LEFT - SIDEWALK_WIDTH : TRACK_RIGHT + SIDEWALK_WIDTH;
  for (let z = ROAD_START_Z; z > ROAD_END_Z; ) {
    const depth = 9 + random() * 8;
    const width = 8 + random() * 6;
    blocks.push({ x: edge + side * (width / 2 + 0.5), z: z - depth / 2, width, depth, height: 7 + random() * 22, shade: random() });
    z -= depth + 1.5 + random() * 3;
  }
  return blocks;
}

type Place = (dummy: Object3D, index: number) => void;

function Instances({ items, place, children }: { items: number; place: Place; children: React.ReactNode }) {
  const ref = useRef<InstancedMesh>(null);
  useLayoutEffect(() => {
    const mesh = ref.current;
    if (!mesh) return;
    const dummy = new Object3D();
    for (let i = 0; i < items; i++) {
      place(dummy, i);
      dummy.updateMatrix();
      mesh.setMatrixAt(i, dummy.matrix);
    }
    mesh.instanceMatrix.needsUpdate = true;
  }, [items, place]);
  return (
    <instancedMesh ref={ref} args={[undefined, undefined, items]} receiveShadow>
      {children}
    </instancedMesh>
  );
}

function LaneMarkings({ palette }: { palette: Palette }) {
  const count = Math.floor(ROAD_LENGTH / (DASH.length + DASH.gap));
  const placeDash = useMemo(
    () => (dummy: Object3D, index: number) => {
      const lane = LANE_ORDER[index % LANE_ORDER.length];
      const step = Math.floor(index / LANE_ORDER.length);
      dummy.position.set(LANE_X[lane] + LANE_HALF_WIDTH, 0.02, ROAD_START_Z - step * (DASH.length + DASH.gap));
      dummy.scale.set(DASH.width, 0.01, DASH.length);
    },
    [],
  );
  return (
    <group>
      <Instances items={count * LANE_ORDER.length} place={placeDash}>
        <boxGeometry args={[1, 1, 1]} />
        <meshStandardMaterial color={palette.paper} roughness={0.9} />
      </Instances>
      {LANE_ORDER.map((lane) => (
        <mesh key={lane} position={[LANE_X[lane] - LANE_HALF_WIDTH, 0.02, ROAD_MID_Z]} receiveShadow>
          <boxGeometry args={[0.14, 0.01, ROAD_LENGTH]} />
          <meshStandardMaterial color={palette.gold} roughness={0.6} />
        </mesh>
      ))}
    </group>
  );
}

function Barriers({ palette }: { palette: Palette }) {
  const barrierX = [LANE_X.vla + BARRIER_OFFSET, LANE_X.you + BARRIER_OFFSET];
  return (
    <group>
      {barrierX.map((x) => (
        <mesh key={x} position={[x, 0.4, ROAD_MID_Z]} receiveShadow>
          <boxGeometry args={[0.5, 0.8, ROAD_LENGTH]} />
          <meshStandardMaterial color={palette.rule} roughness={0.85} />
        </mesh>
      ))}
    </group>
  );
}

function Sidewalks({ palette }: { palette: Palette }) {
  const sides = [TRACK_LEFT - SIDEWALK_WIDTH / 2, TRACK_RIGHT + SIDEWALK_WIDTH / 2];
  return (
    <group>
      {sides.map((x) => (
        <mesh key={x} position={[x, 0.12, ROAD_MID_Z]} receiveShadow>
          <boxGeometry args={[SIDEWALK_WIDTH, 0.24, ROAD_LENGTH]} />
          <meshStandardMaterial color={palette.wash} roughness={0.95} />
        </mesh>
      ))}
    </group>
  );
}

interface WindowBand {
  x: number;
  y: number;
  z: number;
  depth: number;
}

function windowBands(blocks: Block[]): WindowBand[] {
  return blocks.flatMap((block) => {
    const floors = Math.floor(block.height / 3.2) - 1;
    const faceX = block.x < 0 ? block.x + block.width / 2 + 0.02 : block.x - block.width / 2 - 0.02;
    return Array.from({ length: floors }, (_, floor) => ({ x: faceX, y: 2.6 + floor * 3.2, z: block.z, depth: block.depth * 0.82 }));
  });
}

function Buildings({ palette }: { palette: Palette }) {
  const blocks = useMemo(() => {
    const random = seeded(7);
    return [...buildBlocks(-1, random), ...buildBlocks(1, random)];
  }, []);
  const bands = useMemo(() => windowBands(blocks), [blocks]);
  const placeBand = useMemo<Place>(
    () => (dummy, index) => {
      const band = bands[index];
      dummy.position.set(band.x, band.y, band.z);
      dummy.scale.set(0.04, 1.3, band.depth);
    },
    [bands],
  );
  const facades = [palette.paper, palette.rule, palette.wash, palette["blue-mid"]];
  return (
    <group>
      {blocks.map((block) => (
        <mesh key={`${block.x}-${block.z}`} position={[block.x, block.height / 2, block.z]} receiveShadow>
          <boxGeometry args={[block.width, block.height, block.depth]} />
          <meshStandardMaterial color={facades[Math.floor(block.shade * facades.length)]} roughness={0.8} />
        </mesh>
      ))}
      <Instances items={bands.length} place={placeBand}>
        <boxGeometry args={[1, 1, 1]} />
        <meshStandardMaterial color={palette["blue-deep"]} roughness={0.25} metalness={0.3} />
      </Instances>
    </group>
  );
}

const TREE_SPOTS = [TRACK_LEFT - 1.6, TRACK_RIGHT + 1.6].flatMap((x) =>
  Array.from({ length: 22 }, (_, i) => ({ x, z: ROAD_START_Z - 6 - i * 11 })),
);

const placeTrunk: Place = (dummy, index) => {
  const spot = TREE_SPOTS[index];
  dummy.position.set(spot.x, 1.2, spot.z);
};

const placeCrown: Place = (dummy, index) => {
  const spot = TREE_SPOTS[index];
  dummy.position.set(spot.x, 3.1, spot.z);
  dummy.rotation.set(0, index * 0.7, 0);
};

function Trees({ palette }: { palette: Palette }) {
  const leaf = useMemo(() => new Color(palette["blue-mid"]).lerp(new Color(palette.ink), 0.35).getStyle(), [palette]);
  return (
    <group>
      <Instances items={TREE_SPOTS.length} place={placeTrunk}>
        <cylinderGeometry args={[0.14, 0.18, 2.4, 8]} />
        <meshStandardMaterial color={palette["ink-3"]} roughness={0.9} />
      </Instances>
      <Instances items={TREE_SPOTS.length} place={placeCrown}>
        <icosahedronGeometry args={[1.35, 0]} />
        <meshStandardMaterial color={leaf} roughness={0.9} flatShading />
      </Instances>
    </group>
  );
}

export const World = memo(function World({ palette }: { palette: Palette }) {
  const width = TRACK_RIGHT - TRACK_LEFT;
  return (
    <group>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.01, ROAD_MID_Z]} receiveShadow>
        <planeGeometry args={[400, ROAD_LENGTH + 200]} />
        <meshStandardMaterial color={palette.rule} roughness={1} />
      </mesh>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[(TRACK_LEFT + TRACK_RIGHT) / 2, 0, ROAD_MID_Z]} receiveShadow>
        <planeGeometry args={[width, ROAD_LENGTH]} />
        <meshStandardMaterial color={palette.asphalt} roughness={0.95} />
      </mesh>
      <LaneMarkings palette={palette} />
      <Barriers palette={palette} />
      <Sidewalks palette={palette} />
      <Trees palette={palette} />
      <Buildings palette={palette} />
    </group>
  );
});
