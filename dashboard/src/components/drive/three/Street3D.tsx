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
// The driver's eye in the visitor's car: left seat, behind the windscreen, above the hood.
// At this height and distance the gold hood fills about the bottom quarter of the frame.
const EYE = { x: LANE_X.you - 0.38, height: 1.45, behindNose: 1.6 } as const;
const LOOK_AHEAD = 40;
const LOOK_HEIGHT = 1.05;
// Braking pitches the view down about 2 degrees, the way a car's nose dips, eased in and out.
const BRAKE_DIP = 1.4;
const DIP_RATE = 8;
const LABEL_ABOVE_ROOF = 2.1;

function DriverCamera({ travelled, braking }: { travelled: number; braking: boolean }) {
  const camera = useThree((state) => state.camera);
  const target = useRef(new Vector3());
  const dip = useRef(0);
  useFrame((_, delta) => {
    const z = noseZ(travelled);
    dip.current += ((braking ? BRAKE_DIP : 0) - dip.current) * Math.min(1, delta * DIP_RATE);
    camera.position.set(EYE.x, EYE.height, z + EYE.behindNose);
    target.current.set(EYE.x, LOOK_HEIGHT - dip.current, z - LOOK_AHEAD);
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

// The visitor is the driver, so only the two model lanes carry a name tag.
const TAGGED_LANES = LANE_ORDER.filter((lane) => lane !== "you");
type LabelElements = Partial<Record<LaneId, HTMLSpanElement | null>>;

const projected = new Vector3();

// Runs in the frame loop, outside render: floats each model car's name above its roof, and hides it
// while that car is behind the driver or out of frame.
function placeLabels(camera: Camera, size: { width: number; height: number }, sim: Sim, elements: LabelElements) {
  for (const lane of TAGGED_LANES) {
    const element = elements[lane];
    if (!element) continue;
    projected.set(LANE_X[lane], LABEL_ABOVE_ROOF, noseZ(sim.cars[lane].y) + CAR.length / 2).project(camera);
    const inView = projected.z < 1 && Math.abs(projected.x) < 1 && Math.abs(projected.y) < 1;
    element.style.visibility = inView ? "visible" : "hidden";
    const x = ((projected.x + 1) / 2) * size.width;
    const y = ((1 - projected.y) / 2) * size.height;
    element.style.transform = `translate(${x}px, ${y}px) translate(-50%, -100%)`;
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
      <DriverCamera travelled={travelled} braking={isBraking(sim, "you")} />
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
            showImpact={lane !== "you"}
          />
        </group>
      ))}
    </>
  );
}

const LABEL_ORDER = TAGGED_LANES.map((id) => LANES.find((lane) => lane.id === id)!);

export function Street3D({ sim }: { sim: Sim }) {
  const frame = useRef<HTMLDivElement>(null);
  const labels = useRef<LabelElements>({});
  const palette = usePalette(frame);
  return (
    <div ref={frame} className="relative aspect-square w-full overflow-hidden bg-b-wash">
      {palette && (
        // A nearer clip plane costs depth precision, and the ground then shows through the road far ahead.
        <Canvas shadows dpr={[1, 2]} camera={{ fov: 62, near: 0.5, far: 260 }} aria-hidden="true">
          <Scene sim={sim} palette={palette} labels={labels} />
        </Canvas>
      )}
      {/* The driver's own crash: the 3D burst would sit at the windscreen, so the view's edges glow instead. */}
      <div
        aria-hidden="true"
        className={`pointer-events-none absolute inset-0 shadow-[inset_0_0_90px_28px_var(--b-crash)] transition-opacity duration-150 ${sim.cars.you.outcome === "hit" ? "opacity-100" : "opacity-0"}`}
      />
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
