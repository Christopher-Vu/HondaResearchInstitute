#!/usr/bin/env python3
"""H25: turn the grouping runs' opaque-id groups into route-id axes for score_sets.py.

    python docs/research/experiments/h25-caption-cluster/to_axes.py groups.json MAPPING.json --output axes.json

`groups.json` is the workflow's return value: {pool: {"captions": [...], "runs": [{"run": r, "modes": [{"name",
"members": [opaque id]}]}]}}; `--pool` picks one. A run whose agent failed has no modes and scores as no axes.
Modes are ranked by size, largest first, and the top BUDGET become axes, as B3 ranks its clusters. An id the mapping
does not know stops the run, because it means a grouping agent invented or garbled one.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

BUDGET = 10


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("groups", type=Path)
    parser.add_argument("mapping", type=Path)
    parser.add_argument("--pool", required=True)
    parser.add_argument("--method", default="H25_caption_cluster")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    mapping = json.loads(args.mapping.read_text())["mapping"]
    runs = []
    for run in json.loads(args.groups.read_text())[args.pool]["runs"]:
        unknown = {m for mode in run["modes"] for m in mode["members"]} - mapping.keys()
        if unknown:
            raise ValueError(f"run {run['run']} names ids not in the mapping: {sorted(unknown)[:5]}")
        ids = [m for mode in run["modes"] for m in mode["members"]]
        if len(ids) != len(set(ids)):
            raise ValueError(f"run {run['run']} places a route in two modes")
        modes = sorted(run["modes"], key=lambda mode: (-len(mode["members"]), mode["name"]))[:BUDGET]
        runs.append({"run": run["run"], "names": [mode["name"] for mode in modes],
                     "axes": [sorted({mapping[m]["route"] for m in mode["members"]}) for mode in modes if mode["members"]]})
    args.output.write_text(json.dumps({args.method: runs}, indent=1) + "\n")
    print(f"{len(runs)} runs, axes per run {[len(r['axes']) for r in runs]}")


if __name__ == "__main__":
    main()
