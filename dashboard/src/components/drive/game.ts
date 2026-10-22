import {
  createCar,
  MAX_STEP_S,
  SDK_REACTION_S,
  SPEED_MS,
  stepCar,
  STEP_OUT_S,
  VLA_REACTION_S,
  type CarState,
  type LaneId,
  type Scenario,
} from "./physics";

export type Phase = "ready" | "running" | "early" | "done";

export interface Sim {
  phase: Phase;
  time: number;
  scenario: Scenario;
  cars: Record<LaneId, CarState>;
  brakeLatched: boolean;
  reactionMs: number | null;
}

export const LANE_IDS: readonly LaneId[] = ["you", "vla", "sdk"];

export const PREVIEW_SCENARIO: Scenario = { spawnTime: 3, distance: 23.5, pedestrianY: SPEED_MS * 3 + 23.5 };

export function createSim(scenario: Scenario, phase: Phase): Sim {
  return {
    phase,
    time: 0,
    scenario,
    cars: { you: createCar(), vla: createCar(), sdk: createCar() },
    brakeLatched: false,
    reactionMs: null,
  };
}

export function pedestrianHasAppeared(time: number, scenario: Scenario) {
  return time >= scenario.spawnTime;
}

export function stepOutProgress(time: number, scenario: Scenario) {
  return Math.min(1, Math.max(0, (time - scenario.spawnTime) / STEP_OUT_S));
}

function modelBrakes(time: number, scenario: Scenario, reactionS: number) {
  return time >= scenario.spawnTime + reactionS;
}

export function isBraking(sim: Sim, lane: LaneId) {
  if (lane === "you") return sim.brakeLatched;
  const reaction = lane === "vla" ? VLA_REACTION_S : SDK_REACTION_S;
  return modelBrakes(sim.time, sim.scenario, reaction);
}

export function advanceSimBy(sim: Sim, elapsed: number): Sim {
  let next = sim;
  for (let remaining = elapsed; remaining > 0 && next.phase === "running"; remaining -= MAX_STEP_S) {
    next = advanceSim(next, Math.min(remaining, MAX_STEP_S));
  }
  return next;
}

export function advanceSim(sim: Sim, dt: number): Sim {
  if (sim.phase !== "running") return sim;
  const cars = { ...sim.cars };
  for (const lane of LANE_IDS) {
    cars[lane] = stepCar(sim.cars[lane], dt, isBraking(sim, lane), sim.scenario.pedestrianY);
  }
  const finished = LANE_IDS.every((lane) => cars[lane].outcome !== "driving");
  return { ...sim, time: sim.time + dt, cars, phase: finished ? "done" : "running" };
}

export function pressBrake(sim: Sim, secondsSinceFrame: number): Sim {
  if (sim.phase !== "running" || sim.brakeLatched) return sim;
  const pressTime = sim.time + secondsSinceFrame;
  if (!pedestrianHasAppeared(pressTime, sim.scenario)) return { ...sim, phase: "early" };
  const reactionMs = Math.round((pressTime - sim.scenario.spawnTime) * 1000);
  return { ...sim, brakeLatched: true, reactionMs };
}
