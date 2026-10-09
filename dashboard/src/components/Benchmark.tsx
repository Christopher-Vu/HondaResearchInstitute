import { signed } from "@/lib/format";
import type { Ability, Spread } from "@/lib/types";
import { Legend, MARK } from "./Legend";

const at = (value: number) => `${Math.min(100, Math.max(0, value))}%`;

// One score on a 0-100 scale: ours as the bar, the paper's mean as a tick with a whisker for one
// standard deviation, and the pass bar as a hairline, when there is one.
export function BulletRow({ name, ours, paper, bar, unit = "", index }: {
  name: string;
  ours: number;
  paper: Spread;
  bar?: number;
  unit?: string;
  index: number;
}) {
  const legend = [{ label: `Paper ${paper.mean.toFixed(1)}${unit} ± ${paper.sd.toFixed(1)}`, className: "bg-ink" }];
  if (bar !== undefined) legend.push({ label: `Pass bar ${bar}`, className: "bg-ink-3" });
  return (
    <div role="img" aria-label={`${name}: ours ${ours.toFixed(1)}${unit}, paper ${paper.mean.toFixed(1)}${unit} plus or minus ${paper.sd.toFixed(1)}${bar ? `, pass bar ${bar}` : ""}.`}>
      <div className="mb-3 flex items-baseline justify-between gap-4">
        <span className="t-title">{name}</span>
        <span className="flex items-baseline gap-2.5">
          <span className="t-label t-data whitespace-nowrap">{signed(ours - paper.mean)} vs paper</span>
          <span className="t-figure">{ours.toFixed(1)}{unit}</span>
        </span>
      </div>
      <div className="relative h-4 rounded-[4px] bg-track">
        <div className="grow-x h-full rounded-[4px] bg-accent" style={{ width: at(ours), ["--i" as string]: index * 3 }} />
        {bar !== undefined && <div className="absolute -inset-y-1.5 w-px bg-ink-3" style={{ left: at(bar) }} />}
        <div className="absolute top-1/2 h-0.5 -translate-y-1/2 bg-ink" style={{ left: at(paper.mean - paper.sd), width: at(2 * paper.sd) }}>
          <div className="absolute -inset-y-1.5 left-0 w-0.5 bg-ink" />
          <div className="absolute -inset-y-1.5 right-0 w-0.5 bg-ink" />
        </div>
        <div className="absolute -inset-y-2 w-[3px] -translate-x-1/2 rounded-full bg-ink shadow-[0_0_0_2px_var(--page)]" style={{ left: at(paper.mean) }} />
      </div>
      <div className="t-label t-data mt-1.5 flex justify-between" aria-hidden><span>0</span><span>100</span></div>
      <div className="mt-2" aria-hidden><Legend items={legend} /></div>
    </div>
  );
}

const ABILITY_NAMES: Record<Ability, string> = {
  traffic_signs: "Traffic signs",
  emergency_brake: "Emergency brake",
  overtaking: "Overtaking",
  merging: "Merging",
  give_way: "Give way",
};

function DumbbellRow({ name, ours, paper, index }: { name: string; ours: number; paper: number; index: number }) {
  const low = Math.min(ours, paper);
  const growsRight = ours >= paper;
  return (
    <li className="grid grid-cols-[7.5rem_1fr_3rem] items-center gap-3 py-2.5">
      <span className="t-label text-ink-2">{name}</span>
      <div className="relative h-4" aria-hidden>
        <div className="absolute top-1/2 h-px w-full bg-hairline" />
        <div
          className="grow-x absolute top-1/2 h-0.5 -translate-y-1/2 bg-ink-3"
          style={{ left: `${low}%`, width: `${Math.abs(ours - paper)}%`, transformOrigin: growsRight ? "left" : "right", ["--i" as string]: index + 2 }}
        />
        <div className={`absolute top-1/2 size-3 -translate-x-1/2 -translate-y-1/2 rounded-full bg-surface ${MARK.ring}`} style={{ left: `${paper}%` }} />
        <div className="rise-in absolute top-1/2 size-3 -translate-x-1/2 -translate-y-1/2 rounded-full bg-accent shadow-[0_0_0_2px_var(--page)]" style={{ left: `${ours}%`, ["--i" as string]: index + 6 }} />
      </div>
      <span className="t-title t-data text-right">{Math.round(ours)}%</span>
      <span className="sr-only">{name}: ours {ours.toFixed(1)}%, paper {paper.toFixed(1)}%.</span>
    </li>
  );
}

export function AbilityChart({ ours, paper }: { ours: Record<Ability, number>; paper: Record<Ability, number> }) {
  const abilities = (Object.keys(ABILITY_NAMES) as Ability[]).sort((a, b) => ours[b] - ours[a]);
  return (
    <div>
      <div className="mb-3 flex flex-wrap items-baseline justify-between gap-3">
        <span className="t-title">Success by ability</span>
        <Legend items={[{ label: "Savio, one seed", className: `${MARK.accent} rounded-full` }, { label: "Paper", className: `${MARK.ring} rounded-full` }]} />
      </div>
      <ul>
        {abilities.map((ability, index) => (
          <DumbbellRow key={ability} name={ABILITY_NAMES[ability]} ours={ours[ability] * 100} paper={paper[ability] * 100} index={index} />
        ))}
      </ul>
      <div className="grid grid-cols-[7.5rem_1fr_3rem] gap-3" aria-hidden>
        <span />
        <div className="t-label t-data flex justify-between"><span>0%</span><span>50%</span><span>100%</span></div>
      </div>
    </div>
  );
}
