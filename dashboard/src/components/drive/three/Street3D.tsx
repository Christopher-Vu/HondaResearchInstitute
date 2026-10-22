"use client";

import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { useRef, type RefObject } from "react";
import { Vector3, type Camera, type DirectionalLight } from "three";
import { isBraking, type Sim } from "../game";
import { LANES } from "../lanes";
import type { LaneId } from "../physics";
import { LaneActors } from "./Actors";
import { CAR, LANE_ORDER, LANE_X, noseZ, TRACK_CENTRE } from "./layout";
import { usePalette, type Palette, type Token } from "./palette";
import { World } from "./World";

const PAINT: Record<LaneId, Token> = { you: "gold", vla: "blue-mid", sdk: "blue" };
const CAMERA_BEHIND = 22;
const CAMERA_HEIGHT = 12;
const LOOK_AHEAD = 30;
const LABEL_BEHIND_CAR = 1.2;

function ChaseCamera({ travelled }: { travelled: number }) {
  const camera = useThree((state) => state.camera);
  const target = useRef(new Vector3());
  useFrame(() => {
    const z = noseZ(travelled);
    camera.position.set(TRACK_CENTRE, CAMERA_HEIGHT, z + CAMERA_BEHIND);
    target.current.set(TRACK_CENTRE, 0.4, z - LOOK_AHEAD);
    camera.lookAt(target.current);
  });
  return null;
}

// The sun follows the cars so its shadow map only has to cover the stretch on screen.
function Sun({ travelled }: { travelled: number }) {
  const light = useRef<DirectionalLight>(null);
  useFrame(() => {
    const sun = light.current;
    if (!sun) return;
    const z = noseZ(travelled);
    sun.position.set(TRACK_CENTRE - 18, 34, z + 8);
    sun.target.position.set(TRACK_CENTRE, 0, z - 18);
    sun.target.updateMatrixWorld();
  });
  return (
    <directionalLight
      ref={light}
      intensity={2.2}
      castShadow
      shadow-mapSize={[1024, 1024]}
      shadow-camera-left={-26}
      shadow-camera-right={26}
      shadow-camera-top={34}
      shadow-camera-bottom={-34}
      shadow-camera-far={90}
      shadow-bias={-0.0005}
    />
  );
}

type LabelElements = Record<LaneId, HTMLSpanElement | null>;

const projected = new Vector3();
const LABEL_MARGIN = 6;

function clamp(value: number, low: number, high: number) {
  return Math.min(Math.max(value, low), high);
}

// Runs in the frame loop, outside render: pins each lane's name to the road just behind its car,
// clear of the pedestrian ahead.
function placeLabels(camera: Camera, size: { width: number; height: number }, sim: Sim, elements: LabelElements) {
  for (const lane of LANE_ORDER) {
    const element = elements[lane];
    if (!element) continue;
    projected.set(LANE_X[lane], 0, noseZ(sim.cars[lane].y) + CAR.length + LABEL_BEHIND_CAR).project(camera);
    const half = element.offsetWidth / 2;
    const y = clamp(((1 - projected.y) / 2) * size.height, LABEL_MARGIN, size.height - element.offsetHeight - LABEL_MARGIN);
    const x = clamp(((projected.x + 1) / 2) * size.width, half + LABEL_MARGIN, size.width - half - LABEL_MARGIN);
    element.style.transform = `translate(${x}px, ${y}px) translate(-50%, 0)`;
  }
}

function LaneLabels({ sim, labels }: { sim: Sim; labels: RefObject<LabelElements> }) {
  useFrame(({ camera, size }) => placeLabels(camera, size, sim, labels.current));
  return null;
}

function Scene({ sim, palette, labels }: { sim: Sim; palette: Palette; labels: RefObject<LabelElements> }) {
  const travelled = sim.cars.you.y;
  return (
    <>
      <color attach="background" args={[palette.wash]} />
      <fog attach="fog" args={[palette.wash, 60, 170]} />
      <hemisphereLight args={[palette.paper, palette.asphalt, 1.1]} />
      <Sun travelled={travelled} />
      <ChaseCamera travelled={travelled} />
      <LaneLabels sim={sim} labels={labels} />
      <World palette={palette} />
      {LANE_ORDER.map((lane) => (
        <group key={lane} position={[LANE_X[lane], 0, 0]}>
          <LaneActors
            car={sim.cars[lane]}
            paint={palette[PAINT[lane]]}
            braking={isBraking(sim, lane)}
            scenario={sim.scenario}
            time={sim.time}
            palette={palette}
          />
        </group>
      ))}
    </>
  );
}

const LABEL_ORDER = LANE_ORDER.map((id) => LANES.find((lane) => lane.id === id)!);

export function Street3D({ sim }: { sim: Sim }) {
  const frame = useRef<HTMLDivElement>(null);
  const labels = useRef<LabelElements>({ you: null, vla: null, sdk: null });
  const palette = usePalette(frame);
  return (
    <div ref={frame} className="relative aspect-square w-full overflow-hidden bg-b-wash">
      {palette && (
        <Canvas shadows dpr={[1, 2]} camera={{ fov: 50, near: 0.5, far: 260 }} aria-hidden="true">
          <Scene sim={sim} palette={palette} labels={labels} />
        </Canvas>
      )}
      {LABEL_ORDER.map((lane) => (
        <span
          key={lane.id}
          ref={(element) => {
            labels.current[lane.id] = element;
          }}
          className="pointer-events-none absolute top-0 left-0 flex items-center gap-1.5 rounded-full bg-b-paper px-2.5 py-1 text-sm font-semibold whitespace-nowrap text-b-ink shadow-md"
        >
          <span className={`size-2.5 rounded-full ${lane.dotClass}`} aria-hidden="true" />
          {lane.label}
        </span>
      ))}
    </div>
  );
}
