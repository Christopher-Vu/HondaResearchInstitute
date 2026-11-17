#!/usr/bin/env python3
"""Pool frozen held-out scores across models with a joint Fail2Drive-pair bootstrap.

Each ``--model`` is a JSON plan, written before the second held-out model is read::

  {"name": "tfpp", "manifest": "...", "routes": "...", "gaps": ["F2D_A"],
   "methods": {"m23": "m23.json", "m40": "m40.json"},
   "rivals": {"B3_behaviour": "b3.json", "B7_pool": "..."}}

The plans name frozen axes and public route files only.  The scorer gives every (model, gap) unit equal weight and
resamples the shared Fail2Drive pair IDs once per replicate, applying those weights to both models.  It reselects the
best finalist and rival in every replicate, as A1 and prereg amendment A3 require.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

import numpy as np

from harness.scoring_run import load_pool

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("sprint_score", HERE / "sprint_score.py")
assert SPEC is not None and SPEC.loader is not None
sprint_score = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sprint_score)


@dataclass
class Model:
    name: str
    gaps: dict[str, set[str]]
    methods: dict[str, list[set[str]]]
    rivals: dict[str, list[set[str]]]
    pair_of: dict[str, str]


def _path(plan: Path, value: str) -> str:
    path_text, *suffix = value.split(":", 1)
    path = Path(path_text)
    resolved = str(path if path.is_absolute() else plan.parent / path)
    return resolved if not suffix else f"{resolved}:{suffix[0]}"


def load_model(plan: Path) -> Model:
    """Read one frozen model plan without consulting labels beyond its listed gaps."""
    raw = json.loads(plan.read_text())
    required = {"name", "manifest", "routes", "gaps", "methods", "rivals"}
    missing = required - raw.keys()
    if missing:
        raise ValueError(f"{plan}: missing {sorted(missing)}")
    manifest_path = _path(plan, raw["manifest"])
    routes_path = _path(plan, raw["routes"])
    manifest, failed = load_pool([Path(manifest_path)], [Path(routes_path)])
    pool = set(failed)
    if not raw["gaps"]:
        raise ValueError(f"{plan}: needs at least one gap")
    gaps = {
        gap: {str(row["id"]) for row in manifest
              if row["role"] == "pilot_slice" and gap in row["practice_gaps"] and failed.get(str(row["id"]))}
        for gap in raw["gaps"]
    }
    pair_of = {str(row["id"]): str(row["pair"]) for row in manifest if str(row["id"]) in pool}
    if set(pair_of) != pool:
        raise ValueError(f"{plan}: routes and manifest IDs differ")

    def methods(kind: str) -> dict[str, list[set[str]]]:
        return {str(name): sprint_score.read_method(_path(plan, spec))[1]
                for name, spec in raw[kind].items()}

    return Model(str(raw["name"]), gaps, methods("methods"), methods("rivals"), pair_of)


def _validate(models: list[Model]) -> list[str]:
    if len(models) < 2:
        raise ValueError("need at least two held-out models")
    method_names, rival_names = set(models[0].methods), set(models[0].rivals)
    if not method_names or not rival_names:
        raise ValueError("each model needs a method and a rival")
    pairs = set(models[0].pair_of.values())
    for model in models:
        if set(model.methods) != method_names or set(model.rivals) != rival_names:
            raise ValueError("every model must name the same frozen methods and rivals")
        if set(model.pair_of.values()) != pairs:
            raise ValueError("held-out models must share the same Fail2Drive pairs")
    return sorted(pairs)


def unit_scores(models: list[Model], weight: Mapping[str, Mapping[str, float]] | None = None) -> dict[str, dict[str, dict[str, float]]]:
    """Per-model, per-gap best Jaccard, retained beside the pooled headline by A3."""
    names = [*models[0].methods, *models[0].rivals]
    result = {}
    for model in models:
        model_weight = None if weight is None else weight[model.name]
        result[model.name] = {
            gap_name: {name: sprint_score.best(axes, gap, model_weight)
                       for name, axes in {**model.methods, **model.rivals}.items()}
            for gap_name, gap in model.gaps.items()
        }
    return result


def scores(models: list[Model], weight: Mapping[str, Mapping[str, float]] | None = None) -> dict[str, float]:
    """Mean best Jaccard over model-gap units; no model or gap can dominate by having more routes."""
    names = [*models[0].methods, *models[0].rivals]
    values = {name: [] for name in names}
    for model_scores in unit_scores(models, weight).values():
        for gap_scores in model_scores.values():
            for name in names:
                values[name].append(gap_scores[name])
    return {name: float(np.mean(value)) for name, value in values.items()}


def pooled(models: list[Model], *, replicates: int = 2000, seed: int = 0) -> dict:
    """A3 headline and paired percentile intervals, with best selections remade on every draw."""
    pairs = _validate(models)
    point = scores(models)
    methods, rivals = list(models[0].methods), list(models[0].rivals)
    rng = np.random.default_rng(seed)
    draws = {name: np.empty(replicates) for name in [*methods, *rivals]}
    for draw in range(replicates):
        counts = np.bincount(rng.integers(0, len(pairs), len(pairs)), minlength=len(pairs))
        count_of = dict(zip(pairs, counts))
        weights = {model.name: {route: float(count_of[pair]) for route, pair in model.pair_of.items()}
                   for model in models}
        for name, value in scores(models, weights).items():
            draws[name][draw] = value

    units = unit_scores(models)

    def contrast(left: str, right: list[str]) -> dict:
        delta = draws[left] - np.maximum.reduce([draws[name] for name in right])
        point_delta = point[left] - max(point[name] for name in right)
        return {"delta": point_delta,
                "interval": [float(v) for v in np.percentile(delta, [2.5, 97.5])],
                "p_one_sided": float((delta <= 0).mean())}

    rows = {
        method: {"mean_best": point[method], "vs": {rival: contrast(method, [rival]) for rival in rivals},
                 "vs_best_rival": contrast(method, rivals)}
        for method in methods
    }
    delta = np.maximum.reduce([draws[name] for name in methods]) - np.maximum.reduce([draws[name] for name in rivals])
    return {
        "label": "HELD-OUT: pooled equally across model-gap units; paired bootstrap is exploratory until the final read",
        "models": [model.name for model in models],
        "gaps": {model.name: sorted(model.gaps) for model in models},
        "weights": "each model-gap unit equally; Fail2Drive pairs jointly resampled across models",
        "replicates": replicates,
        "per_model": {
            model.name: {
                "mean_best": {name: float(np.mean([gap_scores[name] for gap_scores in units[model.name].values()]))
                              for name in [*methods, *rivals]},
                "per_gap": units[model.name],
            }
            for model in models
        },
        "rows": rows,
        "headline_best_method_vs_best_rival": {
            "delta": max(point[name] for name in methods) - max(point[name] for name in rivals),
            "interval": [float(v) for v in np.percentile(delta, [2.5, 97.5])],
            "p_one_sided": float((delta <= 0).mean()),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--model", action="append", type=Path, required=True, help="frozen JSON model plan")
    parser.add_argument("--replicates", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = pooled([load_model(path) for path in args.model], replicates=args.replicates, seed=args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps(report["headline_best_method_vs_best_rival"]))


if __name__ == "__main__":
    main()
