"use client";

import { useRef, useState, type PointerEvent } from "react";
import type { Route } from "@/lib/types";
import { sentenceCase } from "@/lib/format";
import { Legend, MARK } from "./Legend";

type Kind = "passed" | "passedStall" | "failedStall" | "failed" | "skipped";

const KINDS: { kind: Kind; label: string; mark: string }[] = [
  { kind: "passed", label: "Passed", mark: MARK.quiet },
  { kind: "passedStall", label: "Passed after standing still 38+ s", mark: MARK.accent },
  { kind: "failedStall", label: "Failed after standing still", mark: MARK.inkStall },
  { kind: "failed", label: "Failed", mark: MARK.ink },
  { kind: "skipped", label: "Scenario skipped by Bench2Drive", mark: MARK.hollow },
];
const ORDER = Object.fromEntries(KINDS.map((entry, index) => [entry.kind, index])) as Record<Kind, number>;
const MARKS = Object.fromEntries(KINDS.map((entry) => [entry.kind, entry.mark])) as Record<Kind, string>;

function kindOf(route: Route): Kind {
  if (route.outcome === "skipped") return "skipped";
  if (route.outcome === "passed") return route.stalled ? "passedStall" : "passed";
  return route.stalled ? "failedStall" : "failed";
}

function groupByAbility(routes: Route[]): [string, Route[]][] {
  const groups = new Map<string, Route[]>();
  for (const route of routes) groups.set(route.ability, [...(groups.get(route.ability) ?? []), route]);
  return [...groups.entries()]
    .map(([ability, members]): [string, Route[]] => [ability, members.sort((a, b) => ORDER[kindOf(a)] - ORDER[kindOf(b)])])
    .sort((a, b) => b[1].length - a[1].length);
}

type Hover = { route: Route; left: number; top: number };

function Tooltip({ hover }: { hover: Hover }) {
  const { route } = hover;
  return (
    <div
      className="pointer-events-none absolute z-10 w-60 -translate-x-1/2 -translate-y-full rounded-xl bg-surface p-3 shadow-[0_8px_30px_oklch(0.2_0.01_255/0.14),0_0_0_1px_var(--hairline)]"
      style={{ left: hover.left, top: hover.top - 8 }}
    >
      <p className="t-title">{route.scenario}</p>
      <p className="t-label t-data">Route {route.id} in {route.town}</p>
      <p className="t-label t-data mt-1.5">
        {route.score === null ? "Scenario never ran, so outside the clean score" : `Driving score ${route.score}`}
        {route.stalled && `, stood still ${route.stillSeconds} s`}
      </p>
    </div>
  );
}

function RouteTable({ routes }: { routes: Route[] }) {
  return (
    <details className="mt-6">
      <summary className="t-label cursor-pointer select-none hover:text-ink">Show all {routes.length} routes as a table</summary>
      <div className="mt-3 max-h-96 overflow-auto rounded-xl shadow-[0_0_0_1px_var(--hairline)]">
        <table className="t-data w-full text-left text-sm">
          <thead className="sticky top-0 bg-surface">
            <tr className="t-label">
              {["Route", "Town", "Scenario", "Ability", "Outcome", "Score", "Longest stop (s)"].map((heading) => (
                <th key={heading} className="px-3 py-2 font-medium">{heading}</th>
              ))}
            </tr>
          </thead>
          <tbody className="text-ink-2">
            {routes.map((route) => (
              <tr key={route.id} className="border-t border-hairline">
                <td className="px-3 py-1.5">{route.id}</td>
                <td className="px-3 py-1.5">{route.town}</td>
                <td className="px-3 py-1.5">{route.scenario}</td>
                <td className="px-3 py-1.5">{route.ability}</td>
                <td className="px-3 py-1.5">{KINDS[ORDER[kindOf(route)]].label}</td>
                <td className="px-3 py-1.5">{route.score ?? "none"}</td>
                <td className="px-3 py-1.5">{route.stillSeconds}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  );
}

export function RouteWaffle({ routes }: { routes: Route[] }) {
  const frame = useRef<HTMLDivElement>(null);
  const [hover, setHover] = useState<Hover | null>(null);
  const byId = new Map(routes.map((route) => [route.id, route]));
  const counts = Object.fromEntries(KINDS.map(({ kind }) => [kind, routes.filter((route) => kindOf(route) === kind).length]));

  function onPointerOver(event: PointerEvent<HTMLDivElement>) {
    const cell = (event.target as HTMLElement).closest<HTMLElement>("[data-route]");
    const route = cell && byId.get(cell.dataset.route ?? "");
    if (!cell || !route || !frame.current) return setHover(null);
    const box = cell.getBoundingClientRect();
    const origin = frame.current.getBoundingClientRect();
    setHover({ route, left: box.left - origin.left + box.width / 2, top: box.top - origin.top });
  }

  return (
    <div>
      <Legend items={KINDS.map(({ kind, label, mark }) => ({ label, className: mark, count: counts[kind] }))} />
      <div
        ref={frame}
        className="relative mt-6 space-y-5"
        onPointerOver={onPointerOver}
        onPointerLeave={() => setHover(null)}
        role="img"
        aria-label={`${routes.length} Bench2Drive routes grouped by ability: ${KINDS.map(({ kind, label }) => `${counts[kind]} ${label.toLowerCase()}`).join(", ")}. The full list is in the table below.`}
      >
        {groupByAbility(routes).map(([ability, members]) => {
          const passed = members.filter((route) => route.outcome === "passed").length;
          return (
            <div key={ability} className="grid gap-x-5 gap-y-2 md:grid-cols-[9rem_1fr]">
              <div className="flex items-baseline justify-between md:block">
                <p className="t-title">{sentenceCase(ability)}</p>
                <p className="t-label t-data">{passed} of {members.length} passed</p>
              </div>
              <div className="grid grid-cols-[repeat(20,minmax(0,1fr))] gap-[3px]">
                {members.map((route) => (
                  <div key={route.id} data-route={route.id} className={`aspect-square rounded-[3px] ${MARKS[kindOf(route)]}`} />
                ))}
              </div>
            </div>
          );
        })}
        {hover && <Tooltip hover={hover} />}
      </div>
      <RouteTable routes={routes} />
    </div>
  );
}
