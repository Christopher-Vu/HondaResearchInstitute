#!/usr/bin/env python3
"""j03: m03's embedding, then smaller Ward cuts pooled by cohesion.

m09 round-robins four sources of Ward cuts 2, 3 and 5. That is 10 axes per
source, and the round-robin stops at 10, so cut 5 never gets a slot. Cuts 2
and 3 on a few hundred failures are catch-alls. j03 keeps m03's embedding at
each source (standardise, PCA to 32, standardise on one layer of the approach
window) and emits clusters from cuts 8, 12 and 16 whose sizes fall in
size_band, ranked by cohesion, then round-robins those lists.

Layer choice is a fraction of the cache tensor's own layer axis, so a model
with 6 or 3 layers does not index a 24-layer decoder. On 24 layers the default
fractions land on driving_queries 5, 8 and 20 and all_tokens 1, the four places
m09 used.

    PYTHONPATH=src python docs/research/experiments/f2d-dev-simlingo/j03_bandpool.py CACHE --output OUT.json
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from itertools import zip_longest
from pathlib import Path

import numpy as np
from scipy.cluster.hierarchy import fcluster, linkage

from harness.scoring import jaccard

_SPEC = importlib.util.spec_from_file_location("cache_methods", Path(__file__).with_name("cache_methods.py"))
cache_methods = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(cache_methods)

CUTS = (8, 12, 16)
DIMS = 32
# Fractions of (n_layers - 1), not a fixed decoder depth.
DEFAULT_SITES = (
    ("driving_queries", (5 / 23, 8 / 23, 20 / 23)),
    ("all_tokens", (1 / 23,)),
)


def fractional_layers(n_layers: int, fracs) -> list[int]:
    """Layer indices at frac * (n_layers - 1), clamped, unique, then sorted.

    Python round is banker's. n_layers >= 1 never indexes off the end.
    """
    last = n_layers - 1
    picked = []
    for frac in fracs:
        index = int(round(float(frac) * last))
        if index < 0:
            index = 0
        elif index > last:
            index = last
        picked.append(index)
    return sorted(set(picked))


def size_band(n_fail: int) -> tuple[int, int]:
    """Inclusive cluster-size band. lo is at least 5; hi is at least lo + 1."""
    lo = max(5, int(round(n_fail / 30)))
    hi = max(lo + 1, int(round(n_fail / 8)))
    return lo, hi


def cohesion(rows) -> float:
    """Mean squared Euclidean distance to the centroid. Lower is tighter. Label-free."""
    pts = np.asarray(rows, dtype=np.float64)
    center = pts.mean(axis=0)
    delta = pts - center
    return float(np.mean(np.sum(delta * delta, axis=1)))


def band_axes(features, failing, ids, cuts: tuple[int, ...] = CUTS) -> list[dict]:
    """Ward clusters of the failing rows whose size is inside size_band, tightest first."""
    features = np.asarray(features)
    mask = np.asarray(failing, dtype=bool)
    id_arr = np.asarray(ids).astype(str)
    rows = np.flatnonzero(mask)
    data = features[mask]
    if len(data) < 2:
        return []
    lo, hi = size_band(int(mask.sum()))
    tree = linkage(data, method="ward")
    kept: list[dict] = []
    n = len(data)
    for k in cuts:
        kk = min(int(k), n)
        if kk < 1:
            continue
        labels = fcluster(tree, t=kk, criterion="maxclust")
        for label in set(labels.tolist()):
            members = np.flatnonzero(labels == label)
            size = int(len(members))
            if size < lo or size > hi:
                continue
            member_ids = sorted(id_arr[rows[members]].tolist())
            kept.append({
                "name": f"cut {kk} size {size} c{int(label)}",
                "rollouts": member_ids,
                "cohesion": cohesion(data[members]),
                "size": size,
                "cut": int(kk),
                "label": int(label),
            })
    kept.sort(key=lambda axis: (axis["cohesion"], -axis["size"], axis["cut"], axis["label"]))
    return kept


def pool_sources(sources, limit: int = 10, overlap: float = 0.8) -> list[set[str]]:
    """Round-robin ranked rollout-sets. Skip Jaccard >= overlap with any kept set. Stop at limit.

    Order is the caller's rank. The overlap rule matches pool_axes.py.
    """
    kept: list[set[str]] = []
    for layer in zip_longest(*sources):
        for item in layer:
            if item is None or len(kept) >= limit:
                continue
            group = set(item)
            if all(jaccard(group, prev) < overlap for prev in kept):
                kept.append(group)
            if len(kept) >= limit:
                return kept
    return kept


def _n_layers(cache, site: str) -> int | None:
    files = getattr(cache, "files", None)
    if files is not None and site not in files:
        return None
    try:
        array = cache[site]
    except KeyError:
        return None
    summary = cache_methods.SUMMARY["window"]
    if getattr(array, "ndim", 0) < 3 or array.shape[1] <= summary:
        return None
    block = array[:, summary]
    if getattr(block, "ndim", 0) < 3 or block.shape[1] < 1:
        return None
    return int(block.shape[1])


def _ranked_sources(cache, ids: list[str], failing: np.ndarray):
    lists: list[list[set[str]]] = []
    resolved: list[dict] = []
    for site, fracs in DEFAULT_SITES:
        n_layers = _n_layers(cache, site)
        if n_layers is None:
            continue
        for layer in fractional_layers(n_layers, fracs):
            if layer < 0 or layer >= n_layers:
                continue
            raw = cache_methods.activations(cache, site, [layer], "window")
            embedded = cache_methods.embed("m03", raw, failing, DIMS, 16, 0)
            features = cache_methods.standardise(embedded)
            ranked = band_axes(features, failing, ids, CUTS)
            lists.append([set(axis["rollouts"]) for axis in ranked])
            resolved.append({"site": site, "layer": int(layer)})
    return lists, resolved


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("cache", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with np.load(args.cache) as cache:
        ids = [str(x) for x in cache["route_id"].tolist()]
        meta = [json.loads(m) for m in cache["meta"]]
        failing = np.array([not m["success"] for m in meta])
        lists, resolved = _ranked_sources(cache, ids, failing)
    lo, hi = size_band(int(failing.sum()))
    pooled = pool_sources(lists, limit=10, overlap=0.8)
    out = {
        "method": "j03",
        "settings": {
            "layers": resolved,
            "size_band": [lo, hi],
            "cuts": list(CUTS),
            "summary": "window",
            "dims": DIMS,
            "overlap": 0.8,
            "limit": 10,
        },
        "axes": [{"name": f"j03 axis {i + 1}", "rollouts": sorted(group)} for i, group in enumerate(pooled)],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({"method": out["method"], "layers": resolved, "size_band": [lo, hi],
                      "axes": [len(a["rollouts"]) for a in out["axes"]]}))


if __name__ == "__main__":
    main()
