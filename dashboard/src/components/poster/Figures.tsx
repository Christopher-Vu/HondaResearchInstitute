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
  const grid = Array.from({ length: 7 }, (_, i) => i);
  return (
    <g transform="translate(0 110)">
      <rect x={0} y={0} width={230} height={150} fill="var(--b-blue-mid)" />
      <path d="M0 150 L88 70 L142 70 L230 150 Z" fill="var(--b-asphalt)" />
      <rect x={111} y={84} width={8} height={18} fill="var(--b-gold)" />
      <rect x={111} y={116} width={8} height={24} fill="var(--b-gold)" />
      {grid.map((i) => (
        <g key={i} opacity={0.35}>
          <line x1={(i + 1) * 28.75} x2={(i + 1) * 28.75} y1={0} y2={150} stroke="var(--b-paper)" strokeWidth={1.5} />
          <line x1={0} x2={230} y1={(i + 1) * 18.75} y2={(i + 1) * 18.75} stroke="var(--b-paper)" strokeWidth={1.5} />
        </g>
      ))}
      <rect x={-6} y={-6} width={242} height={162} fill="none" stroke="var(--b-ink-3)" strokeWidth={3} />
    </g>
  );
}

const NET = { x: 320, top: 40, columns: 7, nodes: 6, columnGap: 72, nodeGap: 52, probe: 3 };

function netNode(column: number, row: number) {
  return { x: NET.x + column * NET.columnGap, y: NET.top + row * NET.nodeGap };
}

function NetworkEdges() {
  const edges: React.ReactNode[] = [];
  for (let column = 0; column < NET.columns - 1; column++) {
    const touchesProbe = column === NET.probe || column + 1 === NET.probe;
    for (let from = 0; from < NET.nodes; from++) {
      for (let to = 0; to < NET.nodes; to++) {
        const a = netNode(column, from);
        const b = netNode(column + 1, to);
        edges.push(
          <line
            key={`${column}-${from}-${to}`}
            x1={a.x}
            y1={a.y}
            x2={b.x}
            y2={b.y}
            stroke={touchesProbe ? "var(--b-gold-deep)" : "var(--b-ink-3)"}
            strokeWidth={touchesProbe ? 1.6 : 1.2}
            opacity={touchesProbe ? 0.45 : 0.22}
          />,
        );
      }
    }
  }
  return <g>{edges}</g>;
}

function NetworkNodes() {
  const nodes: React.ReactNode[] = [];
  for (let column = 0; column < NET.columns; column++) {
    for (let row = 0; row < NET.nodes; row++) {
      const { x, y } = netNode(column, row);
      const isProbe = column === NET.probe;
      nodes.push(
        <circle
          key={`${column}-${row}`}
          cx={x}
          cy={y}
          r={isProbe ? 13 : 11}
          fill={isProbe ? "var(--b-gold)" : "var(--b-paper)"}
          stroke={isProbe ? "var(--b-gold-deep)" : "var(--b-blue)"}
          strokeWidth={4}
        />,
      );
    }
  }
  return <g>{nodes}</g>;
}

function Network() {
  const probe = netNode(NET.probe, 0);
  const bottom = netNode(NET.probe, NET.nodes - 1);
  return (
    <g>
      <NetworkEdges />
      <rect x={probe.x - 26} y={probe.y - 26} width={52} height={bottom.y - probe.y + 52} rx={26} fill="var(--b-gold)" opacity={0.18} />
      <NetworkNodes />
      <line x1={bottom.x} x2={bottom.x} y1={bottom.y + 26} y2={bottom.y + 62} stroke="var(--b-gold-deep)" strokeWidth={4} />
    </g>
  );
}

// Activations as a small connected cloud; the gold plane is the contrast direction cutting through it.
const CLOUD = { x: 860, y: 40 };
const FAILING = [[30, 70], [70, 40], [60, 112], [112, 80], [24, 150], [104, 140], [146, 116], [86, 176]];
const CLEAN = [[200, 230], [236, 196], [262, 252], [214, 290], [286, 300], [304, 222], [170, 300], [250, 336]];
const CLOUD_EDGES: [number, number][] = [[0, 1], [0, 2], [1, 3], [2, 4], [2, 5], [3, 6], [5, 7], [6, 7]];
const CROSS_EDGES: [number, number][] = [[6, 1], [7, 6], [5, 0], [3, 2]];

const PLANE = { x1: 40, y1: 300, x2: 330, y2: 40, thickness: 34 };

function sideOfPlane([x, y]: number[]) {
  return (PLANE.x2 - PLANE.x1) * (y - PLANE.y1) - (PLANE.y2 - PLANE.y1) * (x - PLANE.x1);
}

function crossing(a: number[], b: number[]) {
  const sa = sideOfPlane(a);
  const t = sa / (sa - sideOfPlane(b));
  return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t];
}

function CloudEdges({ points, edges }: { points: number[][]; edges: [number, number][] }) {
  return (
    <g>
      {edges.map(([a, b]) => (
        <line key={`${a}-${b}`} x1={points[a][0]} y1={points[a][1]} x2={points[b][0]} y2={points[b][1]} stroke="var(--b-ink-3)" strokeWidth={2} opacity={0.4} />
      ))}
    </g>
  );
}

function CuttingPlane() {
  const dx = PLANE.thickness * 0.7;
  const dy = PLANE.thickness;
  const face = `M${PLANE.x1 - dx} ${PLANE.y1 - dy} L${PLANE.x2 - dx} ${PLANE.y2 - dy} L${PLANE.x2 + dx} ${PLANE.y2 + dy} L${PLANE.x1 + dx} ${PLANE.y1 + dy} Z`;
  return (
    <g>
      <path d={face} fill="var(--b-gold)" opacity={0.28} />
      <path d={face} fill="none" stroke="var(--b-gold-deep)" strokeWidth={4} />
    </g>
  );
}

function ContrastCut() {
  const cuts = CROSS_EDGES.map(([f, c]) => ({ from: FAILING[f], to: CLEAN[c], at: crossing(FAILING[f], CLEAN[c]) }));
  const normalStart = [(PLANE.x1 + PLANE.x2) / 2, (PLANE.y1 + PLANE.y2) / 2];
  return (
    <g transform={`translate(${CLOUD.x} ${CLOUD.y})`}>
      <CloudEdges points={FAILING} edges={CLOUD_EDGES} />
      <CloudEdges points={CLEAN} edges={CLOUD_EDGES} />
      {cuts.map(({ from, to }) => (
        <line key={`${from}-${to}`} x1={from[0]} y1={from[1]} x2={to[0]} y2={to[1]} stroke="var(--b-ink-3)" strokeWidth={2} strokeDasharray="6 8" opacity={0.55} />
      ))}
      <CuttingPlane />
      {cuts.map(({ at }) => (
        <circle key={`${at[0]}-${at[1]}`} cx={at[0]} cy={at[1]} r={8} fill="var(--b-gold-deep)" />
      ))}
      {FAILING.map(([x, y]) => (
        <circle key={`f${x}-${y}`} cx={x} cy={y} r={14} fill="var(--b-blue)" />
      ))}
      {CLEAN.map(([x, y]) => (
        <circle key={`c${x}-${y}`} cx={x} cy={y} r={13} fill="var(--b-paper)" stroke="var(--b-ink-3)" strokeWidth={5} />
      ))}
      <path d={`M${normalStart[0]} ${normalStart[1]} L${normalStart[0] - 92} ${normalStart[1] - 104}`} stroke="var(--b-blue)" strokeWidth={8} markerEnd={`url(#${ARROW_HEAD})`} />
    </g>
  );
}

const AXES = [
  { rank: 1, share: 1 },
  { rank: 2, share: 0.55 },
  { rank: 3, share: 0.32 },
];

function RankedAxes() {
  return (
    <g transform="translate(1290 110)">
      {AXES.map((axis, i) => (
        <g key={axis.rank} transform={`translate(0 ${i * 56})`}>
          <text x={0} y={34} className="p-label-strong" fill="var(--b-ink)">{axis.rank}</text>
          <rect x={44} y={4} width={218} height={36} fill="var(--b-paper)" />
          <rect x={44} y={4} width={218 * axis.share} height={36} fill={axis.rank === 1 ? "var(--b-gold)" : "var(--b-blue-mid)"} />
        </g>
      ))}
    </g>
  );
}

const STAGES = [
  { x: 115, title: "Camera", note: "every drive" },
  { x: NET.x + ((NET.columns - 1) * NET.columnGap) / 2, title: "SimLingo", note: "read layer 10" },
  { x: CLOUD.x + 170, title: "Contrast", note: "a plane splits fail from clean" },
  { x: 1421, title: "Failure axes", note: "ranked" },
];

export function PipelineFigure() {
  return (
    <svg viewBox="0 0 1552 620" width="100%" role="img" aria-label="Camera frames go into SimLingo's network; we read layer 10, cut its activations with a plane that separates failing from clean drives, and rank the resulting failure axes; the axes choose new scenarios to train on">
      <ArrowDefs />
      <CameraFrame />
      <Arrow d="M248 185 L296 185" />
      <Network />
      <Arrow d="M790 185 L846 185" />
      <ContrastCut />
      <Arrow d="M1216 185 L1270 185" />
      <RankedAxes />
      {STAGES.map((stage) => (
        <g key={stage.title}>
          <text x={stage.x} y={470} textAnchor="middle" className="p-label-strong" fill="var(--b-ink)">{stage.title}</text>
          <text x={stage.x} y={516} textAnchor="middle" className="p-label" fill="var(--b-ink-3)">{stage.note}</text>
        </g>
      ))}
      <Arrow d="M1421 540 L1421 590 L536 590 L536 548" dashed />
      <text x={980} y={576} textAnchor="middle" className="p-label" fill="var(--b-ink-2)">Next: generate those scenarios and retrain</text>
    </svg>
  );
}

function Waffle({ x, failed, total, label, fill }: { x: number; failed: number; total: number; label: string; fill: string }) {
  const cells = Array.from({ length: total }, (_, i) => i);
  const columns = 10;
  const size = 32;
  const gap = 6;
  return (
    <g transform={`translate(${x} 0)`}>
      <text x={0} y={70} className="p-figure" fill={fill}>
        {failed}
        <tspan className="p-label" fill="var(--b-ink-3)"> of {total} failed</tspan>
      </text>
      <text x={0} y={124} className="p-label-strong" fill="var(--b-ink)">{label}</text>
      {cells.map((i) => (
        <rect
          key={i}
          x={(i % columns) * (size + gap)}
          y={150 + Math.floor(i / columns) * (size + gap)}
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
    <svg viewBox="0 0 800 380" width="100%" role="img" aria-label={`${occlusion.blocked.failed} of 60 routes failed with the camera centre blocked, ${occlusion.clear.failed} of 60 with a clear camera`}>
      <Waffle x={0} failed={occlusion.blocked.failed} total={occlusion.blocked.routes} label="Centre blocked" fill="var(--b-blue)" />
      <Waffle x={420} failed={occlusion.clear.failed} total={occlusion.clear.routes} label="Clear camera" fill="var(--b-blue-mid)" />
    </svg>
  );
}

export function GapGallery() {
  const { fog, animals } = appearanceGaps;
  const rows = [
    {
      src: "/poster/p4-blocked.jpg",
      alt: "A CARLA highway frame with the middle third of the image blacked out",
      name: "Centre blocked",
      crop: "object-center",
      verdict: "a real gap",
      counts: `${occlusion.blocked.failed} of ${occlusion.blocked.routes} failed, against ${occlusion.clear.failed} of ${occlusion.clear.routes}`,
    },
    {
      src: "/gaps/p3-fog.jpg",
      alt: "Farm road fading into grey fog",
      name: "Dense fog",
      crop: "object-center",
      verdict: "a decoy",
      counts: `${fog.with.failed} of ${fog.with.routes} failed, against ${fog.without.failed} of ${fog.without.routes}`,
    },
    {
      src: "/gaps/p6-zebra.jpg",
      alt: "A zebra on the verge of a suburban road",
      name: "Animals crossing",
      crop: "object-right",
      verdict: "a decoy",
      counts: `${animals.with.failed} of ${animals.with.routes} failed, against ${animals.without.failed} of ${animals.without.routes}`,
    },
  ];
  return (
    <div className="grid grid-cols-3 gap-[40px]">
      {rows.map((row) => (
        <figure key={row.name} className="flex flex-col gap-[16px]">
          {/* eslint-disable-next-line @next/next/no-img-element -- print export needs the raw file, no optimizer */}
          <img src={row.src} alt={row.alt} className={`aspect-[4/3] w-full object-cover ${row.crop}`} />
          <figcaption className="flex flex-col gap-[4px]">
            <span className="p-label-strong">
              {row.name}: <span className={row.verdict === "a real gap" ? "text-b-blue" : "text-b-ink-3"}>{row.verdict}</span>
            </span>
            <span className="p-label">{row.counts}</span>
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

const CONTROL_BAR = 640;

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
    <svg viewBox="0 0 800 500" width="100%" role="img" aria-label="Overlap with the planted failure: our contrastive axes 0.70, human taxonomy 0.70, random axes 0.70, flagging every failure 0.70">
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
