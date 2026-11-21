#!/usr/bin/env python3
"""Per-axis source attribution of the pooled exploratory j rows on H21b. Diagnostic, not a try (230 tried).

    PYTHONPATH=src /opt/miniconda3/bin/python results/h21/attribution/attribute.py

Exploratory, dev, H21b only; never part of the UniAD read. Reads each row's pooled axes and the sources that
pool_axes.py recorded in it, replays pool_axes.py's round-robin to tag every kept axis with its source, and scores
with sprint_score.py's own read_method, best and mean_best. Point values only, no bootstrap.
"""
from __future__ import annotations

import importlib.util
import json
from itertools import zip_longest
from pathlib import Path

from harness.scoring import jaccard
from harness.scoring_run import load_pool

HERE = Path(__file__).parent
SPEC = importlib.util.spec_from_file_location(
    "sprint_score", Path("docs/research/experiments/f2d-dev-simlingo/sprint_score.py"))
sprint_score = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sprint_score)

MANIFEST = Path("results/h21/j18/manifest-pair-fixed.json")
ROUTES = Path("results/h21/h21b/routes.jsonl")
GAPS = ["F2D_CustomObstacles", "F2D_Wall", "F2D_PedestriansOnRoad"]
SHARED = "route-L8"
ROWS = {
    "m23": ("results/h21/h21b/axes/m23.json", "results/h21/h21b/report-m23.json"),
    "j16+route": ("results/h21/j16/axes/j16+route.json", "results/h21/j16/report-j16+route.json"),
    "j17+route": ("results/h21/j16/axes/j17+route.json", "results/h21/j16/report-j17+route.json"),
    "j18": ("results/h21/j18/axes/j18.json", "results/h21/j18/report-j18.json"),
    "j19": ("results/h21/j18/axes/j19.json", "results/h21/j18/report-j19.json"),
    "j20": ("results/h21/j20/axes/j20.json", "results/h21/j20/report-j20.json"),
    "j21": ("results/h21/j20/axes/j21.json", "results/h21/j20/report-j21.json"),
    "j22": ("results/h21/j22/axes/j22.json", "results/h21/j22/report-j22.json"),
    "j23": ("results/h21/j22/axes/j23.json", "results/h21/j22/report-j23.json"),
    "j24": ("results/h21/j24/axes/j24.json", "results/h21/j24/report-j24.json"),
    "j25": ("results/h21/j24/axes/j25.json", "results/h21/j24/report-j25.json"),
}


def load_gaps() -> dict[str, set[str]]:
    """The same two lines as sprint_score.main: a gap is the failing routes of its pilot slice."""
    manifest, failed = load_pool([MANIFEST], [ROUTES])
    slices = lambda c: {str(e["id"]) for e in manifest if e["role"] == "pilot_slice" and c in e["practice_gaps"]}
    return {c: {r for r in slices(c) if failed.get(r)} for c in GAPS}


def replay_pool(sources: dict[str, list[set[str]]]) -> list[dict]:
    """pool_axes.py's round-robin, keeping each kept axis's source and its rank there."""
    kept: list[dict] = []
    tagged = [[(label, rank, axis) for rank, axis in enumerate(axes, 1)] for label, axes in sources.items()]
    for layer in zip_longest(*tagged):
        for label, rank, axis in filter(None, layer):
            if len(kept) < 10 and all(jaccard(axis, k["axis"]) < 0.8 for k in kept):
                kept.append({"source": label, "source_rank": rank, "axis": axis})
    return kept


def identical_in(axis: set[str], sources: dict[str, list[set[str]]], own: str) -> list[str]:
    return [f"{label}#{axes.index(axis) + 1}" for label, axes in sources.items() if label != own and axis in axes]


def best_axes(pooled: list[dict], gap: set[str]) -> dict:
    score = sprint_score.best([p["axis"] for p in pooled], gap)
    ties = [i for i, p in enumerate(pooled, 1) if jaccard(gap, p["axis"]) == score]
    return {"score": score, "best_axis_ranks": ties, "best_axis_sources": sorted({pooled[i - 1]["source"] for i in ties})}


def subset_scores(pooled: list[dict], gaps: dict[str, set[str]], labels: list[str]) -> dict:
    out = {}
    for label in labels:
        axes = [p["axis"] for p in pooled if p["source"] == label]
        out[label] = {"axes": len(axes), "per_gap": {c: sprint_score.best(axes, g) for c, g in gaps.items()},
                      "mean_best": sprint_score.mean_best(axes, gaps) if axes else 0.0}
    return out


def attribute(name: str, axes_path: str, report_path: str, gaps: dict[str, set[str]]) -> dict:
    raw = json.loads(Path(axes_path).read_text())
    sources = {Path(s).stem: sprint_score.read_method(s)[1] for s in raw["sources"]}
    scored = sprint_score.read_method(axes_path)[1]
    pooled = replay_pool(sources)
    if [p["axis"] for p in pooled] != scored:
        raise ValueError(f"{name}: replayed pool differs from the scored axes")
    recorded = json.loads(Path(report_path).read_text())["rows"][raw["method"]]["per_gap"]
    per_gap = {c: best_axes(pooled, g) for c, g in gaps.items()}
    if any(per_gap[c]["score"] != recorded[c] for c in gaps):
        raise ValueError(f"{name}: per-gap score differs from {report_path}")
    return {"method": raw["method"], "axes_file": axes_path, "sources": raw["sources"],
            "mean_best": sprint_score.mean_best(scored, gaps),
            "top10": [{"rank": i, "source": p["source"], "source_rank": p["source_rank"], "size": len(p["axis"]),
                       "identical_in": identical_in(p["axis"], sources, p["source"])} for i, p in enumerate(pooled, 1)],
            "per_gap": per_gap, "source_alone_subset": subset_scores(pooled, gaps, list(sources))}


def main() -> None:
    gaps = load_gaps()
    out = {"label": "EXPLORATORY DEV: H21b only; per-axis source attribution; diagnostic, not a try (230 tried)",
           "manifest": str(MANIFEST), "routes": str(ROUTES), "gap_sizes": {c: len(g) for c, g in gaps.items()},
           "shared_source": SHARED,
           "rows": {name: attribute(name, *paths, gaps) for name, paths in ROWS.items()}}
    (HERE / "attribution.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
