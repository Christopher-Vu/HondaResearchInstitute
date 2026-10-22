export type LaneId = "you" | "vla" | "sdk";

export const SPEED_MS = 60 / 3.6;
export const BRAKE_DECEL = 8;
// Physics steps at most this long, so a slow frame is split into several steps rather than clamped:
// the simulation clock must keep pace with the wall clock or reaction times read short on slow phones.
export const MAX_STEP_S = 1 / 60;
// A longer gap than this means the tab was hidden; it is not driving time.
export const MAX_FRAME_S = 0.25;
export const VLA_REACTION_S = 1.2;
export const SDK_REACTION_S = 0.25;
export const STEP_OUT_S = 0.5;

const SPAWN_RANGE_S = [2, 4.5] as const;
// Nearest spawn stays beyond the SDK lane's 21.5 m stopping distance, so only reaction time decides the other lanes.
const DISTANCE_RANGE_M = [23, 27] as const;

export interface Scenario {
  spawnTime: number;
  distance: number;
  pedestrianY: number;
}

export interface CarState {
  y: number;
  speed: number;
  outcome: "driving" | "stopped" | "hit";
  gap: number;
  impactSpeed: number;
}

function randomBetween(random: () => number, [low, high]: readonly [number, number]) {
  return low + random() * (high - low);
}

export function createScenario(random: () => number = Math.random): Scenario {
  const spawnTime = randomBetween(random, SPAWN_RANGE_S);
  const distance = randomBetween(random, DISTANCE_RANGE_M);
  return { spawnTime, distance, pedestrianY: SPEED_MS * spawnTime + distance };
}

export function createCar(): CarState {
  return { y: 0, speed: SPEED_MS, outcome: "driving", gap: 0, impactSpeed: 0 };
}

function distanceTravelled(speed: number, decel: number, dt: number) {
  const brakingTime = decel > 0 ? Math.min(dt, speed / decel) : dt;
  return speed * brakingTime - 0.5 * decel * brakingTime * brakingTime;
}

function speedAtDistance(speed: number, decel: number, distance: number) {
  return Math.sqrt(Math.max(0, speed * speed - 2 * decel * distance));
}

export function stepCar(car: CarState, dt: number, braking: boolean, pedestrianY: number): CarState {
  if (car.outcome !== "driving") return car;
  const decel = braking ? BRAKE_DECEL : 0;
  const nextY = car.y + distanceTravelled(car.speed, decel, dt);
  if (nextY >= pedestrianY) {
    const impactSpeed = speedAtDistance(car.speed, decel, pedestrianY - car.y);
    return { y: pedestrianY, speed: 0, outcome: "hit", gap: 0, impactSpeed };
  }
  const nextSpeed = Math.max(0, car.speed - decel * dt);
  if (nextSpeed === 0) {
    return { y: nextY, speed: 0, outcome: "stopped", gap: pedestrianY - nextY, impactSpeed: 0 };
  }
  return { ...car, y: nextY, speed: nextSpeed };
}
