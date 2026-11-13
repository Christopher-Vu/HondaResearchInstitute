#!/usr/bin/env python3
"""H24's grouping: an error-aware Gaussian mixture in the manner of Domino (Eyuboglu et al., ICLR 2022), re-implemented.

    python docs/research/experiments/h24-error-aware-grouping/mixture.py features.npz --output axes.json

Each component models the route's features (diagonal Gaussian) and its outcome (Bernoulli). In the E-step the outcome's
log-likelihood is weighted by GAMMA. GAMMA was fixed at 1 on synthetic pools shaped like the real ones (groups of 8, 5
and 3 failures among about 50, tests/test_h24_grouping.py), before any real data: there 0 and 1 recovered the groups
about equally, while 3 and 10 merged failures into one large group (median largest axis 25 to 36 against 9 to 11).
The `act_gamma0` arm (no outcome term, a plain mixture) shows whether the error-aware term changes anything.
Never reads a key: only features, route ids and outcomes.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA

GAMMA = 1.0
ARMS = {"act": (("act",), GAMMA), "act_gamma0": (("act",), 0.0), "kin": (("kin",), GAMMA), "full": (("full",), GAMMA),
        "act+kin": (("act", "kin"), GAMMA)}
COMPONENTS, PCA_DIMS, MAX_ITER, TOL, REG, BUDGET = 10, 32, 300, 1e-6, 1e-3, 10
SEEDS = range(18)


def standardise(matrix: np.ndarray) -> np.ndarray:
    spread = matrix.std(axis=0)
    return np.where(spread > 0, (matrix - matrix.mean(axis=0)) / np.where(spread > 0, spread, 1), 0.0)


def block(matrix: np.ndarray) -> np.ndarray:
    """Standardised, reduced to at most PCA_DIMS components, scaled to unit total variance so blocks weigh equally."""
    z = standardise(matrix.astype(np.float64))
    dims = min(PCA_DIMS, z.shape[0] - 1, z.shape[1])
    if dims < z.shape[1]:
        z = PCA(n_components=dims, random_state=0).fit_transform(z)
    total = z.var(axis=0).sum()
    return z / np.sqrt(total) if total > 0 else z


def embed(data: dict[str, np.ndarray], names: tuple[str, ...]) -> np.ndarray:
    return np.hstack([block(data[name]) for name in names])


def log_gauss(z: np.ndarray, mean: np.ndarray, var: np.ndarray) -> np.ndarray:
    return -0.5 * (((z[:, None, :] - mean[None]) ** 2 / var[None]).sum(-1) + np.log(2 * np.pi * var).sum(-1)[None])


def fit(z: np.ndarray, failed: np.ndarray, seed: int, gamma: float = GAMMA) -> np.ndarray:
    """Most likely component per route."""
    n = len(z)
    k = min(COMPONENTS, n)
    resp = np.eye(k)[KMeans(k, n_init=10, random_state=seed).fit_predict(z)]
    y = failed.astype(np.float64)
    previous = -np.inf
    for _ in range(MAX_ITER):
        weight = resp.sum(axis=0) + 1e-10
        prior = weight / n
        mean = resp.T @ z / weight[:, None]
        var = np.maximum(resp.T @ z ** 2 / weight[:, None] - mean ** 2, 0) + REG
        rate = (resp.T @ y + 1) / (weight + 2)
        outcome = y[:, None] * np.log(rate)[None] + (1 - y[:, None]) * np.log(1 - rate)[None]
        log_resp = np.log(prior)[None] + log_gauss(z, mean, var) + gamma * outcome
        top = log_resp.max(axis=1, keepdims=True)
        total = top[:, 0] + np.log(np.exp(log_resp - top).sum(axis=1))
        resp = np.exp(log_resp - total[:, None])
        objective = total.mean()
        if abs(objective - previous) < TOL:
            break
        previous = objective
    return resp.argmax(axis=1)


def axes(ids: np.ndarray, failed: np.ndarray, assign: np.ndarray) -> list[list[str]]:
    groups = []
    for component in np.unique(assign):
        members = assign == component
        failing = sorted(str(i) for i in ids[members & failed])
        if failing:
            groups.append((-len(failing) / members.sum(), -len(failing), int(component), failing))
    return [group[3] for group in sorted(groups)[:BUDGET]]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("features", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with np.load(args.features) as archive:
        data = {name: archive[name] for name in archive.files}
    ids, failed = data["ids"], data["failed"].astype(bool)
    out = {}
    for name, (blocks, gamma) in ARMS.items():
        z = embed(data, blocks)
        out[f"H24_{name}"] = [{"run": seed, "axes": axes(ids, failed, fit(z, failed, seed, gamma))} for seed in SEEDS]
        print(name, z.shape, [len(run["axes"]) for run in out[f"H24_{name}"]])
    args.output.write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main()
