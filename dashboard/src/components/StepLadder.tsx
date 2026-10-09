import { CheckCircle, Circle } from "@phosphor-icons/react/dist/ssr";
import type { Check, Step } from "@/lib/types";
import { Legend, MARK } from "./Legend";

export function doneCount(step: Step): number {
  return step.checks.filter((check) => check.done).length;
}

// Tooltips near the edges open inward so they stay on screen.
function tooltipAlignment(index: number, total: number): string {
  if (index < 3) return "left-0";
  if (index > total - 4) return "right-0";
  return "left-1/2 -translate-x-1/2";
}

export function CheckList({ checks, size = 18 }: { checks: Check[]; size?: number }) {
  return (
    <ul className="space-y-2">
      {checks.map((check) => (
        <li key={check.text} className="flex items-start gap-2.5">
          {check.done ? (
            <CheckCircle aria-label="Met" size={size} weight="fill" className="mt-px shrink-0 text-ink" />
          ) : (
            <Circle aria-label="Open" size={size} weight="regular" className="mt-px shrink-0 text-ink-3" />
          )}
          <span className={check.done ? "t-body text-ink" : "t-body"}>{check.text}</span>
        </li>
      ))}
    </ul>
  );
}

function Segment({ step, index, total, current }: { step: Step; index: number; total: number; current: boolean }) {
  const done = doneCount(step);
  const fill = (done / step.checks.length) * 100;
  return (
    <li className="group relative">
      <div
        className={`h-6 overflow-hidden rounded-[4px] bg-track ${current ? "shadow-[0_0_14px_var(--accent-glow)]" : ""}`}
      >
        {fill > 0 && (
          <div
            className={`grow-x h-full ${current ? "bg-accent" : "bg-ink"}`}
            style={{ width: `${fill}%`, ["--i" as string]: index }}
          />
        )}
      </div>
      <span aria-hidden className={`t-data mt-2 block text-center text-sm ${current ? "font-bold text-ink" : "text-ink-3"}`}>
        {step.id}
      </span>
      <span className="sr-only">
        Step {step.id}, {step.title}: {done} of {step.checks.length} checks met{current ? ", current step" : ""}.
      </span>
      <div
        aria-hidden
        className={`pointer-events-none invisible absolute bottom-full z-10 mb-3 w-64 rounded-xl bg-surface p-4 opacity-0 shadow-[0_8px_30px_oklch(0.2_0.01_255/0.14),0_0_0_1px_var(--hairline)] transition-[opacity,visibility] duration-150 group-hover:visible group-hover:opacity-100 ${tooltipAlignment(index, total)}`}
      >
        <p className="t-title mb-0.5">Step {step.id}</p>
        <p className="t-label mb-3">{step.title}</p>
        <CheckList checks={step.checks} size={16} />
      </div>
    </li>
  );
}

export function StepLadder({ steps, current }: { steps: Step[]; current: number }) {
  return (
    <div>
      <ol className="grid gap-1" style={{ gridTemplateColumns: `repeat(${steps.length}, minmax(0, 1fr))` }}>
        {steps.map((step, index) => (
          <Segment key={step.id} step={step} index={index} total={steps.length} current={step.id === current} />
        ))}
      </ol>
      <div className="mt-4 flex flex-wrap items-start justify-between gap-x-8 gap-y-3">
        <Legend
          items={[
            { label: "Done-conditions met", className: MARK.ink },
            { label: "Current step", className: MARK.accent },
            { label: "Still open", className: MARK.track },
          ]}
        />
        <details className="group/all">
          <summary className="t-label cursor-pointer select-none hover:text-ink">All steps and their checks</summary>
          <ol className="mt-4 grid gap-5 sm:grid-cols-2">
            {steps.map((step) => (
              <li key={step.id}>
                <p className="t-title mb-2">Step {step.id}: {step.title}</p>
                <CheckList checks={step.checks} size={16} />
              </li>
            ))}
          </ol>
        </details>
      </div>
    </div>
  );
}
