import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { parseEvaluationReport } from "../src/app/failure-explorer/evaluation-report.ts";

const fixture = () => JSON.parse(readFileSync(new URL("../../docs/research/data/h12_layer10_plain.json", import.meta.url), "utf8"));

test("accepts a real dev_eval report without dropping methods or changing scores", () => {
  const report = fixture();
  assert.equal(parseEvaluationReport(report), report);
  assert.equal(Object.keys(report.methods).length > 3, true);
  assert.equal(report.methods[Object.keys(report.methods)[0]].gaps.P19_wide_invading_turn.best_jaccard, 0.6136363636363636);
});

test("preserves excluded runs and reports with no axes", () => {
  const report = fixture();
  const method = Object.values(report.methods)[0];
  method.counts = false;
  method.score.n_axes = 0;
  method.gaps = { empty: { axis_id: null, axis_size: 0, best_jaccard: 0, share_of_failures: 0, recovers: false } };
  assert.equal(parseEvaluationReport(report).methods[Object.keys(report.methods)[0]].counts, false);
  assert.equal(method.gaps.empty.axis_id, null);
});

test("allows empty method and gap maps", () => {
  assert.deepEqual(parseEvaluationReport({ layer: 10, corpus: { rollouts: 0, failures: 0 }, methods: {} }).methods, {});
  const report = fixture();
  Object.values(report.methods)[0].gaps = {};
  assert.doesNotThrow(() => parseEvaluationReport(report));
});

for (const [name, mutate, path] of [
  ["null method", (r, key) => r.methods[key] = null, "methods."],
  ["missing gaps", (r, key) => delete r.methods[key].gaps, ".gaps"],
  ["object axis ID", (r, key, gap) => r.methods[key].gaps[gap].axis_id = {}, "axis_id"],
  ["string score", (r, key, gap) => r.methods[key].gaps[gap].best_jaccard = "0.5", "best_jaccard"],
  ["out of range score", (r, key, gap) => r.methods[key].gaps[gap].best_jaccard = 1.1, "best_jaccard"],
  ["nonfinite share", (r, key, gap) => r.methods[key].gaps[gap].share_of_failures = Infinity, "share_of_failures"],
  ["negative axis size", (r, key, gap) => r.methods[key].gaps[gap].axis_size = -1, "axis_size"],
  ["fractional count", (r, key) => r.methods[key].score.n_axes = 1.5, "n_axes"],
  ["missing eligibility", (r, key) => delete r.methods[key].counts, "counts"],
  ["invalid failure count", (r) => r.corpus.failures = r.corpus.rollouts + 1, "corpus.failures"],
]) {
  test(`rejects ${name} before rendering and identifies the field`, () => {
    const report = fixture();
    const key = Object.keys(report.methods)[0];
    mutate(report, key, Object.keys(report.methods[key].gaps)[0]);
    assert.throws(() => parseEvaluationReport(report), (err) => err.message.includes(path));
  });
}

test("rejects null, arrays, and obsolete runs reports with actionable errors", () => {
  for (const input of [null, [], { runs: [] }, { layer: 10, corpus: [] }]) {
    assert.throws(() => parseEvaluationReport(input), /Invalid evaluation report:/);
  }
});

const inventoryFixture = () => JSON.parse(readFileSync(new URL("./fixtures/dev-eval-inventory.json", import.meta.url), "utf8"));

test("accepts the Python-produced synthetic inventory without filtering or reordering axes", () => {
  const report = inventoryFixture();
  assert.equal(parseEvaluationReport(report), report);
  assert.deepEqual(report.methods.synthetic_method.axes.map((axis) => axis.axis_id), ["synthetic-a", "synthetic-b"]);
  assert.equal(report.methods.synthetic_method.axes[1].supporting_episodes[0].timesteps[1], 20);
  assert.deepEqual(report.methods.synthetic_method.gaps, {});
});

test("distinguishes an older missing inventory from an empty exported inventory", () => {
  const old = fixture();
  assert.equal(Object.values(parseEvaluationReport(old).methods)[0].axes, undefined);
  const report = inventoryFixture();
  report.methods.synthetic_method.axes = [];
  report.methods.synthetic_method.score.n_axes = 0;
  assert.deepEqual(parseEvaluationReport(report).methods.synthetic_method.axes, []);
});

for (const [name, mutate, path] of [
  ["null inventory", (m) => m.axes = null, ".axes"],
  ["truncated inventory", (m) => m.axes.pop(), ".axes"],
  ["duplicate axis IDs", (m) => m.axes[1].axis_id = m.axes[0].axis_id, "axis_id"],
  ["invalid rank", (m) => m.axes[0].rank = 0, "rank"],
  ["invalid description", (m) => m.axes[0].description = {}, "description"],
  ["nonfinite failure share", (m) => m.axes[0].share_of_failures = NaN, "share_of_failures"],
  ["invalid causal verdict", (m) => m.axes[0].causal.verdict = "proven", "causal.verdict"],
  ["missing episodes", (m) => delete m.axes[0].supporting_episodes, "supporting_episodes"],
  ["support count mismatch", (m) => m.axes[0].axis_size = 2, "supporting_episodes"],
  ["duplicate episode IDs", (m) => { m.axes[0].axis_size = 2; m.axes[0].supporting_episodes.push(m.axes[0].supporting_episodes[0]); }, "episode_id"],
  ["nonfinite activation", (m) => m.axes[0].supporting_episodes[0].activation = Infinity, "activation"],
  ["reversed timestep window", (m) => m.axes[0].supporting_episodes[0].timesteps = [20, 10], "timesteps"],
  ["fractional timestep", (m) => m.axes[0].supporting_episodes[0].timesteps = [0, 1.5], "timesteps"],
]) {
  test(`rejects ${name} in an inventory with a field-specific error`, () => {
    const report = inventoryFixture();
    mutate(report.methods.synthetic_method);
    assert.throws(() => parseEvaluationReport(report), (err) => err.message.includes(path));
  });
}
