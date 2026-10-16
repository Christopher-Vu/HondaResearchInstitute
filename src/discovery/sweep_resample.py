"""Rank distribution of every layer-site pair under resampling (docs/steps/04-layer-site-ablation.md, Part A2).

    python -m src.discovery.sweep_resample SHARD_DIR --output OUT.json --start 0 --count 10

Resample i (seed 1000 + i) drops a random fifth of the base routes, as layer_sweep's stability check does,
reruns the whole sweep, and records every pair's combined and family ranks. Tasks write disjoint index
ranges, so an array of jobs covers 100 resamples; `--merge` combines their files into per-pair summaries.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

from .layer_sweep import base_routes, run_sweep

SEED = 1000
DROP_FRACTION = 0.2


def resample(shard_dir: Path, index: int) -> dict[str, Any]:
    bases = base_routes(shard_dir)
    rng = np.random.default_rng(SEED + index)
    dropped = rng.choice(bases, size=round(DROP_FRACTION * len(bases)), replace=False)
    report = run_sweep(shard_dir, exclude_bases=frozenset(str(base) for base in dropped))
    return {"index": index, "dropped": len(dropped),
            "pairs": [{"site": row["site"], "layer": row["layer"], "combined_rank": row["combined_rank"],
                       "family_ranks": row["family_ranks"]} for row in report["pairs"]]}


def merge(files: list[Path]) -> dict[str, Any]:
    runs = [run for path in files for run in json.loads(path.read_text())["resamples"]]
    by_pair: dict[tuple[str, int], dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for run in runs:
        ranked = sorted((p for p in run["pairs"] if p["combined_rank"] is not None),
                        key=lambda p: p["combined_rank"])
        for position, pair in enumerate(ranked, start=1):
            entry = by_pair[(pair["site"], pair["layer"])]
            entry["combined"].append(pair["combined_rank"])
            entry["position"].append(position)
            for family, rank in pair["family_ranks"].items():
                entry[family].append(rank)
    rows = []
    for (site, layer), entry in by_pair.items():
        position = np.array(entry["position"])
        row = {"site": site, "layer": layer, "resamples": len(position),
               "median_position": float(np.median(position)),
               "position_p5_p95": [float(np.percentile(position, 5)), float(np.percentile(position, 95))],
               "top2_share": float(np.mean(position <= 2)), "top3_share": float(np.mean(position <= 3))}
        for family, ranks in entry.items():
            if family not in ("combined", "position"):
                row[f"median_{family}_rank"] = float(np.median(ranks))
        rows.append(row)
    rows.sort(key=lambda row: (row["median_position"], -row["top3_share"]))
    return {"resamples": len(runs), "pairs": rows}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("shards", type=Path, nargs="?")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--count", type=int, default=10)
    parser.add_argument("--merge", type=Path, nargs="+", help="resample files to combine instead of running")
    args = parser.parse_args()
    if args.merge:
        result = merge(args.merge)
    else:
        result = {"shards": str(args.shards),
                  "resamples": [resample(args.shards, i) for i in range(args.start, args.start + args.count)]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=1) + "\n")


if __name__ == "__main__":
    main()
