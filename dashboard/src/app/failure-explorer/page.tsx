"use client";
import AxisImporter from "./AxisImporter";
import { useMemo, useState } from "react";

type FailureAxis = {
  id: string;
  name: string;
  method: string;
  failures: number;
  stability: number;
  description: string;
};

// DEMONSTRATION DATA ONLY — not actual experiment results.
const axes: FailureAxis[] = [
  {
    id: "AX-001",
    name: "Camera Occlusion",
    method: "Contrastive",
    failures: 43,
    stability: 0.92,
    description: "Failures associated with reduced camera visibility.",
  },
  {
    id: "AX-002",
    name: "Traffic Light Confusion",
    method: "SAE",
    failures: 18,
    stability: 0.78,
    description: "Potential difficulty interpreting traffic signals.",
  },
  {
    id: "AX-003",
    name: "Pedestrian Detection",
    method: "Probe Residual",
    failures: 12,
    stability: 0.85,
    description: "Potential failures involving pedestrian detection.",
  },
  {
    id: "AX-004",
    name: "Visual Distraction",
    method: "Contrastive",
    failures: 9,
    stability: 0.63,
    description: "Potential sensitivity to irrelevant visual features.",
  },
];
import gapPilotData from "../../data/gap-pilots.json";
import layerSweepData from "../../data/layer-sweep.json";
export default function FailureExplorer() {
  const [search, setSearch] = useState("");
  const [method, setMethod] = useState("All");

  const methods = ["All", ...new Set(axes.map((axis) => axis.method))];

  const filteredAxes = useMemo(
    () =>
      axes.filter((axis) => {
        const matchesSearch =
          axis.name.toLowerCase().includes(search.toLowerCase()) ||
          axis.description.toLowerCase().includes(search.toLowerCase());

        const matchesMethod =
          method === "All" || axis.method === method;

        return matchesSearch && matchesMethod;
      }),
    [search, method]
  );

  const averageStability =
    axes.reduce((sum, axis) => sum + axis.stability, 0) / axes.length;

  return (
    <main className="min-h-screen bg-gray-50 px-8 py-12 text-gray-900">
      <div className="mx-auto max-w-7xl">
        <a href="/" className="text-sm text-gray-500 hover:text-gray-900">
          ← Back to Dashboard
        </a>

        <div className="mt-8">
          <h1 className="text-4xl font-semibold">
            Failure-Axis Explorer
          </h1>
          <p className="mt-3 text-gray-600">
            Explore discovered failure patterns in SimLingo experiments.
          </p>

          <div className="mt-5 inline-block rounded-full bg-amber-100 px-4 py-2 text-sm font-medium text-amber-900">
            Demo data — not validated research findings
          </div>
        </div>

        <section className="mt-10 grid gap-5 md:grid-cols-3">
          {[
            { label: "Failure Axes", value: axes.length },
            {
              label: "Discovery Methods",
              value: methods.length - 1,
            },
            {
              label: "Average Stability",
              value: `${(averageStability * 100).toFixed(1)}%`,
            },
          ].map((card) => (
            <div
              key={card.label}
              className="rounded-xl border border-gray-200 bg-white p-6"
            >
              <p className="text-sm text-gray-500">{card.label}</p>
              <p className="mt-3 text-3xl font-semibold">{card.value}</p>
            </div>
          ))}
        </section>

        <section className="mt-10 rounded-xl border border-gray-200 bg-white p-6">
          <div className="flex flex-col justify-between gap-4 md:flex-row">
            <div>
              <h2 className="text-xl font-semibold">Discovery Results</h2>
              <p className="mt-1 text-sm text-gray-500">
                Compare failure patterns across discovery methods.
              </p>
            </div>

            <div className="flex flex-wrap gap-3">
              <input
                type="search"
                placeholder="Search failure axes..."
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                className="rounded-lg border border-gray-300 px-4 py-2 text-sm"
              />

              <select
                value={method}
                onChange={(event) => setMethod(event.target.value)}
                className="rounded-lg border border-gray-300 px-4 py-2 text-sm"
              >
                {methods.map((item) => (
                  <option key={item} value={item}>
                    {item}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="mt-6 overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="border-b bg-gray-50 text-gray-500">
                <tr>
                  <th className="px-4 py-4">Failure Axis</th>
                  <th className="px-4 py-4">Discovery Method</th>
                  <th className="px-4 py-4">Associated Failures</th>
                  <th className="px-4 py-4">Stability</th>
                </tr>
              </thead>

              <tbody>
                {filteredAxes.map((axis) => (
                  <tr key={axis.id} className="border-b border-gray-100">
                    <td className="px-4 py-5">
                      <p className="font-medium">{axis.name}</p>
                      <p className="mt-1 text-xs text-gray-500">
                        {axis.description}
                      </p>
                    </td>

                    <td className="px-4 py-5">{axis.method}</td>

                    <td className="px-4 py-5">{axis.failures}</td>

                    <td className="px-4 py-5">
                      <div className="flex items-center gap-3">
                        <div className="h-2 w-24 rounded-full bg-gray-200">
                          <div
                            className="h-2 rounded-full bg-blue-600"
                            style={{ width: `${axis.stability * 100}%` }}
                          />
                        </div>
                        <span>
                          {(axis.stability * 100).toFixed(0)}%
                        </span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {filteredAxes.length === 0 && (
              <p className="py-10 text-center text-gray-500">
                No failure axes match your filters.
              </p>
            )}
          </div>
        </section>
        <section className="mt-10 rounded-xl border border-gray-200 bg-white p-6">
          <h2 className="text-xl font-semibold">Measured Gap Efficacy</h2>
          <p className="mt-2 text-sm text-gray-500">
            Actual paired-route experiment results. These are tested scenarios,
            not necessarily discovered failure axes.
          </p>

          <div className="mt-6 grid gap-4 md:grid-cols-2">
            {gapPilotData.gaps.map((gap) => (
              <div
                key={gap.id}
                className="rounded-lg border border-gray-200 p-5"
              >
                <div className="flex items-center justify-between">
                  <h3 className="font-semibold">
                    {gap.id}: {gap.name}
                  </h3>
                  <span
                    className={
                      gap.passed
                        ? "rounded-full bg-green-100 px-3 py-1 text-xs text-green-800"
                        : "rounded-full bg-gray-100 px-3 py-1 text-xs text-gray-700"
                    }
                  >
                    {gap.passed ? "Passed" : "Did not pass"}
                  </span>
                </div>

                <p className="mt-2 text-sm text-gray-500">{gap.change}</p>
                <p className="mt-2 text-xs text-gray-500">{gap.stage}</p>

                <div className="mt-5 grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-xs text-gray-500">{gap.with.label}</p>
                    <p className="mt-1 text-2xl font-semibold">
                      {gap.with.failed}/{gap.with.routes}
                    </p>
                    <p className="text-xs text-gray-500">Failed routes</p>
                  </div>

                  <div>
                    <p className="text-xs text-gray-500">{gap.without.label}</p>
                    <p className="mt-1 text-2xl font-semibold">
                      {gap.without.failed}/{gap.without.routes}
                    </p>
                    <p className="text-xs text-gray-500">Failed routes</p>
                  </div>
                </div>
              </div>
            ))}
          </div>

          <p className="mt-5 text-xs text-gray-500">
            Source: {gapPilotData.source}
          </p>
        </section>
        <section className="mt-10 rounded-xl border border-gray-200 bg-white p-6">
  <div className="flex flex-wrap items-start justify-between gap-4">
    <div>
      <h2 className="text-xl font-semibold">Layer Sweep Analysis</h2>
      <p className="mt-2 text-sm text-gray-500">
        Failure-prediction AUROC across SimLingo transformer layers.
      </p>
    </div>

    <span className="rounded-full bg-blue-50 px-3 py-1 text-sm text-blue-700">
      Logged layer: {layerSweepData.logged_layer}
    </span>
  </div>

  <div className="mt-6 grid gap-4 sm:grid-cols-3">
    <div className="rounded-lg bg-gray-50 p-4">
      <p className="text-sm text-gray-500">Evaluated routes</p>
      <p className="mt-2 text-3xl font-semibold">{layerSweepData.routes}</p>
    </div>

    <div className="rounded-lg bg-gray-50 p-4">
      <p className="text-sm text-gray-500">Failing routes</p>
      <p className="mt-2 text-3xl font-semibold">{layerSweepData.failing}</p>
    </div>

    <div className="rounded-lg bg-gray-50 p-4">
      <p className="text-sm text-gray-500">Per-token layers</p>
      <p className="mt-2 text-3xl font-semibold">
        {layerSweepData.per_token_layers.join(", ")}
      </p>
    </div>
  </div>

  <div className="mt-8 space-y-3">
    {layerSweepData.layers.map((layer) => (
      <div key={layer.layer} className="flex items-center gap-4">
        <span className="w-16 shrink-0 text-sm text-gray-600">
          Layer {layer.layer}
        </span>

        <div className="h-4 flex-1 overflow-hidden rounded-full bg-gray-100">
          <div
            className={`h-full rounded-full ${
              layer.layer === layerSweepData.logged_layer
                ? "bg-blue-600"
                : "bg-gray-400"
            }`}
            style={{
              width: `${layer.failure_auroc * 100}%`,
            }}
          />
        </div>

        <span className="w-14 text-right text-sm font-medium">
          {layer.failure_auroc.toFixed(3)}
        </span>
      </div>
    ))}
  </div>

  <p className="mt-6 text-xs text-gray-500">
    Source: {layerSweepData.source}
  </p>
  </section>
  <AxisImporter />
      </div>
    </main>
  );
}