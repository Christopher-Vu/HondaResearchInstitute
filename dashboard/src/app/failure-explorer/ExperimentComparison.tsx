"use client";

import { useMemo, useState } from "react";
import h18 from "./h18_result.json";
import h19 from "./h19_result.json";
import h20 from "./h20_result.json";

type Score = { best: number; median: number; at_or_above_0_5: number; dictionaries: number };
type Metric = "median" | "best";
type Entry = { experiment: string; preprocessing: string; method: string; gap: string; score: Score };
const methodNames: Record<string, string> = { M1_raw: "M1 · contrastive", M1_capped: "M1 · capped", B7_pool: "B7 · pool baseline" };
const gapNames: Record<string, string> = { P4_camera_occlusion: "P4 · Camera occlusion", P7_camera_freeze: "P7 · Camera freeze", P8_camera_latency: "P8 · Camera latency", P19_wide_invading_turn: "P19 · Wide invading turn" };
const preprocessingNames: Record<string, string> = { plain: "Original", centre: "Mean removed", vision: "Vision residualized", shuffle: "Shuffled control", "top-variance": "Variance-matched control" };

function isScore(value: unknown): value is Score {
  if (!value || typeof value !== "object") return false;
  const s = value as Record<string, unknown>;
  return ["best", "median"].every(k => typeof s[k] === "number" && Number.isFinite(s[k]) && (s[k] as number) >= 0 && (s[k] as number) <= 1)
    && ["at_or_above_0_5", "dictionaries"].every(k => typeof s[k] === "number" && Number.isInteger(s[k]) && (s[k] as number) >= 0)
    && (s.at_or_above_0_5 as number) <= (s.dictionaries as number);
}

function buildEntries(): Entry[] {
  const entries: Entry[] = [];
  for (const [preprocessing, scores] of Object.entries(h20.table)) {
    for (const [key, value] of Object.entries(scores)) {
      const split = key.indexOf("|");
      if (split < 0 || !isScore(value)) continue;
      entries.push({ experiment: "H20", preprocessing, method: key.slice(0, split), gap: key.slice(split + 1), score: value });
    }
  }
  for (const [preprocessing, control] of Object.entries(h18.controls)) {
    for (const [method, gaps] of Object.entries(control.scores)) {
      for (const [gap, value] of Object.entries(gaps)) {
        if (isScore(value)) entries.push({ experiment: "H18", preprocessing, method, gap, score: value });
      }
    }
  }
  return entries;
}
const entries = buildEntries();
const sourceUrls: Record<string, string> = {
  H18: "https://github.com/Christopher-Vu/HondaResearchInstitute/blob/main/docs/research/data/h18_result.json",
  H19: "https://github.com/Christopher-Vu/HondaResearchInstitute/blob/main/docs/research/data/h19_result.json",
  H20: "https://github.com/Christopher-Vu/HondaResearchInstitute/blob/main/docs/research/data/h20_result.json",
};

export default function ExperimentComparison() {
  const [experiment, setExperiment] = useState("H20");
  const [gap, setGap] = useState("P8_camera_latency");
  const [metric, setMetric] = useState<Metric>("median");
  const [method, setMethod] = useState("All");
  const availableGaps = useMemo(() => Array.from(new Set(entries.filter(e => e.experiment === experiment).map(e => e.gap))), [experiment]);
  const selectedGap = availableGaps.includes(gap) ? gap : availableGaps[0];
  const rows = useMemo(() => entries.filter(e => e.experiment === experiment && e.gap === selectedGap && (method === "All" || e.method === method)), [experiment, selectedGap, method]);
  const options = Array.from(new Set(entries.filter(e => e.experiment === experiment).map(e => e.method)));
  const h19Settings = h19.real as Array<{ axes: number; best_jaccard: Record<string, number> }>;
  const plantedSettings = h19.planted_runs as Array<{ planted_best_jaccard: number }>;
  const h19Max = Math.max(...h19Settings.map(x => x.best_jaccard.P19_wide_invading_turn));

  return (
    <section className="mt-10 rounded-xl border border-gray-200 bg-white p-6" aria-labelledby="experiment-comparison-title">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 id="experiment-comparison-title" className="text-xl font-semibold">Experiment Comparison</h2>
          <p className="mt-2 text-sm text-gray-600">Compare failure-discovery methods and preprocessing on stored research results.</p>
        </div>
        <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-900">DEV ONLY · Not a final verdict</span>
      </div>
      <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <label className="text-sm font-medium">Experiment
          <select className="mt-2 block w-full rounded-lg border border-gray-300 p-2" value={experiment} onChange={e => { setExperiment(e.target.value); setMethod("All"); }}>
            <option value="H18">H18 · Residualization controls</option>
            <option value="H19">H19 · M2 settings sweep</option>
            <option value="H20">H20 · Mean removal</option>
          </select>
        </label>
        {experiment !== "H19" && <>
          <label className="text-sm font-medium">Failure scenario
            <select className="mt-2 block w-full rounded-lg border border-gray-300 p-2" value={selectedGap} onChange={e => setGap(e.target.value)}>
              {availableGaps.map(x => <option key={x} value={x}>{gapNames[x] ?? x}</option>)}
            </select>
          </label>
          <label className="text-sm font-medium">Method
            <select className="mt-2 block w-full rounded-lg border border-gray-300 p-2" value={method} onChange={e => setMethod(e.target.value)}>
              <option value="All">All methods</option>
              {options.map(x => <option key={x} value={x}>{methodNames[x] ?? x}</option>)}
            </select>
          </label>
          <label className="text-sm font-medium">Score
            <select className="mt-2 block w-full rounded-lg border border-gray-300 p-2" value={metric} onChange={e => setMetric(e.target.value as Metric)}>
              <option value="median">Median across dictionaries</option>
              <option value="best">Best axis (key-selected)</option>
            </select>
          </label>
        </>}
      </div>
      {experiment === "H19" ? (
        <div className="mt-7 grid gap-4 md:grid-cols-3">
          <div className="rounded-lg bg-gray-50 p-5"><p className="text-sm text-gray-500">Configurations tested</p><p className="mt-2 text-3xl font-semibold">{h19Settings.length}</p></div>
          <div className="rounded-lg bg-gray-50 p-5"><p className="text-sm text-gray-500">Best P19 overlap</p><p className="mt-2 text-3xl font-semibold">{h19Max.toFixed(3)}</p><p className="text-xs text-gray-500">Selected using known key</p></div>
          <div className="rounded-lg bg-gray-50 p-5"><p className="text-sm text-gray-500">Planted group recovered</p><p className="mt-2 text-3xl font-semibold">{plantedSettings.some(x => x.planted_best_jaccard > 0) ? "Some" : "No"}</p><p className="text-xs text-gray-500">25 planted failures; all tested configurations scored 0</p></div>
          <p className="text-sm text-gray-600 md:col-span-3">M2 did not recover the artificial group. This does not prove the real-world failure patterns are absent.</p>
        </div>
      ) : (
        <>
          <p className="mt-6 text-sm text-gray-600">Higher Jaccard means greater overlap between a discovered axis and the known failure group. Best scores use the answer key to choose an axis and should not be interpreted as blind discovery.</p>
          <div className="mt-5 space-y-5">
            {rows.map(row => <div key={`${row.preprocessing}-${row.method}`}>
              <div className="mb-2 flex flex-wrap items-center justify-between gap-2 text-sm">
                <span className="font-medium">{methodNames[row.method] ?? row.method} <span className="font-normal text-gray-500">· {preprocessingNames[row.preprocessing] ?? row.preprocessing}</span></span>
                <span className="tabular-nums font-semibold">{row.score[metric].toFixed(3)}</span>
              </div>
              <div className="h-3 overflow-hidden rounded-full bg-gray-100" role="img" aria-label={`${methodNames[row.method] ?? row.method}, ${preprocessingNames[row.preprocessing] ?? row.preprocessing}: ${metric} Jaccard ${row.score[metric].toFixed(3)}`}>
                <div className="h-full rounded-full bg-blue-600" style={{ width: `${row.score[metric] * 100}%` }} />
              </div>
              <p className="mt-1 text-xs text-gray-500">{row.score.at_or_above_0_5} of {row.score.dictionaries} dictionaries reached Jaccard ≥ 0.5</p>
            </div>)}
            {rows.length === 0 && <p className="text-sm text-gray-500">No measured scores for this selection.</p>}
          </div>
        </>
      )}
      <div className="mt-7 border-t border-gray-200 pt-4 text-xs text-gray-500">
        <p>Research status: exploratory development measurements. H18 and H20 use different rollout pools; do not interpret cross-experiment differences as controlled effects.</p>
        <a className="mt-2 inline-block font-medium text-blue-700 underline" href={sourceUrls[experiment]} target="_blank" rel="noreferrer">View {experiment} source JSON</a>
      </div>
    </section>
  );
}
