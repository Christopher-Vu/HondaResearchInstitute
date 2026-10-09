export type Swatch = { label: string; className: string; count?: number | string };

// Mark shapes shared by every chart, so a swatch always matches the mark it names.
export const MARK = {
  quiet: "bg-quiet",
  ink: "bg-ink",
  accent: "bg-accent",
  inkStall: "bg-ink shadow-[inset_0_0_0_2.5px_var(--accent)]",
  hollow: "shadow-[inset_0_0_0_1.5px_var(--ink-3)]",
  ring: "shadow-[inset_0_0_0_2px_var(--ink-3)]",
  track: "bg-track",
};

export function Legend({ items }: { items: Swatch[] }) {
  return (
    <ul className="flex flex-wrap gap-x-5 gap-y-2">
      {items.map((item) => (
        <li key={item.label} className="flex items-center gap-2">
          <span aria-hidden className={`size-3 shrink-0 rounded-[3px] ${item.className}`} />
          <span className="t-label">
            {item.label}
            {item.count !== undefined && <span className="t-data ml-1.5 font-semibold text-ink">{item.count}</span>}
          </span>
        </li>
      ))}
    </ul>
  );
}
