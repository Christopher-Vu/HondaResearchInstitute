// Shapes of docs/steps/progress.yaml and the measured blocks of the step configs.

export type Check = { text: string; done: boolean };

export type Step = {
  id: number;
  title: string;
  source?: string;
  started?: boolean;
  checks: Check[];
};

export type Spread = { mean: number; sd: number };

export type Ability = "overtaking" | "merging" | "emergency_brake" | "give_way" | "traffic_signs";

export type Progress = {
  updated: string;
  current: number;
  steps: Step[];
  benchmark: {
    bar_driving_score: number;
    paper: {
      driving_score: Spread;
      success_rate: Spread;
      ability_success_rate: Record<Ability, number>;
    };
  };
  compute: {
    allowance_su: number;
    window: [string, string];
    program_used_su: number;
    program_used_as_of: string;
    planned: { item: string; su: [number, number] }[];
  };
};

export type Step1Measure = {
  wall_clock_seconds: number;
  simulated_seconds: number;
  real_time_factor: number;
  peak_vram_gb: number;
  service_units: number;
};

export type Step2Measure = {
  official_driving_score: number;
  official_success_rate: number;
  ability_success_rate: Record<Ability | "mean", number>;
  simulated_seconds: number;
  gpu_hours: number;
  service_units: number;
  ability_job_service_units: number;
};

export type Update = {
  sha: string;
  url: string;
  message: string;
  author: string;
  authorUrl: string;
  avatar: string;
  branch: string;
  time: string;
};

export type RouteOutcome = "passed" | "failed" | "skipped";

export type Route = {
  id: string;
  town: string;
  scenario: string;
  ability: string;
  outcome: RouteOutcome;
  stalled: boolean;
  score: number | null;
  stillSeconds: number;
};
