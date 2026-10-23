"""Resampling utilities for contrastive discovery stability evaluation."""

from __future__ import annotations

from collections import defaultdict

import numpy as np


def resample_by_base(
    rollout_ids: list[str],
    base_ids: dict[str, str],
    seed: int,
    keep_fraction: float = 0.8,
) -> list[str]:
    """Keep a reproducible random subset of base routes and all their rollouts."""
    if not 0 < keep_fraction <= 1:
        raise ValueError("keep_fraction must be between 0 and 1")

    groups: dict[str, list[str]] = defaultdict(list)

    for rollout_id in rollout_ids:
        groups[base_ids[rollout_id]].append(rollout_id)

    bases = sorted(groups)
    if not bases:
        return []

    rng = np.random.default_rng(seed)
    n_keep = max(1, round(len(bases) * keep_fraction))
    selected = set(rng.choice(bases, size=n_keep, replace=False))

    return [
        rollout_id
        for rollout_id in rollout_ids
        if base_ids[rollout_id] in selected
    ]
from discovery.contrastive import (
    ContrastiveConfig,
    Rollout,
    contrastive_directive,
)


def evaluate_stability(
    rollouts: list[Rollout],
    base_ids: dict[str, str],
    seeds: range = range(10),
) -> list[dict]:
    """Compare contrastive discovery with and without a failure-share cap."""

    results = []
    rollout_ids = [r.rollout_id for r in rollouts]

    for seed in seeds:
        selected_ids = set(
            resample_by_base(rollout_ids, base_ids, seed=seed)
        )

        sample = [
            r for r in rollouts
            if r.rollout_id in selected_ids
        ]

        for method, cap in [
            ("uncapped", None),
            ("capped", 0.8),
        ]:
            config = ContrastiveConfig(max_failure_share=cap)

            directive, _ = contrastive_directive(sample, config)

            failures = {
                r.rollout_id for r in sample if r.failed
            }

            axes = directive.axes

            results.append({
                "seed": seed,
                "method": method,
                "n_rollouts": len(sample),
                "n_failures": len(failures),
                "n_axes": len(axes),
                "largest_axis_share": max(
                    (
                        len(axis.rollouts & failures) / len(failures)
                        for axis in axes
                    ),
                    default=0.0,
                ) if failures else 0.0,
            })

    return results
def axis_similarity(
    axes_a: list[set[str]],
    axes_b: list[set[str]],
    shared_rollouts: set[str],
) -> float:
    """Compare discovered axes on rollouts shared by two samples.

    Returns the mean best-match Jaccard similarity, symmetrized
    across both sets of axes.
    """
    a = [axis & shared_rollouts for axis in axes_a]
    b = [axis & shared_rollouts for axis in axes_b]

    a = [axis for axis in a if axis]
    b = [axis for axis in b if axis]

    if not a and not b:
        return 1.0

    if not a or not b:
        return 0.0

    def best_match(source, target):
        scores = []

        for axis in source:
            best = max(
                len(axis & other) / len(axis | other)
                for other in target
            )
            scores.append(best)

        return sum(scores) / len(scores)

    return (
        best_match(a, b) +
        best_match(b, a)
    ) / 2
def evaluate_stability(
    rollouts: list[Rollout],
    base_ids: dict[str, str],
    seeds: range = range(10),
) -> list[dict]:
    """Compare contrastive discovery across all pairs of resamples."""

    results = []
    rollout_ids = [r.rollout_id for r in rollouts]
    samples_by_method = {"uncapped": [], "capped": []}

    for seed in seeds:
        selected_ids = set(
            resample_by_base(rollout_ids, base_ids, seed=seed)
        )

        sample = [
            r for r in rollouts
            if r.rollout_id in selected_ids
        ]

        failures = {
            r.rollout_id for r in sample if r.failed
        }

        for method, cap in [
            ("uncapped", None),
            ("capped", 0.8),
        ]:
            config = ContrastiveConfig(max_failure_share=cap)
            directive, _ = contrastive_directive(sample, config)

            axes = [set(axis.rollouts) for axis in directive.axes]

            samples_by_method[method].append({
                "seed": seed,
                "selected_ids": selected_ids,
                "axes": axes,
            })

            results.append({
                "seed": seed,
                "method": method,
                "n_rollouts": len(sample),
                "n_failures": len(failures),
                "n_axes": len(axes),
                "largest_axis_share": max(
                    (
                        len(axis & failures) / len(failures)
                        for axis in axes
                    ),
                    default=0.0,
                ) if failures else 0.0,
                "stability": None,
            })

    for method, samples in samples_by_method.items():
        for first, second in combinations(samples, 2):
            shared = first["selected_ids"] & second["selected_ids"]

            if not shared:
                continue

            similarity = axis_similarity(
                first["axes"],
                second["axes"],
                shared,
            )

            for row in results:
                if row["method"] == method and row["seed"] == second["seed"]:
                    row.setdefault("pairwise_stability", []).append(similarity)

    for row in results:
        values = row.pop("pairwise_stability", [])
        row["stability"] = (
            float(np.mean(values)) if values else None
        )

    return results
from itertools import combinations


def summarize_stability(results: list[dict]) -> dict:
    """Summarize stability and axis coverage for each method."""
    summary = {}

    for method in ("uncapped", "capped"):
        rows = [r for r in results if r["method"] == method]

        stability_values = [
            r["stability"]
            for r in rows
            if r["stability"] is not None
        ]

        summary[method] = {
            "n_resamples": len(rows),
            "mean_stability": (
                float(np.mean(stability_values))
                if stability_values else None
            ),
            "mean_axes": (
                float(np.mean([r["n_axes"] for r in rows]))
                if rows else None
            ),
            "mean_largest_axis_share": (
                float(np.mean([
                    r["largest_axis_share"] for r in rows
                ]))
                if rows else None
            ),
            "empty_axis_frequency": (
                float(np.mean([r["n_axes"] == 0 for r in rows]))
                if rows else None
            ),
        }

    return summary