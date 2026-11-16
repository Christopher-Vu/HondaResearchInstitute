#!/usr/bin/env python3
"""The H21 pool (SimLingo, all 100 Fail2Drive pairs, seed 24) as a one-layer sprint cache, plus its scoring inputs.

    PYTHONPATH=src python docs/research/experiments/f2d-dev-simlingo/h21_cache.py \
        results/savio/h24-h25/f2d-features.npz configs/rollout/f2d-all.manifest.json --output results/h21

Writes, under --output:
- cache.npz in cache_pool.py's format. `driving_queries` is (routes, 3, 1, 896): only the approach-window slot (1)
  holds data, H24's layer-10 window mean; the route and early slots are NaN, so a method that reads them fails
  loudly. There are no per-frame speeds and no infraction counts. Rows are in cache_pool's salted order.
- b3_kin.json: the B3-behaviour stand-in. H24's `kin` block only (window speed mean, min and max, and the route's
  stationary share), standardised over all routes, Ward on the failing routes, cuts 2, 3 and 5, largest first.
- manifest.json: the f2d-all manifest with `pair` = `base_id`, which sprint_score.py resamples.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from scipy.cluster.hierarchy import fcluster, linkage

from cache_pool import order_key

CUTS = (2, 3, 5)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("features", type=Path)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with np.load(args.features) as raw:
        ids, failed, act, kin = (raw[k] for k in ("ids", "failed", "act", "kin"))
    order = sorted(range(len(ids)), key=lambda i: order_key(str(ids[i])))
    ids, failed, act, kin = [str(ids[i]) for i in order], failed[order], act[order], kin[order]

    block = np.full((len(ids), 3, 1, act.shape[1]), np.nan, np.float16)
    block[:, 1, 0] = act.astype(np.float16)
    meta = [json.dumps({"success": not f, "failure_step": None, "n_steps": None, "infractions": {}}) for f in failed]
    args.output.mkdir(parents=True, exist_ok=True)
    np.savez(args.output / "cache.npz", route_id=np.array(ids), meta=np.array(meta), driving_queries=block)

    z = (kin - kin.mean(0)) / np.where(kin.std(0) > 0, kin.std(0), 1.0)
    rows = np.flatnonzero(failed)
    tree = linkage(z[rows], method="ward")
    axes = []
    for k in CUTS:
        labels = fcluster(tree, t=k, criterion="maxclust")
        groups = sorted(({ids[rows[j]] for j in np.flatnonzero(labels == c)} for c in set(labels)), key=len,
                        reverse=True)
        axes += [{"name": f"kin cut {k} group {n + 1}", "rollouts": sorted(g)} for n, g in enumerate(groups)]
    (args.output / "b3_kin.json").write_text(json.dumps({"method": "B3_behaviour_kin", "axes": axes}, indent=1) + "\n")

    manifest = [entry | {"pair": entry["base_id"]} for entry in json.loads(args.manifest.read_text())]
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
    print(json.dumps({"routes": len(ids), "failing": int(failed.sum()), "b3_kin_axes": [len(a["rollouts"]) for a in axes]}))


if __name__ == "__main__":
    main()
