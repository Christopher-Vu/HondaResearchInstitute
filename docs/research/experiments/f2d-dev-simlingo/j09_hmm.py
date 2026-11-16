#!/usr/bin/env python3
"""j09: diagonal Gaussian HMM on the frame sequence, not the window mean.

Two failing routes that visit the same regimes in opposite orders have the same
window mean, so a mean embedding cannot tell them apart. j09 keeps the order.
Every valid frame of every route (passing and failing) is scaled by one
root-mean-square, then projected with unwhitened PCA. One diagonal-covariance
HMM is fit to those frame sequences. Failing routes are clustered on the
Hellinger embedding of state occupancy and transitions.

    PYTHONPATH=src python docs/research/experiments/f2d-dev-simlingo/j09_hmm.py CACHE \
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
from scipy.special import logsumexp
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA


def _load_cache_methods():
    path = Path(__file__).with_name("cache_methods.py")
    spec = importlib.util.spec_from_file_location("cache_methods", path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


cache_methods = _load_cache_methods()

N_COMPONENTS = 16
N_ITER = 30
CANDIDATES = (4, 6, 8)
VAR_FLOOR = 1e-3


def n_free_parameters(n_states: int) -> int:
    """start (S-1) + transitions S*(S-1) + diagonal Gaussian means and variances."""
    return (n_states - 1) + n_states * (n_states - 1) + 2 * n_states * N_COMPONENTS


def resolve_layer(stored, layer: int | None, depth: int) -> tuple[int, int]:
    """Return (layer index, position in `stored`).

    The default index is round(8/23*(depth-1)). Depth is the --depth argument.
    max(stored)+1 is not a depth.
    """
    stored = np.asarray(stored, dtype=np.int64)
    if layer is None:
        target = int(round((8 / 23) * (depth - 1)))
        how = f"round(8/23*({depth}-1))"
    else:
        target = int(layer)
        how = "--layer"
    hits = np.flatnonzero(stored == target)
    if hits.size == 0:
        raise SystemExit(
            f"j09: layer {target} ({how}) is not in stored layers {stored.tolist()}"
        )
    return target, int(hits[0])


def _as_str(value) -> str:
    if isinstance(value, np.ndarray):
        value = value.item()
    if isinstance(value, bytes):
        return value.decode()
    return str(value)


def sequences_from_block(block: np.ndarray, n_frames: np.ndarray) -> list[np.ndarray]:
    """Right-aligned valid frames. block is (routes, F, width)."""
    frame_count = block.shape[1]
    sequences = []
    for index, count in enumerate(np.asarray(n_frames)):
        count = int(count)
        sequences.append(np.asarray(block[index, frame_count - count:frame_count], dtype=np.float64))
    return sequences


def scale_and_project(sequences: list[np.ndarray]) -> list[np.ndarray]:
    """One RMS over every valid frame, then unwhitened PCA to 16 scores."""
    lengths = [len(seq) for seq in sequences]
    pooled = np.concatenate(sequences, axis=0)
    rms = float(np.sqrt(np.mean(pooled * pooled)))
    if rms == 0.0:
        raise SystemExit("j09: root-mean-square of the valid frames is 0")
    pooled = pooled / rms
    scores = PCA(
        n_components=N_COMPONENTS, svd_solver="full", random_state=0, whiten=False
    ).fit_transform(pooled)
    projected = []
    start = 0
    for length in lengths:
        projected.append(np.ascontiguousarray(scores[start:start + length]))
        start += length
    return projected


def _log_emit(obs: np.ndarray, means: np.ndarray, variances: np.ndarray) -> np.ndarray:
    """Diagonal-Gaussian log density. obs (N, T, D) -> (N, T, S)."""
    inv = 1.0 / variances
    quad = np.einsum("ntd,sd->nts", obs * obs, inv, optimize=True)
    quad += np.sum(means * means * inv, axis=1)
    quad -= 2.0 * np.einsum("ntd,sd->nts", obs, means * inv, optimize=True)
    log_det = np.sum(np.log(2.0 * np.pi * variances), axis=1)
    return -0.5 * (quad + log_det)


def forward_backward(obs, startprob, transmat, means, variances):
    """Scaled log-space forward-backward for one sequence.

    obs is (T, D). Returns log-likelihood, gamma (T, S), and xi (T-1, S, S).
    xi is empty along time when T is 1. gamma sums to 1 over states at each step.
    """
    obs = np.asarray(obs, dtype=np.float64)
    loglik, gamma, xi = _fb_batch(
        obs[None, :, :],
        np.asarray(startprob, dtype=np.float64),
        np.asarray(transmat, dtype=np.float64),
        np.asarray(means, dtype=np.float64),
        np.asarray(variances, dtype=np.float64),
    )
    return float(loglik[0]), gamma[0], xi[0]


def _fb_batch(obs, startprob, transmat, means, variances):
    """obs (N, T, D) -> loglik (N,), gamma (N, T, S), xi (N, T-1, S, S)."""
    n_seq, t_len, _ = obs.shape
    n_states = means.shape[0]
    log_emit = _log_emit(obs, means, variances)
    with np.errstate(divide="ignore"):
        log_pi = np.log(startprob)
        log_a = np.log(transmat)
    log_alpha = np.empty((n_seq, t_len, n_states))
    log_alpha[:, 0, :] = log_emit[:, 0, :] + log_pi
    for t in range(1, t_len):
        mixed = log_alpha[:, t - 1, :, None] + log_a
        log_alpha[:, t, :] = log_emit[:, t, :] + logsumexp(mixed, axis=1)
    loglik = logsumexp(log_alpha[:, -1, :], axis=1)
    log_beta = np.zeros((n_seq, t_len, n_states))
    for t in range(t_len - 2, -1, -1):
        nxt = log_emit[:, t + 1, :] + log_beta[:, t + 1, :]
        mixed = log_a + nxt[:, None, :]
        log_beta[:, t, :] = logsumexp(mixed, axis=2)
    gamma = np.exp(log_alpha + log_beta - loglik[:, None, None])
    if t_len == 1:
        xi = np.zeros((n_seq, 0, n_states, n_states))
    else:
        log_xi = (
            log_alpha[:, :-1, :, None]
            + log_a
            + log_emit[:, 1:, None, :]
            + log_beta[:, 1:, None, :]
            - loglik[:, None, None, None]
        )
        xi = np.exp(log_xi)
    return loglik, gamma, xi


def _batches(sequences: list[np.ndarray]) -> list[np.ndarray]:
    buckets: dict[int, list[np.ndarray]] = {}
    for seq in sequences:
        buckets.setdefault(len(seq), []).append(seq)
    return [np.stack(group, axis=0) for group in buckets.values()]


def _init_params(frames: np.ndarray, n_states: int):
    overall_var = np.var(frames, axis=0)
    kmeans = KMeans(n_clusters=n_states, n_init=1, random_state=0).fit(frames)
    means = np.asarray(kmeans.cluster_centers_, dtype=np.float64)
    variances = np.empty_like(means)
    bump = VAR_FLOOR * overall_var
    for state in range(n_states):
        members = frames[kmeans.labels_ == state]
        if members.shape[0] == 0:
            variances[state] = overall_var
        else:
            variances[state] = np.var(members, axis=0) + bump
    startprob = np.full(n_states, 1.0 / n_states)
    transmat = np.full((n_states, n_states), 0.1 / (n_states - 1))
    np.fill_diagonal(transmat, 0.9)
    return startprob, transmat, means, variances, overall_var


def _e_step(batches, startprob, transmat, means, variances):
    n_states, dim = means.shape
    sum_gamma = np.zeros(n_states)
    sum_gx = np.zeros((n_states, dim))
    sum_gx2 = np.zeros((n_states, dim))
    sum_start = np.zeros(n_states)
    sum_xi = np.zeros((n_states, n_states))
    loglik = 0.0
    for obs in batches:
        ll, gamma, xi = _fb_batch(obs, startprob, transmat, means, variances)
        loglik += float(np.sum(ll))
        sum_gamma += gamma.sum(axis=(0, 1))
        sum_gx += np.einsum("nts,ntd->sd", gamma, obs, optimize=True)
        sum_gx2 += np.einsum("nts,ntd->sd", gamma, obs * obs, optimize=True)
        sum_start += gamma[:, 0].sum(axis=0)
        if xi.shape[1]:
            sum_xi += xi.sum(axis=(0, 1))
    return loglik, sum_gamma, sum_gx, sum_gx2, sum_start, sum_xi


def _m_step(stats, overall_var, prev_means, prev_trans):
    _, sum_gamma, sum_gx, sum_gx2, sum_start, sum_xi = stats
    means = np.array(prev_means, dtype=np.float64, copy=True)
    populated = sum_gamma > 1e-8
    means[populated] = sum_gx[populated] / sum_gamma[populated, None]
    var = np.empty_like(means)
    var[populated] = sum_gx2[populated] / sum_gamma[populated, None] - np.square(means[populated])
    var[~populated] = overall_var
    variances = np.maximum(var, VAR_FLOOR * overall_var)
    startprob = sum_start / sum_start.sum()
    transmat = np.array(prev_trans, dtype=np.float64, copy=True)
    denom = sum_xi.sum(axis=1)
    movable = denom > 0.0
    transmat[movable] = sum_xi[movable] / denom[movable, None]
    return startprob, transmat, means, variances


def fit_hmm(sequences: list[np.ndarray], n_states: int, n_iter: int = N_ITER) -> dict:
    """KMeans init, then exactly n_iter EM steps. No early stop.

    Variances are floored at 1e-3 times the pooled per-dimension variance after
    every M step. The returned loglik is the likelihood of the final parameters.
    """
    frames = np.concatenate(sequences, axis=0)
    startprob, transmat, means, variances, overall_var = _init_params(frames, n_states)
    batches = _batches(sequences)
    for _ in range(n_iter):
        stats = _e_step(batches, startprob, transmat, means, variances)
        startprob, transmat, means, variances = _m_step(stats, overall_var, means, transmat)
    loglik, *_rest = _e_step(batches, startprob, transmat, means, variances)
    return {
        "startprob": startprob,
        "transmat": transmat,
        "means": means,
        "variances": variances,
        "loglik": float(loglik),
    }


def select_model(sequences: list[np.ndarray]) -> tuple[int, dict[int, float], dict[int, float], dict]:
    """BIC over S in {4, 6, 8}. Smallest BIC wins; a tie keeps the smaller S."""
    n_frames = sum(len(seq) for seq in sequences)
    log_n = float(np.log(n_frames))
    bics: dict[int, float] = {}
    logliks: dict[int, float] = {}
    chosen = None
    chosen_model = None
    best_bic = None
    for n_states in CANDIDATES:
        model = fit_hmm(sequences, n_states)
        bic = -2.0 * model["loglik"] + n_free_parameters(n_states) * log_n
        bics[n_states] = float(bic)
        logliks[n_states] = float(model["loglik"])
        if best_bic is None or bic < best_bic:
            best_bic = bic
            chosen = n_states
            chosen_model = model
    return int(chosen), bics, logliks, chosen_model


def hellinger_feature(gamma: np.ndarray, xi: np.ndarray) -> np.ndarray:
    """sqrt(concat(mean_t gamma_t, normalised sum_t xi_t)). Zeros if T is 1."""
    occupancy = np.mean(gamma, axis=0)
    n_states = gamma.shape[1]
    if gamma.shape[0] == 1:
        trans = np.zeros((n_states, n_states))
    else:
        total = float(np.sum(xi))
        trans = np.zeros((n_states, n_states)) if total == 0.0 else np.sum(xi, axis=0) / total
    return np.sqrt(np.concatenate([occupancy, np.ravel(trans)]))


def embed_failing(sequences: list[np.ndarray], failing: np.ndarray, model: dict) -> np.ndarray:
    n_states = model["means"].shape[0]
    features = np.zeros((len(sequences), n_states + n_states * n_states))
    buckets: dict[int, list[int]] = {}
    for index, seq in enumerate(sequences):
        if failing[index]:
            buckets.setdefault(len(seq), []).append(index)
    for indexes in buckets.values():
        obs = np.stack([sequences[index] for index in indexes], axis=0)
        _ll, gamma, xi = _fb_batch(
            obs, model["startprob"], model["transmat"], model["means"], model["variances"]
        )
        for row, index in enumerate(indexes):
            features[index] = hellinger_feature(gamma[row], xi[row])
    return features


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("cache", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--layer", type=int, default=None,
                        help="stored layer index; default is round(8/23*(depth-1))")
    parser.add_argument("--depth", type=int, default=24,
                        help="tensor depth used only to pick the default layer")
    args = parser.parse_args()
    with np.load(args.cache) as cache:
        ids = [str(value) for value in np.asarray(cache["route_id"]).tolist()]
        meta = [json.loads(str(item)) for item in np.asarray(cache["meta"])]
        failing = np.array([not item["success"] for item in meta])
        stored = np.asarray(cache["layers"])
        site = _as_str(cache["site"])
        layer, position = resolve_layer(stored, args.layer, args.depth)
        block = np.asarray(cache["frames"][:, position], dtype=np.float64)
        n_frames = np.asarray(cache["n_frames"], dtype=np.int64)
    sequences = scale_and_project(sequences_from_block(block, n_frames))
    chosen, bics, logliks, model = select_model(sequences)
    features = embed_failing(sequences, failing, model)
    name = f"j09-{site}-L{layer}-hmm"
    axes = cache_methods.axes_from(features, failing, ids, name, "ward", (2, 3, 5), seed=0)[:10]
    settings = vars(args) | {
        "cache": str(args.cache),
        "output": str(args.output),
        "layer": int(layer),
        "S": int(chosen),
        "bic": {str(state): float(value) for state, value in bics.items()},
        "loglik": {str(state): float(value) for state, value in logliks.items()},
    }
    payload = {"method": name, "settings": settings, "axes": axes}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=1) + "\n")
    print(json.dumps({
        "S": int(chosen),
        "bic": {str(state): float(value) for state, value in bics.items()},
        "axes": [len(axis["rollouts"]) for axis in axes],
    }))


if __name__ == "__main__":
    main()
