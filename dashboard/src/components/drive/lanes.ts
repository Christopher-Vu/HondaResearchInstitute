import type { LaneId } from "./physics";

export interface LaneConfig {
  id: LaneId;
  label: string;
  dotClass: string;
  carClass: string;
}

export const LANES: readonly LaneConfig[] = [
  { id: "you", label: "You", dotClass: "bg-b-gold", carClass: "fill-b-gold" },
  { id: "vla", label: "Model alone", dotClass: "bg-b-blue-mid", carClass: "fill-b-blue-mid" },
  { id: "sdk", label: "Model + SDK", dotClass: "bg-b-blue", carClass: "fill-b-blue" },
];
