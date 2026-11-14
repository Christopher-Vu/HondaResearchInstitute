export type InventoryAxis = {
  axis_id: string;
  name: string;
  description: string;
  rank: number;
  axis_size: number;
  share_of_failures: number;
  causal: { verdict?: "causal" | "correlational_only" | "untested" };
  supporting_episodes: {
    episode_id: string;
    activation: number;
    timesteps: [number, number];
  }[];
};

export type GapSummary = {
  axis_id: string | null;
  best_jaccard: number;
  axis_size: number;
  share_of_failures: number;
  recovers: boolean;
};

export type EvaluationReport = {
  layer: number;
  corpus: { rollouts: number; failures: number };
  methods: Record<string, {
    family: string;
    kind: string;
    counts: boolean;
    score: { n_axes: number };
    axes?: InventoryAxis[];
    gaps: Record<string, GapSummary>;
  }>;
};

function record(value: unknown, path: string): Record<string, unknown> {
  if (value === null || typeof value !== "object" || Array.isArray(value)) {
    throw new Error(`Invalid evaluation report: ${path} must be an object.`);
  }
  return value as Record<string, unknown>;
}

function requireValue(valid: boolean, path: string): asserts valid {
  if (!valid) throw new Error(`Invalid evaluation report: invalid ${path}.`);
}

const count = (value: unknown): value is number =>
  typeof value === "number" && Number.isSafeInteger(value) && value >= 0;
const fraction = (value: unknown): value is number =>
  typeof value === "number" && Number.isFinite(value) && value >= 0 && value <= 1;

function validateInventory(value: unknown, path: string, nAxes: number, rollouts: number): void {
  requireValue(Array.isArray(value) && value.length === nAxes, path);
  const ids = new Set<string>();
  for (const [index, item] of value.entries()) {
    const axisPath = `${path}[${index}]`;
    const axis = record(item, axisPath);
    requireValue(typeof axis.axis_id === "string" && !ids.has(axis.axis_id), `${axisPath}.axis_id`);
    ids.add(axis.axis_id);
    requireValue(typeof axis.name === "string", `${axisPath}.name`);
    requireValue(typeof axis.description === "string", `${axisPath}.description`);
    requireValue(count(axis.rank) && axis.rank > 0, `${axisPath}.rank`);
    requireValue(count(axis.axis_size) && axis.axis_size <= rollouts, `${axisPath}.axis_size`);
    requireValue(fraction(axis.share_of_failures), `${axisPath}.share_of_failures`);
    const causal = record(axis.causal, `${axisPath}.causal`);
    requireValue(causal.verdict === undefined ||
      ["causal", "correlational_only", "untested"].includes(causal.verdict as string), `${axisPath}.causal.verdict`);
    requireValue(Array.isArray(axis.supporting_episodes) &&
      axis.supporting_episodes.length === axis.axis_size, `${axisPath}.supporting_episodes`);
    const episodes = new Set<string>();
    for (const [epIndex, item] of axis.supporting_episodes.entries()) {
      const epPath = `${axisPath}.supporting_episodes[${epIndex}]`;
      const episode = record(item, epPath);
      requireValue(typeof episode.episode_id === "string" && !episodes.has(episode.episode_id), `${epPath}.episode_id`);
      episodes.add(episode.episode_id);
      requireValue(typeof episode.activation === "number" && Number.isFinite(episode.activation), `${epPath}.activation`);
      const steps = episode.timesteps;
      requireValue(Array.isArray(steps) && steps.length === 2 && steps.every(count) && steps[0] <= steps[1], `${epPath}.timesteps`);
    }
  }
}

/** Validate every field used by the UI; tolerate extra producer metadata. */
export function parseEvaluationReport(value: unknown): EvaluationReport {
  const report = record(value, "report");
  requireValue(count(report.layer), "layer");
  const corpus = record(report.corpus, "corpus");
  requireValue(count(corpus.rollouts), "corpus.rollouts");
  requireValue(count(corpus.failures) && corpus.failures <= corpus.rollouts, "corpus.failures");
  const methods = record(report.methods, "methods");
  for (const [label, value] of Object.entries(methods)) {
    const path = `methods.${label}`;
    const method = record(value, path);
    requireValue(typeof method.family === "string", `${path}.family`);
    requireValue(typeof method.kind === "string", `${path}.kind`);
    requireValue(typeof method.counts === "boolean", `${path}.counts`);
    const score = record(method.score, `${path}.score`);
    requireValue(count(score.n_axes), `${path}.score.n_axes`);
    if ("axes" in method) validateInventory(method.axes, `${path}.axes`, score.n_axes, corpus.rollouts);
    for (const [gap, value] of Object.entries(record(method.gaps, `${path}.gaps`))) {
      const rowPath = `${path}.gaps.${gap}`;
      const row = record(value, rowPath);
      requireValue(row.axis_id === null || typeof row.axis_id === "string", `${rowPath}.axis_id`);
      requireValue(count(row.axis_size) && row.axis_size <= corpus.rollouts, `${rowPath}.axis_size`);
      requireValue(fraction(row.best_jaccard), `${rowPath}.best_jaccard`);
      requireValue(fraction(row.share_of_failures), `${rowPath}.share_of_failures`);
      requireValue(typeof row.recovers === "boolean", `${rowPath}.recovers`);
    }
  }
  return value as EvaluationReport;
}
