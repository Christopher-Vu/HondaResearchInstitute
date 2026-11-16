#!/usr/bin/env python3
"""j10: emission-mean Fisher score of j09's diagonal Gaussian HMM.

j09 embeds a failing route by how often it visits each state and how it moves
between them. Two routes with the same visits then look the same, even when
their frames sit in different places inside a state. j10 keeps j09's frame
scaling, unwhitened 16-d projection, and BIC model (S in {4, 6, 8}, fit on
every route). It embeds each failing route by the Fisher score of the emission
means (Jaakkola & Haussler 1998).

For state s, posterior gamma_t(s) from j09's forward-backward, mean mu_s and
diagonal variance var_s:

    g_s = (1 / (T * sqrt(w_s))) * sum_t gamma_t(s) * (x_t - mu_s) / sqrt(var_s)

T is that route's frame count. w_s is the mean of gamma over every valid frame
of every route, passing and failing, computed once. The S blocks are
concatenated and not standardised.

    PYTHONPATH=src python docs/research/experiments/f2d-dev-simlingo/j10_hmmfisher.py CACHE \
        --output OUT.json

CACHE is the per-frame file: route_id, meta, layers, site, frames, n_frames.
Pass/fail is read from meta.success. No scenario, town, route-config, or
category field is read, and ego_speed is not read. One layer only. With no
--layer, the layer is round(8/23*(--depth-1)) at --depth 24, and that index
must be one of the stored layers.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

import numpy as np


def _load_j09():
    path = Path(__file__).with_name("j09_hmm.py")
    spec = importlib.util.spec_from_file_location("j09_hmm", path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


j09 = _load_j09()


def embed_failing(sequences: list[np.ndarray], failing: np.ndarray, model: dict) -> np.ndarray:
    """S*D Fisher scores of the emission means. Passing routes stay zero.

    w_s is the frame-weighted mean posterior over every sequence in
    `sequences`, not only the failing ones. A state with no posterior mass
    gets a zero block.
    """
    means = np.asarray(model["means"], dtype=np.float64)
    variances = np.asarray(model["variances"], dtype=np.float64)
    startprob = np.asarray(model["startprob"], dtype=np.float64)
    transmat = np.asarray(model["transmat"], dtype=np.float64)
    n_states, dim = means.shape
    n_routes = len(sequences)
    failing = np.asarray(failing, dtype=bool)
    if failing.shape != (n_routes,):
        raise ValueError(f"j10: failing has shape {failing.shape}, expected {(n_routes,)}")
    inv_sqrt = np.zeros_like(variances)
    np.divide(1.0, np.sqrt(variances), out=inv_sqrt, where=variances > 0.0)

    raw = np.zeros((n_routes, n_states, dim), dtype=np.float64)
    lengths = np.zeros(n_routes, dtype=np.float64)
    sum_gamma = np.zeros(n_states, dtype=np.float64)
    total_frames = 0
    buckets: dict[int, list[int]] = {}
    for index, seq in enumerate(sequences):
        buckets.setdefault(len(seq), []).append(index)
    for indexes in buckets.values():
        obs = np.stack([sequences[index] for index in indexes], axis=0)
        _ll, gamma, _xi = j09._fb_batch(obs, startprob, transmat, means, variances)
        sum_gamma += gamma.sum(axis=(0, 1))
        total_frames += int(gamma.shape[0] * gamma.shape[1])
        sum_g = gamma.sum(axis=1)
        sum_gx = np.einsum("nts,ntd->nsd", gamma, obs, optimize=True)
        centered = sum_gx - means[None, :, :] * sum_g[:, :, None]
        score = centered * inv_sqrt[None, :, :]
        length = float(gamma.shape[1])
        for row, index in enumerate(indexes):
            raw[index] = score[row]
            lengths[index] = length
    if total_frames == 0:
        raise SystemExit("j10: no frames")
    w = sum_gamma / float(total_frames)
    sqrt_w = np.sqrt(np.maximum(w, 0.0))
    features = np.zeros((n_routes, n_states * dim), dtype=np.float64)
    live = sqrt_w > 0.0
    for index in np.flatnonzero(failing):
        block = np.zeros((n_states, dim), dtype=np.float64)
        block[live] = raw[index, live] / (lengths[index] * sqrt_w[live, None])
        features[index] = block.reshape(-1)
    return features


def evaluate(cache_path: Path, layer: int | None = None, depth: int = 24) -> dict:
    """Load one layer, fit j09's HMM, and embed failing routes by the Fisher score."""
    cache_path = Path(cache_path)
    with np.load(cache_path) as cache:
        ids = [str(value) for value in np.asarray(cache["route_id"]).tolist()]
        meta = [json.loads(str(item)) for item in np.asarray(cache["meta"])]
        failing = np.array([not item["success"] for item in meta])
        stored = np.asarray(cache["layers"])
        site = j09._as_str(cache["site"])
        resolved, position = j09.resolve_layer(stored, layer, depth)
        block = np.asarray(cache["frames"][:, position], dtype=np.float64)
        n_frames = np.asarray(cache["n_frames"], dtype=np.int64)
    sequences = j09.scale_and_project(j09.sequences_from_block(block, n_frames))
    chosen, bics, logliks, model = j09.select_model(sequences)
    features = embed_failing(sequences, failing, model)
    name = f"j10-{site}-L{resolved}-fisher"
    axes = j09.cache_methods.axes_from(
        features, failing, ids, name, "ward", (2, 3, 5), seed=0
    )[:10]
    return {
        "method": name,
        "axes": axes,
        "features": features,
        "model": model,
        "chosen": int(chosen),
        "bics": bics,
        "logliks": logliks,
        "ids": ids,
        "failing": failing,
        "sequences": sequences,
        "block": block,
        "n_frames": n_frames,
        "site": site,
        "layer": int(resolved),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("cache", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--layer", type=int, default=None,
                        help="stored layer index; default is round(8/23*(depth-1))")
    parser.add_argument("--depth", type=int, default=24,
                        help="tensor depth used only to pick the default layer")
    args = parser.parse_args()
    result = evaluate(args.cache, args.layer, args.depth)
    settings = vars(args) | {
        "cache": str(args.cache),
        "output": str(args.output),
        "layer": int(result["layer"]),
        "S": int(result["chosen"]),
        "bic": {str(state): float(value) for state, value in result["bics"].items()},
        "loglik": {str(state): float(value) for state, value in result["logliks"].items()},
    }
    payload = {"method": result["method"], "settings": settings, "axes": result["axes"]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=1) + "\n")
    print(json.dumps({
        "S": int(result["chosen"]),
        "bic": {str(state): float(value) for state, value in result["bics"].items()},
        "axes": [len(axis["rollouts"]) for axis in result["axes"]],
    }))


if __name__ == "__main__":
    main()
