#!/usr/bin/env python3
"""j08: multi-view Ward candidates, ranked by bootstrap cluster stability.

Why: the view that carries the gaps differs by pool. On H21 the speed features
beat layer 10 even with labels (round-8 ceiling diagnostic), while on Chris's
pool B3-behaviour scores 0.093 and activation layers lead (all measured, dev).
A fixed view is a bet on the pool. j08 pools candidates from every view and
lets a label-free signal, the stability of each cluster under subsampling,
pick which ones fill the 10 slots.

Two kinds of view, in a fixed order. V0, "kin", is the behaviour block from
j06 (the cache kin array, otherwise b3 kinematics), columns standardised over
every route. A column whose standard deviation is 0 is set to 0. That matrix
is the embedding: no PCA. V1 onward is one view per driving_queries layer at
the window summary. Layers are j01's defaults, the fractions 5/23, 8/23 and
20/23 of the tensor depth, de-duplicated; a one-layer cache contributes the
one layer it has. Each layer is embedded with j01.embed_unwhitened, PCA to 32
components, fit on every route.

Ward (scipy, the same linkage and the same largest-first order as
cache_methods.axes_from) cuts the failing rows of each view at k = 2, 3 and 5.
A cluster is kept only when 3 <= size <= n_fail // 2. Stability is the
clusterwise Jaccard of Hennig 2007. For each view, 100 subsamples (or
--subsamples) each draw a rounded --frac of the failing routes without
replacement, from one numpy Generator seeded by --seed, in view then subsample
order. Ward is re-run on that view's existing rows (the embedding is not
refit) and cut at the same k. The score of cluster C on subsample S is the
maximum over subsample clusters D of |C intersect D| / |(C intersect S) union D|.
A subsample that misses C is skipped, and the stability is the mean of the
rest. Rows of a subsample keep cache order.

Axes are ranked by stability descending, then smaller size, then view order,
then cut order, then that cut's cluster order. Route ids are not a sort key.
Greedy de-duplication drops a candidate whose Jaccard with an already chosen
axis is above 0.5. The first 10 that remain are written. The only label read
is pass/fail. No gap, category, or scenario field is read.

    PYTHONPATH=src python docs/research/experiments/f2d-dev-simlingo/j08_stability.py CACHE \
        --output OUT.json --subsamples 100 --frac 0.8 --seed 0
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

import numpy as np
from scipy.cluster.hierarchy import fcluster, linkage

from harness.scoring import jaccard


def _load(name: str):
    path = Path(__file__).with_name(f"{name}.py")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


j01 = _load("j01_unwhite")
j06 = _load("j06_kinresid")
cache_methods = _load("cache_methods")

CUTS = (2, 3, 5)
DIMS = 32
SITE = "driving_queries"
SUMMARY = "window"
MIN_SIZE = 3
MAX_AXES = 10
OVERLAP = 0.5


def standardise_columns(behaviour: np.ndarray) -> np.ndarray:
    """Centre each column and divide by its standard deviation. Std 0 becomes 0."""
    block = np.asarray(behaviour, dtype=np.float64)
    if block.ndim == 1:
        block = block.reshape(-1, 1)
    if block.ndim != 2:
        raise SystemExit(f"j08: behaviour block has shape {getattr(behaviour, 'shape', None)}")
    centred = block - block.mean(axis=0)
    sd = block.std(axis=0)
    scaled = np.zeros_like(centred)
    keep = sd > 0
    scaled[:, keep] = centred[:, keep] / sd[keep]
    return scaled


def dedupe_layers(layers: list[int]) -> list[int]:
    seen: list[int] = []
    for layer in layers:
        layer = int(layer)
        if layer not in seen:
            seen.append(layer)
    return seen


def subsample_count(n_fail: int, frac: float) -> int:
    """Rounded fraction of the failing routes, capped at the whole failing set."""
    return min(n_fail, int(round(float(frac) * n_fail)))


def ward_candidates(embedding: np.ndarray, failing: np.ndarray, ids: list[str], view, view_order: int,
                    n_fail: int) -> list[dict]:
    """Failing-route Ward clusters at each cut, in cache_methods order, after the size filter."""
    rows = np.flatnonzero(failing)
    tree = linkage(np.asarray(embedding[rows], dtype=np.float64), method="ward")
    limit = n_fail // 2
    index_of = {route_id: index for index, route_id in enumerate(ids)}
    candidates = []
    for cut_order, k in enumerate(CUTS):
        labels = fcluster(tree, t=k, criterion="maxclust")
        # Largest first. Equal sizes keep the order of set(labels), as axes_from does.
        ordered = sorted(
            ({ids[rows[j]] for j in np.flatnonzero(labels == c)} for c in set(labels)),
            key=len,
            reverse=True,
        )
        for cluster_order, members in enumerate(ordered):
            size = len(members)
            if size < MIN_SIZE or size > limit:
                continue
            rollouts = sorted(members)
            candidates.append({
                "view": view,
                "view_order": view_order,
                "cut": int(k),
                "cut_order": cut_order,
                "cluster_order": cluster_order,
                "size": size,
                "rollouts": rollouts,
                "indices": {index_of[route_id] for route_id in members},
                "scores": [],
            })
    return candidates


def _partitions(sample: np.ndarray, embedding: np.ndarray) -> dict[int, list[set[int]]]:
    tree = linkage(np.asarray(embedding[sample], dtype=np.float64), method="ward")
    partitions = {}
    for k in CUTS:
        labels = fcluster(tree, t=k, criterion="maxclust")
        partitions[k] = [
            {int(sample[j]) for j in np.flatnonzero(labels == c)}
            for c in set(labels)
        ]
    return partitions


def score_candidates(embedding: np.ndarray, samples: list[np.ndarray], candidates: list[dict]) -> None:
    """Mean clusterwise Jaccard. A subsample that misses a candidate is skipped for that candidate."""
    if not candidates:
        return
    for sample in samples:
        partitions = _partitions(sample, embedding)
        sample_set = {int(index) for index in sample}
        for cand in candidates:
            base = cand["indices"] & sample_set
            if not base:
                continue
            best = 0.0
            for group in partitions[cand["cut"]]:
                union = len(base | group)
                if union == 0:
                    continue
                score = len(base & group) / union
                if score > best:
                    best = score
            cand["scores"].append(best)
    for cand in candidates:
        scores = cand["scores"]
        cand["stability"] = float(sum(scores) / len(scores)) if scores else 0.0


def select_axes(candidates: list[dict], method: str) -> list[dict]:
    """Stability, then smaller size, then view, cut and cluster order. Drop Jaccard overlaps above 0.5."""
    ranked = sorted(candidates, key=lambda cand: (
        -cand["stability"], cand["size"], cand["view_order"], cand["cut_order"], cand["cluster_order"],
    ))
    chosen: list[dict] = []
    chosen_sets: list[set[str]] = []
    for cand in ranked:
        routes = set(cand["rollouts"])
        if any(jaccard(routes, previous) > OVERLAP for previous in chosen_sets):
            continue
        chosen_sets.append(routes)
        chosen.append({
            "name": f"{method} view {cand['view']} cut {cand['cut']} group {cand['cluster_order'] + 1}",
            "rollouts": cand["rollouts"],
            "view": cand["view"],
            "cut": cand["cut"],
            "size": cand["size"],
            "stability": cand["stability"],
        })
        if len(chosen) == MAX_AXES:
            break
    return chosen


def build_axes(views: list[tuple], failing: np.ndarray, ids: list[str], subsamples: int, frac: float,
               seed: int, method: str) -> list[dict]:
    n_fail = int(np.count_nonzero(failing))
    if n_fail < 2:
        raise SystemExit(f"j08: need at least 2 failing routes, got {n_fail}")
    n_sub = subsample_count(n_fail, frac)
    if n_sub < 2:
        raise SystemExit(f"j08: subsample size {n_sub} is below 2 (frac {frac}, failing {n_fail})")
    fail_idx = np.flatnonzero(failing)
    per_view = []
    for view_order, (view, embedding) in enumerate(views):
        per_view.append(ward_candidates(embedding, failing, ids, view, view_order, n_fail))
    rng = np.random.default_rng(seed)
    for candidates, (_view, embedding) in zip(per_view, views):
        samples = [np.sort(rng.choice(fail_idx, size=n_sub, replace=False)) for _ in range(subsamples)]
        score_candidates(embedding, samples, candidates)
    flat = [cand for group in per_view for cand in group]
    return select_axes(flat, method)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("cache", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--subsamples", type=int, default=100)
    parser.add_argument("--frac", type=float, default=0.8)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--layer", type=int, nargs="*", default=None,
                        help="absolute indices; default is fractions 5/23, 8/23, 20/23 of the tensor depth")
    args = parser.parse_args()
    if args.subsamples < 1:
        raise SystemExit(f"j08: --subsamples must be at least 1, got {args.subsamples}")
    if not 0.0 < args.frac <= 1.0:
        raise SystemExit(f"j08: --frac must be in (0, 1], got {args.frac}")
    j04 = _load("j04_bgmoment")
    with np.load(args.cache) as cache:
        if SITE not in cache.files:
            raise SystemExit(f"j08: cache has no site {SITE}")
        ids = [str(item) for item in cache["route_id"].tolist()]
        meta = [json.loads(item) for item in cache["meta"]]
        failing = np.array([not item["success"] for item in meta])
        block = cache[SITE][:, cache_methods.SUMMARY[SUMMARY]]
        n_layers = 1 if block.ndim == 2 else int(block.shape[1])
        layers = dedupe_layers(j04.resolve_layers(n_layers, args.layer))
        behaviour, behaviour_name = j06.behaviour_matrix(cache, meta)
        views: list[tuple] = [("kin", np.array(standardise_columns(behaviour), dtype=np.float64, copy=True))]
        for layer in layers:
            matrix = j01.layer_matrix(cache, SITE, [layer], SUMMARY)
            embedded = j01.embed_unwhitened(matrix, DIMS, args.seed)
            views.append((int(layer), np.array(embedded, dtype=np.float64, copy=True)))
    method = f"j08-{SITE}-L{'+'.join(str(layer) for layer in layers)}-{SUMMARY}"
    axes = build_axes(views, failing, ids, args.subsamples, args.frac, args.seed, method)
    out = {
        "method": method,
        "settings": vars(args) | {
            "cache": str(args.cache),
            "output": str(args.output),
            "layer": layers,
            "behaviour": behaviour_name,
            "views": [view for view, _embedding in views],
        },
        "axes": axes,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({
        "method": method,
        "axes": [
            {"view": axis["view"], "cut": axis["cut"], "size": axis["size"], "stability": axis["stability"]}
            for axis in axes
        ],
    }))


if __name__ == "__main__":
    main()
