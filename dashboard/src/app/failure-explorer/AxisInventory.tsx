"use client";

import { useState } from "react";
import type { InventoryAxis } from "./evaluation-report";

export default function AxisInventory({ axes }: { axes?: InventoryAxis[] }) {
  const [search, setSearch] = useState("");
  const query = search.trim().toLowerCase();
  const filtered = axes?.filter((axis) =>
    [axis.axis_id, axis.name, axis.description].some((text) => text.toLowerCase().includes(query))
  ) ?? [];

  return (
    <div className="mt-6 border-t border-gray-200 pt-6">
      <h3 className="text-lg font-semibold">Emitted axis inventory</h3>
      <p className="mt-2 text-sm text-gray-500">
        All axes emitted by this method/run, in the report’s order, including axes
        that are not the best match for any gap. Names and descriptions come from
        the method; they are not verified explanations of failure.
      </p>
      {axes === undefined ? (
        <p className="mt-4 text-sm text-gray-500">
          This older report does not contain an axis inventory. Its gap summaries
          remain available above. Missing axes cannot be reconstructed from those summaries.
        </p>
      ) : axes.length === 0 ? (
        <p className="mt-4 text-sm text-gray-500">This method/run emitted no axes.</p>
      ) : (
        <>
          <label className="mt-4 block text-sm">
            Search emitted axes
            <input type="search" value={search} onChange={(event) => setSearch(event.target.value)}
              className="mt-2 block w-full rounded-lg border border-gray-300 px-3 py-2" />
          </label>
          <p className="mt-3 text-sm text-gray-500" role="status">Showing {filtered.length} of {axes.length} axes</p>
          <ul className="mt-4 space-y-4">
            {filtered.map((axis) => (
              <li key={axis.axis_id} className="rounded-lg border border-gray-200 p-4">
                <h4 className="font-medium">{axis.rank}. {axis.name} ({axis.axis_id})</h4>
                <p className="mt-1 text-sm text-gray-600">{axis.description}</p>
                <p className="mt-3 text-sm text-gray-500">
                  {axis.axis_size} associated rollouts · {(axis.share_of_failures * 100).toFixed(1)}% of failures
                  {" · "}Causal verdict: {axis.causal.verdict ?? "untested"}
                </p>
                <details className="mt-3 text-sm">
                  <summary className="cursor-pointer">Supporting episodes ({axis.supporting_episodes.length})</summary>
                  <p className="mt-2 text-xs text-gray-500">
                    Episode identifiers and timestep windows recorded by the method.
                    A 0–0 window may be a method placeholder, not a localized failure.
                  </p>
                  <ul className="mt-2 max-h-48 space-y-1 overflow-y-auto">
                    {axis.supporting_episodes.map((episode) => (
                      <li key={episode.episode_id}>
                        {episode.episode_id} · timesteps {episode.timesteps[0]}–{episode.timesteps[1]}
                      </li>
                    ))}
                  </ul>
                </details>
              </li>
            ))}
          </ul>
          {filtered.length === 0 && <p className="py-4 text-sm text-gray-500">No emitted axes match your search.</p>}
        </>
      )}
    </div>
  );
}
