"""Independent rescore of the H21b headline from the pre-registration text alone.

Rule (docs/prereg-fail2drive.md A1 + A2): each method keeps its first M = 10
distinct axes; its score is the mean over gaps of the best Jaccard between one of
those axes and the gap's failing rollouts. Comparisons: delta, 95% percentile
interval and one-sided p from a paired bootstrap of 2,000 replicates resampling
Fail2Drive pairs, each pair carrying all its seeds.

A resampled pair contributes its routes once per draw, so Jaccard in a replicate
is weighted by draw counts.
"""

import argparse
import json
import re
from pathlib import Path

import numpy as np

AXIS_BUDGET = 10
REPLICATES = 2000
SEED_SUFFIX = re.compile(r"-s\d+$")


def jaccard(a, b):
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)


def first_distinct_axes(axes, budget=AXIS_BUDGET):
    kept = []
    for axis in axes:
        rollouts = frozenset(axis["rollouts"])
        if rollouts not in kept:
            kept.append(rollouts)
        if len(kept) == budget:
            break
    return kept


def fail2drive_pair(entry):
    return SEED_SUFFIX.sub("", entry["base_id"])


def load_pool(manifest_path, routes_path):
    outcomes = {}
    for line in Path(routes_path).read_text().splitlines():
        record = json.loads(line)
        outcomes[record["id"]] = record["success"]
    scored = [e for e in json.loads(Path(manifest_path).read_text()) if e["id"] in outcomes]
    for entry in scored:
        entry["failed"] = not outcomes[entry["id"]]
    return scored


def gap_failures(scored, gap):
    return frozenset(
        e["id"] for e in scored
        if e["failed"] and e["role"] == "pilot_slice" and gap in e["practice_gaps"]
    )


def membership(sets, route_index):
    matrix = np.zeros((len(sets), len(route_index)), dtype=bool)
    for row, members in enumerate(sets):
        matrix[row, [route_index[r] for r in members]] = True
    return matrix


def weighted_best_jaccard(axes, gaps, weights):
    """Mean over gaps of the best weighted Jaccard; weights is (replicates, routes)."""
    per_gap = []
    for gap in gaps:
        inter = (axes & gap).astype(float) @ weights.T
        union = (axes | gap).astype(float) @ weights.T
        ratio = np.divide(inter, union, out=np.zeros_like(inter), where=union > 0)
        per_gap.append(ratio.max(axis=0))
    return np.mean(per_gap, axis=0)


def replicate_weights(scored, route_index, rng, replicates=REPLICATES):
    pairs = sorted({fail2drive_pair(e) for e in scored})
    pair_of_route = np.zeros(len(route_index), dtype=int)
    for entry in scored:
        pair_of_route[route_index[entry["id"]]] = pairs.index(fail2drive_pair(entry))
    draws = rng.integers(0, len(pairs), size=(replicates, len(pairs)))
    counts = np.stack([np.bincount(row, minlength=len(pairs)) for row in draws])
    return counts[:, pair_of_route].astype(float), len(pairs)


def compare(method, rival):
    delta = method - rival
    return {
        "delta": float(delta[0]),
        "interval": [float(np.percentile(delta[1:], 2.5)), float(np.percentile(delta[1:], 97.5))],
        "p_one_sided": float(np.mean(delta[1:] <= 0)),
    }


def score(args):
    scored = load_pool(args.manifest, args.routes)
    route_index = {e["id"]: i for i, e in enumerate(scored)}
    gap_sets = [gap_failures(scored, g) for g in args.gaps]
    gaps = membership(gap_sets, route_index)
    weights, n_pairs = replicate_weights(scored, route_index, np.random.default_rng(args.seed))
    weights = np.vstack([np.ones(len(route_index)), weights])

    methods, per_gap = {}, {}
    for spec in args.method:
        name, path = spec.split("=", 1)
        axes_sets = first_distinct_axes(json.loads(Path(path).read_text())["axes"])
        methods[name] = weighted_best_jaccard(membership(axes_sets, route_index), gaps, weights)
        per_gap[name] = {g: max(jaccard(a, s) for a in axes_sets) for g, s in zip(args.gaps, gap_sets)}

    return {
        "routes": len(scored),
        "failing": sum(e["failed"] for e in scored),
        "pairs_resampled": n_pairs,
        "gap_failures": {g: len(s) for g, s in zip(args.gaps, gap_sets)},
        "replicates": REPLICATES,
        "seed": args.seed,
        "scores": {n: float(v[0]) for n, v in methods.items()},
        "per_gap": per_gap,
        "comparisons": {
            f"{m} - {r}": compare(methods[m], methods[r])
            for m, r in (spec.split(":") for spec in args.compare)
        },
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--routes", required=True)
    parser.add_argument("--gaps", nargs="+", required=True)
    parser.add_argument("--method", action="append", required=True, help="name=axes.json")
    parser.add_argument("--compare", action="append", default=[], help="method:rival")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--output")
    args = parser.parse_args()
    report = score(args)
    text = json.dumps(report, indent=2)
    print(text)
    if args.output:
        Path(args.output).write_text(text + "\n")


if __name__ == "__main__":
    main()
