// Top-down street drawn to scale (48 px = 1 m) so the stopping bars under it share the road's ruler.
// Illustrative physics, matching the /drive demo: 60 km/h, 8 m/s² braking, person 24 m ahead.

const PX_PER_M = 48;
const CAR_FRONT = 420;
const SPEED = 60 / 3.6;
const DECEL = 8;
const PERSON_M = 24;

const LANE = { oncoming: [90, 263], ego: [263, 436], parking: [436, 550] } as const;
const EGO_Y = (LANE.ego[0] + LANE.ego[1]) / 2;

const atMetres = (m: number) => CAR_FRONT + m * PX_PER_M;
const brakingMetres = (SPEED * SPEED) / (2 * DECEL);

const OUTCOMES = [
  { key: "alone", label: "Model alone", reaction: 1.2, y: 700 },
  { key: "sdk", label: "Model + SDK", reaction: 0.25, y: 800 },
] as const;

function Car({ x, y, body, glass, facesLeft = false }: { x: number; y: number; body: string; glass: string; facesLeft?: boolean }) {
  return (
    <g transform={`translate(${x} ${y}) scale(${facesLeft ? -1 : 1} 1)`}>
      <rect x={-216} y={-46} width={216} height={92} rx={22} fill={body} />
      <path d="M-62 -36 L-30 -30 L-30 30 L-62 36 Z" fill={glass} />
      <path d="M-176 -34 L-160 -30 L-160 30 L-176 34 Z" fill={glass} />
      <rect x={-150} y={-38} width={82} height={76} rx={10} fill={body} opacity={0.85} />
      <rect x={-8} y={-38} width={6} height={16} rx={3} fill="var(--b-gold)" />
      <rect x={-8} y={22} width={6} height={16} rx={3} fill="var(--b-gold)" />
    </g>
  );
}

function Van() {
  return (
    <g transform={`translate(${atMetres(PERSON_M) - 22} ${(LANE.parking[0] + LANE.parking[1]) / 2})`}>
      <rect x={-264} y={-50} width={264} height={100} rx={14} fill="var(--b-blue-mid)" />
      <rect x={-232} y={-40} width={170} height={80} rx={6} fill="var(--b-paper)" opacity={0.2} />
      <path d="M-44 -42 L-14 -36 L-14 36 L-44 42 Z" fill="var(--b-blue-deep)" />
    </g>
  );
}

function Person({ x, y }: { x: number; y: number }) {
  return (
    <g transform={`translate(${x} ${y})`}>
      <circle cx={0} cy={0} r={64} fill="none" stroke="var(--b-gold)" strokeWidth={6} />
      <ellipse cx={0} cy={0} rx={30} ry={18} fill="var(--b-paper)" stroke="var(--b-ink)" strokeWidth={5} />
      <circle cx={0} cy={0} r={13} fill="var(--b-gold-deep)" stroke="var(--b-ink)" strokeWidth={4} />
    </g>
  );
}

function CameraView() {
  const reach = 2500;
  const wide = Math.tan((28 * Math.PI) / 180) * reach;
  const blocked = Math.tan((4 * Math.PI) / 180) * reach;
  const tip = CAR_FRONT + reach;
  return (
    <g clipPath="url(#road-clip)">
      <path d={`M${CAR_FRONT} ${EGO_Y} L${tip} ${EGO_Y - wide} L${tip} ${EGO_Y + wide} Z`} fill="var(--b-paper)" opacity={0.1} />
      <path d={`M${tip} ${EGO_Y - wide} L${CAR_FRONT} ${EGO_Y} L${tip} ${EGO_Y + wide}`} fill="none" stroke="var(--b-gold)" strokeWidth={5} strokeDasharray="20 14" />
      <path d={`M${CAR_FRONT} ${EGO_Y} L${tip} ${EGO_Y - blocked} L${tip} ${EGO_Y + blocked} Z`} fill="var(--b-blue-deep)" opacity={0.92} />
      <path d={`M${CAR_FRONT} ${EGO_Y} L${tip} ${EGO_Y - blocked} L${tip} ${EGO_Y + blocked} Z`} fill="url(#hatch)" />
    </g>
  );
}

function Street() {
  const dashes = Array.from({ length: 16 }, (_, i) => i * 190);
  return (
    <g>
      <rect x={0} y={0} width={2880} height={LANE.oncoming[0]} fill="var(--b-wash)" />
      <rect x={0} y={LANE.parking[1]} width={2880} height={90} fill="var(--b-wash)" />
      <rect x={0} y={LANE.oncoming[0]} width={2880} height={LANE.parking[1] - LANE.oncoming[0]} fill="var(--b-asphalt)" />
      <line x1={0} x2={2880} y1={LANE.ego[0] - 5} y2={LANE.ego[0] - 5} stroke="var(--b-gold)" strokeWidth={5} />
      <line x1={0} x2={2880} y1={LANE.ego[0] + 5} y2={LANE.ego[0] + 5} stroke="var(--b-gold)" strokeWidth={5} />
      {dashes.map((x) => (
        <rect key={x} x={x} y={LANE.ego[1] - 3} width={100} height={6} fill="var(--b-paper)" opacity={0.7} />
      ))}
      <line x1={0} x2={2880} y1={LANE.oncoming[0] + 8} y2={LANE.oncoming[0] + 8} stroke="var(--b-paper)" strokeWidth={5} opacity={0.8} />
      <line x1={0} x2={2880} y1={LANE.parking[1] - 2} y2={LANE.parking[1] - 2} stroke="var(--b-ink-3)" strokeWidth={6} />
    </g>
  );
}

function WalkPath() {
  const x = atMetres(PERSON_M);
  return (
    <g>
      <path d={`M${x} ${LANE.parking[1] + 60} L${x} ${EGO_Y + 70}`} stroke="var(--b-paper)" strokeWidth={6} strokeDasharray="4 18" strokeLinecap="round" />
      <path d={`M${x - 18} ${EGO_Y + 92} L${x} ${EGO_Y + 62} L${x + 18} ${EGO_Y + 92}`} fill="none" stroke="var(--b-paper)" strokeWidth={6} strokeLinecap="round" />
    </g>
  );
}

function Callouts() {
  return (
    <g>
      <line x1={1520} x2={1440} y1={LANE.oncoming[0] + 60} y2={EGO_Y - 40} stroke="var(--b-paper)" strokeWidth={4} />
      <text x={1540} y={LANE.oncoming[0] + 74} className="p-label-strong" fill="var(--b-paper)">
        Blocked camera centre: the model cannot see here
      </text>
      <text x={CAR_FRONT - 216} y={LANE.oncoming[0] + 74} className="p-label" fill="var(--b-paper)" opacity={0.85}>
        Camera view
      </text>
    </g>
  );
}

function OutcomeBar({ label, reaction, y, isOurs }: { label: string; reaction: number; y: number; isOurs: boolean }) {
  const reactionM = SPEED * reaction;
  const stopM = reactionM + brakingMetres;
  const hits = stopM > PERSON_M;
  const endM = Math.min(stopM, PERSON_M);
  const fill = isOurs ? "var(--b-gold)" : "var(--b-blue-mid)";
  return (
    <g>
      <text x={CAR_FRONT - 24} y={y + 50} textAnchor="end" className="p-label-strong" fill="var(--b-ink)">
        {label}
      </text>
      <rect x={CAR_FRONT} y={y} width={reactionM * PX_PER_M} height={72} fill="url(#hatch-ink)" />
      <rect x={atMetres(reactionM)} y={y} width={(endM - reactionM) * PX_PER_M} height={72} fill={fill} />
      {hits && (
        <g>
          <Impact x={atMetres(PERSON_M)} y={y + 36} />
          <text x={atMetres(PERSON_M) + 72} y={y + 50} className="p-label-strong" fill="var(--b-ink)">
            hits at {Math.round(impactKmh(reactionM))} km/h
          </text>
        </g>
      )}
      {!hits && (
        <g>
          <rect x={atMetres(stopM) - 6} y={y - 12} width={12} height={96} fill="var(--b-gold-deep)" />
          <text x={atMetres(PERSON_M) + 72} y={y + 50} className="p-label-strong" fill="var(--b-ink)">
            stops {(PERSON_M - stopM).toFixed(1)} m short
          </text>
        </g>
      )}
    </g>
  );
}

function impactKmh(reactionM: number) {
  const brakingRoom = Math.max(0, PERSON_M - reactionM);
  return Math.sqrt(Math.max(0, SPEED * SPEED - 2 * DECEL * brakingRoom)) * 3.6;
}

function Impact({ x, y }: { x: number; y: number }) {
  const spikes = Array.from({ length: 8 }, (_, i) => {
    const angle = (i * Math.PI) / 4;
    return `M${x + Math.cos(angle) * 22} ${y + Math.sin(angle) * 22} L${x + Math.cos(angle) * 48} ${y + Math.sin(angle) * 48}`;
  });
  return (
    <g>
      <circle cx={x} cy={y} r={16} fill="var(--b-crash)" />
      <path d={spikes.join(" ")} stroke="var(--b-crash)" strokeWidth={8} strokeLinecap="round" />
    </g>
  );
}

function Ruler() {
  const ticks = Array.from({ length: 9 }, (_, i) => i * 5);
  const baseY = 880;
  return (
    <g>
      <line x1={CAR_FRONT} x2={atMetres(40)} y1={baseY} y2={baseY} stroke="var(--b-ink-3)" strokeWidth={4} />
      {ticks.map((m) => (
        <g key={m}>
          <line x1={atMetres(m)} x2={atMetres(m)} y1={baseY} y2={baseY + 18} stroke="var(--b-ink-3)" strokeWidth={4} />
          <text x={atMetres(m)} y={baseY + 56} textAnchor="middle" className="p-note" fill="var(--b-ink-3)">
            {m === 0 ? "0 m" : m}
          </text>
        </g>
      ))}
      <line x1={atMetres(PERSON_M)} x2={atMetres(PERSON_M)} y1={EGO_Y + 30} y2={baseY} stroke="var(--b-ink)" strokeWidth={4} strokeDasharray="14 12" />
      <text x={atMetres(PERSON_M) + 16} y={672} className="p-label" fill="var(--b-ink)">
        Person, {PERSON_M} m ahead
      </text>
      <text x={atMetres(40) + 40} y={baseY + 12} className="p-note" fill="var(--b-ink-3)">
        Illustration at 60 km/h
      </text>
    </g>
  );
}

function Legend() {
  return (
    <g transform={`translate(${atMetres(40) + 40} 700)`}>
      <rect x={0} y={0} width={56} height={40} fill="url(#hatch-ink)" />
      <text x={76} y={34} className="p-note" fill="var(--b-ink-2)">Not braking yet</text>
      <rect x={0} y={64} width={28} height={40} fill="var(--b-blue-mid)" />
      <rect x={28} y={64} width={28} height={40} fill="var(--b-gold)" />
      <text x={76} y={98} className="p-note" fill="var(--b-ink-2)">Braking</text>
    </g>
  );
}

function Patterns() {
  return (
    <defs>
      <clipPath id="road-clip">
        <rect x={0} y={LANE.oncoming[0]} width={2880} height={LANE.parking[1] - LANE.oncoming[0]} />
      </clipPath>
      <pattern id="hatch" width={24} height={24} patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
        <line x1={0} y1={0} x2={0} y2={24} stroke="var(--b-paper)" strokeWidth={3} opacity={0.25} />
      </pattern>
      <pattern id="hatch-ink" width={22} height={22} patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
        <rect width={22} height={22} fill="var(--b-paper)" />
        <line x1={0} y1={0} x2={0} y2={22} stroke="var(--b-ink-3)" strokeWidth={7} />
      </pattern>
    </defs>
  );
}

export function HeroScene() {
  return (
    <svg
      viewBox="0 0 2880 940"
      width="100%"
      role="img"
      aria-label="Top-down street: a car's camera has its centre blocked, so a person stepping out from behind a parked van is hidden; the model alone brakes too late and hits them, the model with our SDK stops short"
    >
      <Patterns />
      <Street />
      <CameraView />
      <Car x={CAR_FRONT} y={EGO_Y} body="var(--b-paper)" glass="var(--b-blue)" />
      <g opacity={0.55}>
        <Car x={2700} y={(LANE.oncoming[0] + LANE.oncoming[1]) / 2} body="var(--b-rule)" glass="var(--b-ink-3)" facesLeft />
      </g>
      <Van />
      <WalkPath />
      <Person x={atMetres(PERSON_M)} y={EGO_Y + 6} />
      <Callouts />
      <Ruler />
      {OUTCOMES.map((outcome) => (
        <OutcomeBar key={outcome.key} label={outcome.label} reaction={outcome.reaction} y={outcome.y} isOurs={outcome.key === "sdk"} />
      ))}
      <Legend />
    </svg>
  );
}
