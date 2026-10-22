import { appearanceGaps, controlCheck, layers, occlusion } from "./facts";

const ARROW_HEAD = "arrow-head";

function ArrowDefs() {
  return (
    <defs>
      <marker id={ARROW_HEAD} viewBox="0 0 10 10" refX={8} refY={5} markerWidth={5} markerHeight={5} orient="auto-start-reverse">
        <path d="M0 0 L10 5 L0 10 Z" fill="var(--b-ink-3)" />
      </marker>
    </defs>
  );
}

function Arrow({ d, dashed = false }: { d: string; dashed?: boolean }) {
  return (
    <path d={d} fill="none" stroke="var(--b-ink-3)" strokeWidth={6} markerEnd={`url(#${ARROW_HEAD})`} strokeDasharray={dashed ? "18 14" : undefined} />
  );
}

function CameraFrame() {
  return (
    <g>
      <rect x={0} y={150} width={220} height={130} fill="var(--b-blue-mid)" />
      <path d="M0 280 L80 205 L140 205 L220 280 Z" fill="var(--b-asphalt)" />
      <rect x={106} y={215} width={8} height={18} fill="var(--b-gold)" />
      <rect x={106} y={248} width={8} height={22} fill="var(--b-gold)" />
      <text x={110} y={350} textAnchor="middle" className="p-label-strong" fill="var(--b-ink)">Camera</text>
      <text x={110} y={396} textAnchor="middle" className="p-label" fill="var(--b-ink-3)">every drive</text>
    </g>
  );
}

function LayerStack() {
  const rows = Array.from({ length: 24 }, (_, i) => i);
  return (
    <g transform="translate(300 0)">
      {rows.map((layer) => (
        <rect
          key={layer}
          x={0}
          y={(23 - layer) * 13}
          width={180}
          height={8}
          fill={layer === layers.chosen ? "var(--b-gold)" : "var(--b-rule)"}
        />
      ))}
      <rect x={-8} y={(23 - layers.chosen) * 13 - 6} width={196} height={20} fill="none" stroke="var(--b-gold-deep)" strokeWidth={4} />
      <text x={90} y={350} textAnchor="middle" className="p-label-strong" fill="var(--b-ink)">SimLingo</text>
      <text x={90} y={396} textAnchor="middle" className="p-label" fill="var(--b-ink-3)">layer 10</text>
    </g>
  );
}

const FAILING = [[40, 60], [70, 40], [56, 92], [96, 70], [30, 110], [88, 112], [120, 96], [64, 132]];
const PASSING = [[150, 210], [180, 190], [200, 236], [166, 256], [214, 280], [240, 214], [130, 270], [190, 300]];

function SignalSplit() {
  return (
    <g transform="translate(590 0)">
      <path d="M10 300 L250 20" stroke="var(--b-gold-deep)" strokeWidth={8} markerEnd={`url(#${ARROW_HEAD})`} />
      {FAILING.map(([x, y]) => (
        <circle key={`f${x}-${y}`} cx={x} cy={y} r={14} fill="var(--b-blue)" />
      ))}
      {PASSING.map(([x, y]) => (
        <circle key={`p${x}-${y}`} cx={x} cy={y} r={13} fill="var(--b-paper)" stroke="var(--b-ink-3)" strokeWidth={5} />
      ))}
      <text x={130} y={350} textAnchor="middle" className="p-label-strong" fill="var(--b-ink)">Contrast</text>
      <text x={130} y={396} textAnchor="middle" className="p-label" fill="var(--b-ink-3)">failing vs clean</text>
    </g>
  );
}

const AXES = [
  { label: "Axis 1", share: 1, top: true },
  { label: "Axis 2", share: 0.55, top: false },
  { label: "Axis 3", share: 0.32, top: false },
];

function RankedAxes() {
  return (
    <g transform="translate(936 60)">
      {AXES.map((axis, i) => (
        <g key={axis.label} transform={`translate(0 ${i * 78})`}>
          <rect x={0} y={0} width={280} height={44} fill="var(--b-paper)" />
          <rect x={0} y={0} width={280 * axis.share} height={44} fill={axis.top ? "var(--b-gold)" : "var(--b-blue-mid)"} />
        </g>
      ))}
      <text x={140} y={290} textAnchor="middle" className="p-label-strong" fill="var(--b-ink)">Axes</text>
      <text x={140} y={336} textAnchor="middle" className="p-label" fill="var(--b-ink-3)">ranked</text>
    </g>
  );
}

export function PipelineFigure() {
  return (
    <svg viewBox="0 0 1216 540" width="100%" role="img" aria-label="Camera frames go into SimLingo; we read layer 10, contrast failing against clean drives, and rank failure axes; the axes choose new scenarios to train on">
      <ArrowDefs />
      <CameraFrame />
      <Arrow d="M236 215 L286 215" />
      <LayerStack />
      <Arrow d="M500 160 L570 160" />
      <SignalSplit />
      <Arrow d="M860 160 L920 160" />
      <RankedAxes />
      <Arrow d="M1076 420 L1076 470 L390 470 L390 426" dashed />
      <text x={733} y={530} textAnchor="middle" className="p-label" fill="var(--b-ink-2)">Next: generate those scenarios and retrain</text>
    </svg>
  );
}

function Waffle({ y, failed, total, label, fill }: { y: number; failed: number; total: number; label: string; fill: string }) {
  const cells = Array.from({ length: total }, (_, i) => i);
  const columns = 10;
  const size = 40;
  const gap = 8;
  return (
    <g transform={`translate(0 ${y})`}>
      <text x={0} y={60} className="p-figure" fill={fill === "var(--b-blue)" ? "var(--b-blue)" : "var(--b-ink-2)"}>
        {failed}
        <tspan className="p-label" fill="var(--b-ink-3)"> of {total}</tspan>
      </text>
      <text x={0} y={118} className="p-label-strong" fill="var(--b-ink)">{label}</text>
      {cells.map((i) => (
        <rect
          key={i}
          x={(i % columns) * (size + gap)}
          y={140 + Math.floor(i / columns) * (size + gap)}
          width={size}
          height={size}
          fill={i < failed ? fill : "var(--b-paper)"}
        />
      ))}
    </g>
  );
}

export function OcclusionWaffles() {
  return (
    <svg viewBox="0 0 480 870" width="100%" role="img" aria-label={`${occlusion.blocked.failed} of 60 routes failed with the camera centre blocked, ${occlusion.clear.failed} of 60 with a clear camera`}>
      <Waffle y={0} failed={occlusion.blocked.failed} total={occlusion.blocked.routes} label="Centre blocked" fill="var(--b-blue)" />
      <Waffle y={440} failed={occlusion.clear.failed} total={occlusion.clear.routes} label="Clear camera" fill="var(--b-blue-mid)" />
    </svg>
  );
}

export function DecoyRow() {
  const { fog, animals } = appearanceGaps;
  const rows = [
    { src: "/gaps/p3-fog.jpg", alt: "Farm road fading into grey fog", name: "Dense fog", gap: fog },
    { src: "/gaps/p6-zebra.jpg", alt: "A zebra on the verge of a suburban road", name: "Animals crossing", gap: animals },
  ];
  return (
    <div className="grid grid-cols-2 gap-[32px]">
      {rows.map((row) => (
        <figure key={row.name} className="flex flex-col gap-[14px]">
          {/* eslint-disable-next-line @next/next/no-img-element -- print export needs the raw file, no optimizer */}
          <img src={row.src} alt={row.alt} className="aspect-[2/1] w-full object-cover" />
          <figcaption className="p-label">
            <span className="p-label-strong">{row.name}:</span> {row.gap.with.failed} of {row.gap.with.routes} failed, against {row.gap.without.failed} of {row.gap.without.routes}
          </figcaption>
        </figure>
      ))}
    </div>
  );
}

const AUROC_MIN = 0.5;
const AUROC_MAX = 0.8;

export function LayerChart() {
  const width = 784;
  const height = 500;
  const plotLeft = 110;
  const plotTop = 60;
  const plotBottom = 430;
  const slot = (width - plotLeft) / layers.scores.length;
  const x = (layer: number) => plotLeft + layer * slot;
  const y = (auroc: number) => plotBottom - ((auroc - AUROC_MIN) / (AUROC_MAX - AUROC_MIN)) * (plotBottom - plotTop);
  const best = layers.scores.find((s) => s.layer === layers.chosen);
  return (
    <svg viewBox={`0 0 ${width} ${height}`} width="100%" role="img" aria-label="Failure-flagging score for each of SimLingo's 24 layers; layer 10 is highest at 0.764, where 0.5 is chance">
      {[0.5, 0.6, 0.7, 0.8].map((tick) => (
        <g key={tick}>
          <line x1={plotLeft} x2={width} y1={y(tick)} y2={y(tick)} stroke="var(--b-rule)" strokeWidth={tick === 0.5 ? 5 : 3} />
          <text x={plotLeft - 16} y={y(tick) + 13} textAnchor="end" className="p-label" fill="var(--b-ink-3)">
            {tick.toFixed(1)}
          </text>
        </g>
      ))}
      {layers.scores.map(({ layer, auroc }) => (
        <rect
          key={layer}
          x={x(layer) + 3}
          y={y(auroc)}
          width={slot - 6}
          height={plotBottom - y(auroc)}
          fill={layer === layers.chosen ? "var(--b-gold)" : "var(--b-blue-mid)"}
          opacity={layer === layers.chosen ? 1 : 0.55}
        />
      ))}
      {best && (
        <text x={x(best.layer) + slot / 2} y={y(best.auroc) - 18} textAnchor="middle" className="p-label-strong" fill="var(--b-ink)">
          {best.auroc.toFixed(2)}
        </text>
      )}
      <text x={x(0)} y={height - 8} className="p-label" fill="var(--b-ink-3)">Layer 0</text>
      <text x={x(layers.chosen) + slot / 2} y={height - 8} textAnchor="middle" className="p-label-strong" fill="var(--b-ink)">10</text>
      <text x={width} y={height - 8} textAnchor="end" className="p-label" fill="var(--b-ink-3)">23</text>
    </svg>
  );
}

const CONTROL_BAR = 520;

function ControlBar({ y, name, overlap, fill }: { y: number; name: string; overlap: number; fill: string }) {
  return (
    <g transform={`translate(0 ${y})`}>
      <text x={0} y={36} className="p-label-strong" fill="var(--b-ink)">{name}</text>
      <rect x={0} y={56} width={CONTROL_BAR} height={40} fill="var(--b-paper)" />
      <rect x={0} y={56} width={CONTROL_BAR * overlap} height={40} fill={fill} />
      <text x={CONTROL_BAR + 24} y={90} className="p-label-strong" fill="var(--b-ink)">{overlap.toFixed(2)}</text>
    </g>
  );
}

export function ControlBars() {
  return (
    <svg viewBox="0 0 696 500" width="100%" role="img" aria-label="Overlap with the planted failure: our contrastive axes 0.70, human taxonomy 0.70, random axes 0.70, flagging every failure 0.70">
      <defs>
        <pattern id="hatch-control" width={22} height={22} patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
          <rect width={22} height={22} fill="var(--b-paper)" />
          <line x1={0} y1={0} x2={0} y2={22} stroke="var(--b-ink-3)" strokeWidth={7} />
        </pattern>
      </defs>
      {controlCheck.methods.map((method, i) => (
        <ControlBar key={method.name} y={i * 116} name={method.name} overlap={method.overlap} fill={method.ours ? "var(--b-gold)" : "var(--b-blue-mid)"} />
      ))}
      <ControlBar y={348} name="Flag every failure" overlap={controlCheck.overlap} fill="url(#hatch-control)" />
      <text x={0} y={492} className="p-note" fill="var(--b-ink-3)">
        {controlCheck.plantedFailures} planted of {controlCheck.developmentFailures} failures
      </text>
    </svg>
  );
}
