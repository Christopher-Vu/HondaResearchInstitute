import { useCallback, useEffect, useRef, useState } from "react";
import { advanceSim, createSim, PREVIEW_SCENARIO, pressBrake, type Sim } from "./game";
import { createScenario, MAX_FRAME_S } from "./physics";

function useSimLoop(running: boolean, simRef: { current: Sim }, lastFrameRef: { current: number }, commit: (sim: Sim) => void) {
  useEffect(() => {
    if (!running) return;
    let handle = 0;
    let previous = performance.now();
    lastFrameRef.current = previous;
    const tick = (now: number) => {
      const dt = Math.min(Math.max((now - previous) / 1000, 0), MAX_FRAME_S);
      previous = now;
      lastFrameRef.current = now;
      commit(advanceSim(simRef.current, dt));
      handle = requestAnimationFrame(tick);
    };
    handle = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(handle);
  }, [running, simRef, lastFrameRef, commit]);
}

export function useDriveGame() {
  const [sim, setSim] = useState<Sim>(() => createSim(PREVIEW_SCENARIO, "ready"));
  const [held, setHeld] = useState(false);
  const simRef = useRef(sim);
  const lastFrameRef = useRef(0);

  const commit = useCallback((next: Sim) => {
    simRef.current = next;
    setSim(next);
  }, []);

  useSimLoop(sim.phase === "running", simRef, lastFrameRef, commit);

  const start = useCallback(() => {
    setHeld(false);
    commit(createSim(createScenario(), "running"));
  }, [commit]);

  const press = useCallback(() => {
    const sinceFrame = Math.min(Math.max((performance.now() - lastFrameRef.current) / 1000, 0), MAX_FRAME_S);
    setHeld(true);
    commit(pressBrake(simRef.current, sinceFrame));
  }, [commit]);

  const release = useCallback(() => setHeld(false), []);

  return { sim, held, start, press, release };
}
