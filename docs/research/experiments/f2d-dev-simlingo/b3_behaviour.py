#!/usr/bin/env python3
"""B3-behaviour, the sprint's main rival (docs/prd-discovery-sprint.md §3.1; prereg amendment A1).

    PYTHONPATH=src python docs/research/experiments/f2d-dev-simlingo/b3_behaviour.py CACHE --output b3.json

Only what a fleet logs. From the cache (cache_pool.py): ego speed per captured frame and the infraction counts.
Features per route:
- approach window (the last 6 captured frames, about 3 s, before the failure step, or before the end): mean, min,
  max and final speed, mean acceleration and largest deceleration;
- whole route: mean speed, fraction of frames below 0.5 m/s, log of the step count;
- one count per infraction type seen anywhere in the pool.
Excluded: distances to objects, any scenario or route field, expert action error (Chris, 2026-11-14: out). Steering
and braking are not logged in these shards, so they are not used.

Grouping: features standardised over all routes; Ward clustering of the failing routes; axes are the clusters at
cuts k = 2, 3 and 5 (10 axes), in that order, largest first within a cut.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from scipy.cluster.hierarchy import fcluster, linkage

WINDOW = 6
CUTS = (2, 3, 5)


def kinematics(speed: np.ndarray, step: np.ndarray, failure_step: int | None) -> list[float]:
    keep = ~np.isnan(speed)
    v, t = speed[keep], step[keep] / 20.0
    before = (step[keep] < failure_step) if failure_step is not None else np.ones(len(v), bool)
    if not before.any():
        before[0] = True
    wv, wt = v[before][-WINDOW:], t[before][-WINDOW:]
    accel = np.diff(wv) / np.maximum(np.diff(wt), 1e-6) if len(wv) > 1 else np.zeros(1)
    return [wv.mean(), wv.min(), wv.max(), wv[-1], accel.mean(), accel.min(),
            v.mean(), (v < 0.5).mean(), np.log1p(len(v) * 10)]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("cache", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with np.load(args.cache) as cache:
        ids, meta = cache["route_id"].tolist(), [json.loads(m) for m in cache["meta"]]
        speed, step = cache["ego_speed"], cache["step"]
    kinds = sorted({k for m in meta for k in m["infractions"]})
    features = np.array([kinematics(speed[i], step[i], m["failure_step"]) +
                         [float(m["infractions"].get(k, 0) or 0) for k in kinds] for i, m in enumerate(meta)])
    features = (features - features.mean(0)) / np.where(features.std(0) > 0, features.std(0), 1.0)
    failing = [i for i, m in enumerate(meta) if not m["success"]]
    tree = linkage(features[failing], method="ward")
    axes = []
    for k in CUTS:
        labels = fcluster(tree, t=k, criterion="maxclust")
        groups = sorted(({ids[failing[j]] for j in np.flatnonzero(labels == c)} for c in set(labels)), key=len,
                        reverse=True)
        axes += [{"name": f"behaviour cut {k} group {n + 1}", "rollouts": sorted(g)} for n, g in enumerate(groups)]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"method": "B3_behaviour", "features": len(features[0]), "infraction_kinds": kinds,
                                       "axes": axes}, indent=1) + "\n")
    print(json.dumps({"failing": len(failing), "axes": [len(a["rollouts"]) for a in axes]}))


if __name__ == "__main__":
    main()
