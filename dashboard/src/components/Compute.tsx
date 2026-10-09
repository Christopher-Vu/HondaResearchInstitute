import { clampPercent, percent, su } from "@/lib/format";
import type { Progress } from "@/lib/types";
import { Legend, MARK } from "./Legend";

export type Spend = { item: string; su: number };

// The whole allowance on one bar: this project's spend, the rest of the program's, and the
// planned work as an outlined range, all against 200,000 SU.
function AllowanceBar({ ours, others, planned, allowance }: {
  ours: number;
  others: number;
  planned: [number, number];
  allowance: number;
}) {
  const used = ours + others;
  return (
    <div>
      <div className="relative h-5 overflow-hidden rounded-[4px] bg-track" role="img"
        aria-label={`Allowance ${su(allowance)} SU: this project ${su(ours)}, others in the program ${su(others)}, planned ${su(planned[0])} to ${su(planned[1])}.`}>
        <div className="grow-x absolute inset-y-0 left-0 bg-accent" style={{ width: clampPercent(ours, allowance) }} />
        <div className="grow-x absolute inset-y-0 bg-ink" style={{ left: clampPercent(ours, allowance), width: clampPercent(others, allowance), ["--i" as string]: 2 }} />
        <div className="absolute inset-y-0 shadow-[inset_0_0_0_1.5px_var(--ink-3)] rounded-r-[4px]"
          style={{ left: clampPercent(used, allowance), width: clampPercent(planned[1], allowance) }} />
        <div className="absolute inset-y-0 bg-ink-3/25" style={{ left: clampPercent(used, allowance), width: clampPercent(planned[0], allowance) }} />
      </div>
      <div className="t-label t-data mt-2 flex justify-between"><span>0</span><span>{su(allowance)} SU</span></div>
      <div className="mt-4">
        <Legend items={[
          { label: "This project", className: MARK.accent, count: su(ours) },
          { label: "Rest of the program", className: MARK.ink, count: su(others) },
          { label: "Planned", className: MARK.hollow, count: `${su(planned[0])} to ${su(planned[1])}` },
        ]} />
      </div>
    </div>
  );
}

function SpendRow({ item, low, high, spent, max, index }: { item: string; low: number; high: number; spent: boolean; max: number; index: number }) {
  const value = low === high ? su(low) : `${su(low)} to ${su(high)}`;
  return (
    <li className="grid grid-cols-[minmax(0,11rem)_1fr] items-center gap-3 py-1.5 sm:grid-cols-[13rem_1fr]">
      <span className="t-label text-ink-2">{item}</span>
      <div className="flex items-center gap-2.5">
        <div className="relative h-3 flex-1">
          {!spent && <div className="absolute inset-y-0 left-0 rounded-r-[4px] shadow-[inset_0_0_0_1.5px_var(--ink-3)]" style={{ width: clampPercent(high, max) }} />}
          <div className={`grow-x absolute inset-y-0 left-0 rounded-r-[4px] ${spent ? "bg-accent" : "bg-ink-3/25"}`}
            style={{ width: clampPercent(low, max), minWidth: 3, ["--i" as string]: index }} />
        </div>
        <span className="t-label t-data w-28 shrink-0 text-right text-ink">{value}</span>
      </div>
    </li>
  );
}

export function SpendChart({ spent, planned }: { spent: Spend[]; planned: Progress["compute"]["planned"] }) {
  const max = Math.max(...planned.map((entry) => entry.su[1]), ...spent.map((entry) => entry.su));
  return (
    <ul aria-label="Service units spent and planned, by item">
      {spent.map((entry, index) => (
        <SpendRow key={entry.item} item={entry.item} low={entry.su} high={entry.su} spent max={max} index={index} />
      ))}
      {planned.map((entry, index) => (
        <SpendRow key={entry.item} item={entry.item} low={entry.su[0]} high={entry.su[1]} spent={false} max={max} index={index + spent.length} />
      ))}
    </ul>
  );
}

export function ComputeSummary({ compute, spent, perRoute }: { compute: Progress["compute"]; spent: Spend[]; perRoute: number }) {
  const ours = spent.reduce((total, entry) => total + entry.su, 0);
  const planned = compute.planned.reduce<[number, number]>((total, entry) => [total[0] + entry.su[0], total[1] + entry.su[1]], [0, 0]);
  return (
    <div className="space-y-10">
      <div className="grid gap-8 md:grid-cols-[auto_minmax(0,1fr)] md:items-end md:gap-12">
        <div className="flex gap-10">
          <p><span className="t-figure block">{percent(compute.program_used_su / compute.allowance_su, 2)}</span><span className="t-label">of the program allowance used</span></p>
          <p><span className="t-figure block">{su(perRoute)}</span><span className="t-label">SU per Bench2Drive route</span></p>
        </div>
        <AllowanceBar ours={ours} others={compute.program_used_su - ours} planned={planned} allowance={compute.allowance_su} />
      </div>
      <div>
        <p className="t-title mb-2">Spent and planned, in SU</p>
        <SpendChart spent={spent} planned={compute.planned} />
      </div>
    </div>
  );
}
