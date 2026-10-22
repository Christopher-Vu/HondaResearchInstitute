import { Cube, MapTrifold } from "@phosphor-icons/react";

export type View = "3d" | "top";

const OPTIONS = [
  { view: "3d", label: "3D street", Icon: Cube },
  { view: "top", label: "Top-down", Icon: MapTrifold },
] as const;

export function ViewSwitch({ view, onChange, disabled }: { view: View; onChange: (view: View) => void; disabled: boolean }) {
  return (
    <div role="radiogroup" aria-label="Camera view" className="flex gap-1 rounded-lg bg-b-wash p-1">
      {OPTIONS.map(({ view: option, label, Icon }) => {
        const selected = option === view;
        return (
          <button
            key={option}
            type="button"
            role="radio"
            aria-checked={selected}
            disabled={disabled}
            onClick={() => onChange(option)}
            className={`flex min-h-10 flex-1 items-center justify-center gap-2 rounded-md text-sm font-semibold disabled:opacity-50 ${
              selected ? "bg-b-paper text-b-ink shadow-sm" : "text-b-ink-2"
            }`}
          >
            <Icon size={18} weight={selected ? "fill" : "regular"} aria-hidden="true" />
            {label}
          </button>
        );
      })}
    </div>
  );
}
