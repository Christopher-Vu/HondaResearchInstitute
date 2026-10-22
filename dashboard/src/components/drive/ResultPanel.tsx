import { CheckCircle, XCircle } from "@phosphor-icons/react";
import { Button } from "./Button";
import type { Sim } from "./game";
import { LANES } from "./lanes";
import { buildHeadline, buildRows } from "./summary";

interface ResultPanelProps {
  sim: Sim;
  onRetry: () => void;
}

function OutcomeIcon({ outcome }: { outcome: "stopped" | "hit" }) {
  if (outcome === "hit") return <XCircle size={28} weight="fill" className="shrink-0 text-b-crash" aria-label="Hit" />;
  return <CheckCircle size={28} weight="fill" className="shrink-0 text-b-blue" aria-label="Stopped safely" />;
}

function ResultRows({ sim }: { sim: Sim }) {
  return (
    <ul className="divide-y divide-b-rule rounded-lg bg-b-wash px-4">
      {buildRows(sim).map((row, index) => (
        <li key={row.lane} className="flex items-center gap-3 py-3">
          <OutcomeIcon outcome={row.outcome} />
          <div className="min-w-0 flex-1">
            <p className="text-base font-semibold text-b-ink">{LANES[index].label}</p>
            <p className="text-sm text-b-ink-2">{row.detail}</p>
          </div>
          <p className="text-base font-medium tabular-nums text-b-ink">{row.reaction}</p>
        </li>
      ))}
    </ul>
  );
}

export function ResultPanel({ sim, onRetry }: ResultPanelProps) {
  if (sim.phase === "early") {
    return (
      <div className="flex flex-col gap-4">
        <p className="text-xl font-semibold text-b-ink">Too early. Wait until someone steps out.</p>
        <Button variant="neutral" onClick={onRetry}>Try again</Button>
      </div>
    );
  }
  return (
    <div className="flex flex-col gap-4">
      <p className="text-xl font-semibold text-b-ink">{buildHeadline(sim)}</p>
      <ResultRows sim={sim} />
      <Button variant="neutral" onClick={onRetry}>Try again</Button>
    </div>
  );
}
