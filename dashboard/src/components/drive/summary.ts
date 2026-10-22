import { LANE_IDS, type Sim } from "./game";
import { SDK_REACTION_S, VLA_REACTION_S, type CarState, type LaneId } from "./physics";

export interface ResultRow {
  lane: LaneId;
  outcome: "stopped" | "hit";
  reaction: string;
  detail: string;
}

function formatMetres(metres: number) {
  return `${metres.toFixed(1)} m`;
}

function formatKmh(speed: number) {
  return `${Math.max(1, Math.round(speed * 3.6))} km/h`;
}

function reactionLabel(lane: LaneId, reactionMs: number | null) {
  if (lane === "vla") return `${Math.round(VLA_REACTION_S * 1000)} ms`;
  if (lane === "sdk") return `${Math.round(SDK_REACTION_S * 1000)} ms`;
  return reactionMs === null ? "No brake" : `${reactionMs} ms`;
}

function detailFor(car: CarState) {
  return car.outcome === "hit" ? `Hit at ${formatKmh(car.impactSpeed)}` : `${formatMetres(car.gap)} to spare`;
}

export function buildRows(sim: Sim): ResultRow[] {
  return LANE_IDS.map((lane) => ({
    lane,
    outcome: sim.cars[lane].outcome === "hit" ? "hit" : "stopped",
    reaction: reactionLabel(lane, sim.reactionMs),
    detail: detailFor(sim.cars[lane]),
  }));
}

export function buildHeadline(sim: Sim) {
  const car = sim.cars.you;
  if (car.outcome === "hit") return `You hit the pedestrian at ${formatKmh(car.impactSpeed)}.`;
  return `You stopped ${formatMetres(car.gap)} short.`;
}
