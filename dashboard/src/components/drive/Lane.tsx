import { pedestrianHasAppeared, stepOutProgress } from "./game";
import type { LaneConfig } from "./lanes";
import type { CarState, Scenario } from "./physics";

const LANE_WIDTH = 96;
const VIEW_HEIGHT = 400;
const PIXELS_PER_METRE = 9;
const CAR_FRONT_Y = 330;
const CAR_LENGTH = 4.5 * PIXELS_PER_METRE;
const CAR_WIDTH = 26;
const CAR_CENTRE_X = 34;
const KERB_X = 86;
const VAN_X = 60;
const VAN_WIDTH = 24;
const VAN_LENGTH = 5.5 * PIXELS_PER_METRE;
const PEDESTRIAN_START_X = 74;
const DASH_PERIOD = 30;

interface LaneProps {
  config: LaneConfig;
  car: CarState;
  scenario: Scenario;
  time: number;
  braking: boolean;
}

function screenY(worldY: number, carY: number) {
  return CAR_FRONT_Y - (worldY - carY) * PIXELS_PER_METRE;
}

function starPoints(cx: number, cy: number, outer: number, inner: number, spikes: number) {
  const points: string[] = [];
  for (let i = 0; i < spikes * 2; i++) {
    const radius = i % 2 === 0 ? outer : inner;
    const angle = (Math.PI * i) / spikes;
    points.push(`${(cx + radius * Math.cos(angle)).toFixed(1)},${(cy + radius * Math.sin(angle)).toFixed(1)}`);
  }
  return points.join(" ");
}

function RoadSurface({ carY }: { carY: number }) {
  const scroll = -((carY * PIXELS_PER_METRE) % DASH_PERIOD);
  return (
    <>
      <rect width={LANE_WIDTH} height={VIEW_HEIGHT} className="fill-b-asphalt" />
      <rect x={KERB_X} width={LANE_WIDTH - KERB_X} height={VIEW_HEIGHT} className="fill-b-wash" />
      <line
        x1={6}
        x2={6}
        y2={VIEW_HEIGHT}
        strokeWidth={2}
        strokeDasharray="16 14"
        strokeDashoffset={scroll}
        className="stroke-b-paper"
      />
      <line
        x1={KERB_X + 5}
        x2={KERB_X + 5}
        y2={VIEW_HEIGHT}
        strokeWidth={4}
        strokeDasharray="10 20"
        strokeDashoffset={scroll}
        className="stroke-b-rule"
      />
    </>
  );
}

function ParkedVan({ y }: { y: number }) {
  return (
    <g>
      <rect x={VAN_X} y={y} width={VAN_WIDTH} height={VAN_LENGTH} rx={3} className="fill-b-paper" />
      <rect x={VAN_X + 3} y={y + 2} width={VAN_WIDTH - 6} height={8} rx={2} className="fill-b-ink-3" />
    </g>
  );
}

function Pedestrian({ y, progress }: { y: number; progress: number }) {
  const eased = progress * (2 - progress);
  const x = PEDESTRIAN_START_X + (CAR_CENTRE_X - PEDESTRIAN_START_X) * eased;
  return (
    <g>
      <ellipse cx={x} cy={y} rx={11} ry={6} className="fill-b-paper" />
      <circle cx={x} cy={y} r={5} className="fill-b-gold-deep" />
    </g>
  );
}

function Car({ y, braking, carClass }: { y: number; braking: boolean; carClass: string }) {
  const x = CAR_CENTRE_X - CAR_WIDTH / 2;
  const rear = y + CAR_LENGTH;
  return (
    <g>
      <rect x={x} y={y} width={CAR_WIDTH} height={CAR_LENGTH} rx={6} className={carClass} />
      <rect x={x + 3} y={y + 8} width={CAR_WIDTH - 6} height={9} rx={2} className="fill-b-blue-deep" />
      <rect x={x + 3} y={rear - 12} width={CAR_WIDTH - 6} height={6} rx={2} className="fill-b-blue-deep" />
      {braking && (
        <>
          <rect x={x + 2} y={rear - 3} width={7} height={3} className="fill-b-crash" />
          <rect x={x + CAR_WIDTH - 9} y={rear - 3} width={7} height={3} className="fill-b-crash" />
        </>
      )}
    </g>
  );
}

function StopLine({ y }: { y: number }) {
  return <rect x={0} y={y - 3} width={KERB_X} height={6} className="fill-b-gold" />;
}

export function Lane({ config, car, scenario, time, braking }: LaneProps) {
  const pedestrianY = screenY(scenario.pedestrianY, car.y);
  const vanY = screenY(scenario.pedestrianY - 0.5, car.y);
  const appeared = pedestrianHasAppeared(time, scenario);
  return (
    <svg viewBox={`0 0 ${LANE_WIDTH} ${VIEW_HEIGHT}`} className="block h-auto w-full" aria-hidden="true">
      <RoadSurface carY={car.y} />
      <ParkedVan y={vanY} />
      <Car y={CAR_FRONT_Y} braking={braking} carClass={config.carClass} />
      {car.outcome === "stopped" && <StopLine y={CAR_FRONT_Y - 4} />}
      {car.outcome === "hit" && (
        <polygon points={starPoints(CAR_CENTRE_X, CAR_FRONT_Y, 13, 6, 7)} className="fill-b-crash" />
      )}
      {appeared && <Pedestrian y={pedestrianY} progress={stepOutProgress(time, scenario)} />}
    </svg>
  );
}
