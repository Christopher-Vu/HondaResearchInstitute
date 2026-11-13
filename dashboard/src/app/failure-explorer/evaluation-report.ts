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
