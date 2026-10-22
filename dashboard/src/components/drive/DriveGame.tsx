"use client";

import dynamic from "next/dynamic";
import { useEffect, useState, useSyncExternalStore } from "react";
import { BrakeButton } from "./BrakeButton";
import { Button } from "./Button";
import { isBraking, LANE_IDS, type Sim } from "./game";
import { Lane } from "./Lane";
import { LANES } from "./lanes";
import { ResultPanel } from "./ResultPanel";
import { useDriveGame } from "./useDriveGame";
import { ViewSwitch, type View } from "./ViewSwitch";

const Street3D = dynamic(() => import("./three/Street3D").then((module) => module.Street3D), {
  ssr: false,
  loading: () => <div className="aspect-square w-full animate-pulse bg-b-wash motion-reduce:animate-none" />,
});

// Probed once: every getContext call opens a WebGL context, and browsers drop the oldest past about 16,
// which would include the scene's own.
let webGLSupport: boolean | null = null;

function detectWebGL() {
  if (webGLSupport !== null) return webGLSupport;
  try {
    const canvas = document.createElement("canvas");
    const context = canvas.getContext("webgl2") ?? canvas.getContext("webgl");
    context?.getExtension("WEBGL_lose_context")?.loseContext();
    webGLSupport = Boolean(context);
  } catch {
    webGLSupport = false;
  }
  return webGLSupport;
}

const noSubscription = () => () => {};

function useWebGL() {
  return useSyncExternalStore(noSubscription, detectWebGL, () => false);
}

const FOOTNOTE =
  "The two model lanes are an illustration. Measured in simulation: with its camera centre blocked, SimLingo failed 43 of 60 routes, against 12 of 60 with a clear camera. The SDK-trained result is our goal and has not been measured yet.";

function useSpaceBar(active: boolean, press: () => void, release: () => void) {
  useEffect(() => {
    if (!active) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.code !== "Space") return;
      event.preventDefault();
      if (!event.repeat) press();
    };
    const onKeyUp = (event: KeyboardEvent) => {
      if (event.code === "Space") release();
    };
    window.addEventListener("keydown", onKeyDown);
    window.addEventListener("keyup", onKeyUp);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      window.removeEventListener("keyup", onKeyUp);
    };
  }, [active, press, release]);
}

function TopDownRoads({ sim }: { sim: Sim }) {
  return (
    <div className="grid grid-cols-3 gap-2 px-4">
      {LANES.map((config, index) => (
        <div key={config.id} className="flex flex-col gap-2">
          <p className="flex min-h-10 items-start gap-1.5 text-sm font-medium leading-tight text-b-ink">
            <span className={`mt-1 size-2.5 shrink-0 rounded-full ${config.dotClass}`} aria-hidden="true" />
            <span>{config.label}</span>
          </p>
          <div className={`overflow-hidden rounded-lg ${index === 0 ? "ring-2 ring-b-gold" : ""}`}>
            <Lane
              config={config}
              car={sim.cars[LANE_IDS[index]]}
              scenario={sim.scenario}
              time={sim.time}
              braking={isBraking(sim, config.id)}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

function Controls({ game }: { game: ReturnType<typeof useDriveGame> }) {
  const { sim, held, start, press, release } = game;
  if (sim.phase === "ready") {
    return (
      <div className="flex flex-col gap-4">
        <p className="text-xl font-semibold text-b-ink">Hold Brake the moment someone steps out.</p>
        <Button onClick={start}>Start</Button>
      </div>
    );
  }
  if (sim.phase === "running") return <BrakeButton held={held} onPress={press} onRelease={release} />;
  return <ResultPanel sim={sim} onRetry={start} />;
}

function RoadView({ sim, view }: { sim: Sim; view: View }) {
  if (view === "3d") return <Street3D sim={sim} />;
  return <TopDownRoads sim={sim} />;
}

export function DriveGame() {
  const game = useDriveGame();
  useSpaceBar(game.sim.phase === "running", game.press, game.release);
  const running = game.sim.phase === "running";
  const hasWebGL = useWebGL();
  const [chosenView, setChosenView] = useState<View>("3d");
  const view = hasWebGL ? chosenView : "top";

  return (
    <main className="mx-auto flex min-h-dvh w-full max-w-md flex-col gap-4 bg-b-paper pt-6">
      <header className="flex flex-col gap-1 px-4">
        <h1 className="text-3xl font-semibold text-b-ink">Can you stop in time?</h1>
        <p className="text-base text-b-ink-2">UC Berkeley x Honda Research Institute</p>
      </header>
      {hasWebGL && (
        <div className="px-4">
          <ViewSwitch view={view} onChange={setChosenView} disabled={running} />
        </div>
      )}
      <RoadView sim={game.sim} view={view} />
      <div
        aria-live="polite"
        className={`px-4 pb-4 ${running ? "sticky bottom-0 bg-b-paper pt-2 pb-[max(1rem,env(safe-area-inset-bottom))]" : ""}`}
      >
        <Controls game={game} />
      </div>
      <p className="px-4 pb-8 text-sm text-b-ink-3">{FOOTNOTE}</p>
    </main>
  );
}
