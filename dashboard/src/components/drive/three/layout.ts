import type { LaneId } from "../physics";

// World units are metres. Cars drive toward -z; a car that has travelled y metres has its nose at z = -y.
// Lanes sit side by side: model alone on the left, the visitor in the middle, model + SDK on the right.
export const LANE_PITCH = 6.6;
export const LANE_HALF_WIDTH = 1.75;
export const PARKING_WIDTH = 2.3;
export const BARRIER_OFFSET = LANE_HALF_WIDTH + PARKING_WIDTH + 0.55;

export const LANE_X: Record<LaneId, number> = { vla: -LANE_PITCH, you: 0, sdk: LANE_PITCH };
export const LANE_ORDER: readonly LaneId[] = ["vla", "you", "sdk"];

export const TRACK_LEFT = LANE_X.vla - LANE_HALF_WIDTH - 0.65;
export const TRACK_RIGHT = LANE_X.sdk + BARRIER_OFFSET;
export const TRACK_CENTRE = (TRACK_LEFT + TRACK_RIGHT) / 2;

export const ROAD_START_Z = 30;
export const ROAD_END_Z = -230;
export const ROAD_LENGTH = ROAD_START_Z - ROAD_END_Z;

export const CAR = { width: 1.9, length: 4.5 } as const;
export const VAN = { width: 2.1, length: 5.5, height: 2.2, x: LANE_HALF_WIDTH + 1.15 } as const;
export const PEDESTRIAN_START_X = VAN.x + VAN.width / 2 + 0.55;

export const noseZ = (travelled: number) => -travelled;
