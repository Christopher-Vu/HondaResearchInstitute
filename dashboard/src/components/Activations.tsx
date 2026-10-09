import { ArrowDown, ArrowRight } from "@phosphor-icons/react/dist/ssr";
import Image from "next/image";
import type { ReactNode } from "react";
import { Legend, MARK } from "./Legend";

export type ReplayFrame = { route: string; step: number; pathMetres: number; speedMetres: number; lastFrame: boolean };

const LAYERS = 24;
// A replayed plan that moves more than this has changed its decision, not just its rounding.
const FLIP_METRES = 1;

function Node({ title, detail, children }: { title: string; detail: string; children?: ReactNode }) {
  return (
    <div className="rounded-xl bg-surface p-4 shadow-[0_0_0_1px_var(--hairline)]">
      {children}
      <p className="t-title">{title}</p>
      <p className="t-label mt-0.5">{detail}</p>
    </div>
  );
}

function Arrow() {
  return (
    <div aria-hidden className="flex items-center justify-center text-ink-3">
      <ArrowDown size={18} className="lg:hidden" />
      <ArrowRight size={18} className="hidden lg:block" />
    </div>
  );
}

function LayerStack() {
  return (
    <div aria-hidden className="mb-3 grid gap-[3px]">
      {Array.from({ length: LAYERS }, (_, index) => (
        <div key={index} className="h-[3px] rounded-full bg-ink-3/40" />
      ))}
    </div>
  );
}

// Where SimLingo's activations are recorded on every step of every route.
export function ModelDiagram() {
  return (
    <figure>
      <div className="grid items-stretch gap-2 lg:grid-cols-[1fr_auto_1fr_auto_1.15fr_auto_1fr_auto_1fr]">
        <Node title="Camera image" detail="Front camera, one frame per step">
          <Image src="/savio-route-26956.png" alt="" width={1024} height={512} className="mb-3 w-full rounded-md outline-1 -outline-offset-1 outline-[var(--image-outline)]" />
        </Node>
        <Arrow />
        <Node title="Vision encoder" detail="InternViT-300M turns the image into tokens" />
        <Arrow />
        <div className="rounded-xl bg-surface p-4 shadow-[0_0_0_1px_var(--accent),0_0_18px_var(--accent-glow)]">
          <LayerStack />
          <p className="t-title">24 decoder layers</p>
          <p className="t-label mt-0.5">Qwen2-0.5B, 896 numbers per token</p>
        </div>
        <Arrow />
        <Node title="Driving head" detail="30 query tokens: 20 for the path, 10 for speed" />
        <Arrow />
        <Node title="Waypoints" detail="Path and speed, then steering and throttle" />
      </div>
      <figcaption className="t-label mt-4 flex items-start gap-2">
        <span aria-hidden className="mt-1 size-2 shrink-0 rounded-full bg-accent" />
        Recorded on every step: each layer&apos;s average over all tokens and over the 30 driving tokens. The exact model input is saved every 10th step, so any frame can be replayed.
      </figcaption>
    </figure>
  );
}

export function LayerSweep({ definitionUrl }: { definitionUrl: string }) {
  return (
    <div>
      <p className="t-title mb-3">Which layer best predicts a failure</p>
      <div aria-hidden className="grid grid-cols-[repeat(24,minmax(0,1fr))] gap-[3px]">
        {Array.from({ length: LAYERS }, (_, index) => (
          <div key={index} className="h-10 rounded-[3px] bg-track" />
        ))}
      </div>
      <div aria-hidden className="t-label t-data mt-1.5 flex justify-between"><span>Layer 1</span><span>12</span><span>24</span></div>
      <p className="t-body mt-3">
        Not measured yet. Step 4&apos;s layer sweep is running on Savio over 190 dev-pool routes, scored against B7, which was frozen before any activation was opened.{" "}
        <a href={definitionUrl} className="text-ink underline underline-offset-2">Read B7&apos;s definition</a>
      </p>
    </div>
  );
}

const LOG_MIN = Math.log10(0.005);
const LOG_MAX = Math.log10(10);
const atLog = (metres: number) => `${((Math.log10(Math.max(metres, 0.005)) - LOG_MIN) / (LOG_MAX - LOG_MIN)) * 100}%`;
const TICKS: [number, string][] = [[0.01, "1 cm"], [0.1, "10 cm"], [1, "1 m"], [10, "10 m"]];

function median(values: number[]): number {
  const sorted = [...values].sort((a, b) => a - b);
  const middle = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[middle] : (sorted[middle - 1] + sorted[middle]) / 2;
}

function centimetres(metres: number): string {
  return metres >= 1 ? `${metres.toFixed(1)} m` : `${(metres * 100).toFixed(1)} cm`;
}

function StripRow({ name, values }: { name: string; values: { value: number; key: string }[] }) {
  const middle = median(values.map((entry) => entry.value));
  return (
    <div className="grid items-center gap-x-4 gap-y-1 sm:grid-cols-[8rem_1fr]">
      <div>
        <p className="t-title">{name}</p>
        <p className="t-label t-data">Median {centimetres(middle)}</p>
      </div>
      <div className="relative h-7">
        <div className="absolute top-1/2 h-px w-full bg-hairline" />
        {values.map((entry) => (
          <div
            key={entry.key}
            title={`${entry.key}: ${centimetres(entry.value)}`}
            className={`absolute top-1/2 size-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full shadow-[0_0_0_1.5px_var(--page)] ${entry.value > FLIP_METRES ? "bg-accent" : "bg-ink-3/70"}`}
            style={{ left: atLog(entry.value) }}
          />
        ))}
        <div className="absolute inset-y-0 w-0.5 -translate-x-1/2 rounded-full bg-ink" style={{ left: atLog(middle) }} />
      </div>
    </div>
  );
}

export function ReplayStrip({ frames }: { frames: ReplayFrame[] }) {
  const flips = frames.filter((frame) => frame.speedMetres > FLIP_METRES);
  const key = (frame: ReplayFrame) => `Route ${frame.route}, step ${frame.step}`;
  return (
    <div>
      <div className="mb-4 flex flex-wrap items-baseline justify-between gap-3">
        <p className="t-title">How far Savio&apos;s precision moves the plan</p>
        <Legend items={[
          { label: "One replayed frame", className: "bg-ink-3/70 rounded-full" },
          { label: "Decision changed", className: `${MARK.accent} rounded-full`, count: flips.length },
          { label: "Median", className: "bg-ink w-0.5 rounded-full" },
        ]} />
      </div>
      <div className="space-y-3" role="img"
        aria-label={`${frames.length} frames logged in 32-bit on the Mac and replayed in bfloat16. Path waypoints moved a median ${centimetres(median(frames.map((frame) => frame.pathMetres)))}; speed waypoints a median ${centimetres(median(frames.map((frame) => frame.speedMetres)))}, with ${flips.length} frames changing the decision.`}>
        <StripRow name="Path waypoints" values={frames.map((frame) => ({ value: frame.pathMetres, key: key(frame) }))} />
        <StripRow name="Speed waypoints" values={frames.map((frame) => ({ value: frame.speedMetres, key: key(frame) }))} />
        <div aria-hidden className="grid sm:grid-cols-[8rem_1fr] sm:gap-x-4">
          <span />
          <div className="t-label t-data relative h-4">
            {TICKS.map(([metres, label]) => (
              <span key={label} className={`absolute whitespace-nowrap ${metres === 10 ? "-translate-x-full" : "-translate-x-1/2"}`} style={{ left: atLog(metres) }}>{label}</span>
            ))}
          </div>
        </div>
      </div>
      <p className="t-label mt-4">
        {frames.length} frames from {new Set(frames.map((frame) => frame.route)).size} Mac routes, logged in 32-bit and replayed in bfloat16, the format Savio runs.
        In {flips.map((frame) => `route ${frame.route} at step ${frame.step}`).join(" and ")}, the 32-bit plan keeps going while the bfloat16 plan brakes.
      </p>
    </div>
  );
}
