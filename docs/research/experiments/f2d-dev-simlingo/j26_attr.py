#!/usr/bin/env python3
"""j26: cluster failing routes by what a cross-fitted nonlinear pass/fail probe uses, not by their activations.

    PYTHONPATH=src python docs/research/experiments/f2d-dev-simlingo/j26_attr.py FRAMES CACHE --output OUT.json \
        [--seed 0] [--keep-position]

1. Window features: each route's mean over its valid frames of layer 8 (the last 50 frames before the failure step,
   or before the route ends when it passed), standardised over all routes, PCA 32 fit on all routes (m15's input).
2. Position removal (the m19 confound). A passing route's window ends at the route end and a failing route's at the
   failure, so window position differs by outcome. Each window frame gets two positions from the cache's step array,
   log(step since start) and log(1 + steps to the route's end); each route takes their mean over its window. Each
   position is fitted within each outcome separately (four targets), so the outcome gap itself is not what is fitted.
   Directions that predict a target (ridge, 5 folds over the salted order) are removed one at a time, iterative
   nullspace projection, until no target has cross-fitted R2 above TOLERANCE or MAX_DIRECTIONS are gone. The probe sees
   the window features in the remaining orthonormal basis. --keep-position skips this step (diagnostic only).
3. Probe: an MLP (in, 64, 64, 1; GELU; AdamW; balanced BCE; full batch), 5 folds over the salted row order. Every
   route is explained by the fold model that did not see it.
4. Attribution: gradient of the probe's logit times the fold-standardised input, for each held-out route, divided
   by the root-mean-square of that fold's held-out attributions so no fold's logit scale dominates.
5. Axes: Ward on the failing routes' attributions at cuts 2/3/5 (cache_methods.axes_from), top 10 in its label-free
   order (cut order, largest first within a cut). Attribution columns are not standardised: that would lift inputs
   the probe ignores to the size of the ones it uses (tests/test_j26_attr.py has the toy).

Reads frames.npz (route_id, meta.success, meta.failure_step, layers, frames, n_frames) and cache.npz (route_id,
step). No scenario, town, route-config or category field is read. Rows keep the files' salted order.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

import numpy as np
import torch
from sklearn.decomposition import PCA
from sklearn.linear_model import Ridge
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import KFold

DIMS = 32
FOLDS = 5
TOLERANCE = 0.05
MAX_DIRECTIONS = 16
HIDDEN = 64
EPOCHS = 300
LR = 3e-3
WEIGHT_DECAY = 1e-2


def _load(name: str):
    path = Path(__file__).with_name(f"{name}.py")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


cache_methods = _load("cache_methods")


def window_steps(steps: np.ndarray, failure_step: int | None, n_frames: int) -> np.ndarray:
    """Steps of a route's window frames, by cache_pool's rule: the last frames before the failure step."""
    steps = steps[np.isfinite(steps)]
    before = steps[steps < failure_step] if failure_step is not None else steps
    if len(before) == 0:
        before = steps[:1]
    chosen = before[-n_frames:]
    if len(chosen) != n_frames:
        raise SystemExit("j26: window frames do not match the cache's step array")
    return chosen


def frame_positions(steps: np.ndarray, route_end: float) -> np.ndarray:
    """(frames, 2): log step since start and log(1 + steps to the route's end)."""
    return np.column_stack([np.log(steps), np.log1p(route_end - steps)])


def cross_fitted_r2(x: np.ndarray, y: np.ndarray) -> float:
    pred = np.empty_like(y)
    for train, test in KFold(FOLDS).split(x):
        pred[test] = Ridge(alpha=1.0).fit(x[train], y[train]).predict(x[test])
    return float(1 - ((pred - y) ** 2).mean() / y.var())


def position_directions(z: np.ndarray, positions: np.ndarray, outcome: np.ndarray) -> tuple[np.ndarray, list]:
    """Iterative nullspace projection: (dims, k) orthonormal directions that predict a position within either outcome.

    Each (outcome, position) pair is its own target, fitted on that outcome's routes only, so a direction that tracks
    failure step among failing routes is found even when route length among passing routes runs elsewhere. A target
    that is constant within its outcome (steps to the route's end, for passing routes) carries no position and is
    dropped."""
    targets = [(outcome == g, j) for g in (False, True) for j in range(positions.shape[1])
               if np.ptp(positions[outcome == g, j]) > 1e-6]
    removed = np.zeros((z.shape[1], 0))
    history = []
    for _ in range(MAX_DIRECTIONS + 1):
        residual = z - z @ removed @ removed.T
        r2 = [cross_fitted_r2(residual[rows], positions[rows, j]) for rows, j in targets]
        history.append([round(v, 4) for v in r2])
        if max(r2) < TOLERANCE or removed.shape[1] == MAX_DIRECTIONS:
            break
        rows, j = targets[int(np.argmax(r2))]
        w = Ridge(alpha=1.0).fit(residual[rows], positions[rows, j]).coef_
        w = w - removed @ (removed.T @ w)
        removed = np.column_stack([removed, w / np.linalg.norm(w)])
    return removed, history


def complement(removed: np.ndarray, dims: int) -> np.ndarray:
    """(dims, dims - k) orthonormal basis of what the removed directions leave."""
    if removed.shape[1] == 0:
        return np.eye(dims)
    u = np.linalg.svd(removed, full_matrices=True)[0]
    return u[:, removed.shape[1]:]


def _mlp(width: int) -> torch.nn.Module:
    return torch.nn.Sequential(torch.nn.Linear(width, HIDDEN), torch.nn.GELU(), torch.nn.Linear(HIDDEN, HIDDEN),
                               torch.nn.GELU(), torch.nn.Linear(HIDDEN, 1))


def fit_probe(x: np.ndarray, y: np.ndarray, seed: int) -> torch.nn.Module:
    torch.manual_seed(seed)
    model = _mlp(x.shape[1])
    xt, yt = torch.tensor(x, dtype=torch.float32), torch.tensor(y, dtype=torch.float32)
    loss_fn = torch.nn.BCEWithLogitsLoss(pos_weight=torch.tensor((1 - y).sum() / max(y.sum(), 1)))
    optimiser = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=WEIGHT_DECAY)
    for _ in range(EPOCHS):
        optimiser.zero_grad()
        loss_fn(model(xt).squeeze(1), yt).backward()
        optimiser.step()
    return model


def gradient_times_input(model: torch.nn.Module, x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    xt = torch.tensor(x, dtype=torch.float32, requires_grad=True)
    logit = model(xt).squeeze(1)
    logit.sum().backward()
    return (xt.grad * xt).detach().numpy().astype(np.float64), logit.detach().numpy().astype(np.float64)


def cross_fitted_attributions(x: np.ndarray, failing: np.ndarray, seed: int) -> tuple[np.ndarray, np.ndarray]:
    """Per route, attribution and logit from the fold model that did not see it (folds over the salted order)."""
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    attribution, logit = np.zeros_like(x), np.zeros(len(x))
    for fold, (train, test) in enumerate(KFold(FOLDS).split(x)):
        mean, sd = x[train].mean(0), x[train].std(0)
        scale = lambda rows: (x[rows] - mean) / np.where(sd > 0, sd, 1.0)
        model = fit_probe(scale(train), failing[train].astype(np.float64), seed * 100 + fold)
        held_out, logit[test] = gradient_times_input(model, scale(test))
        attribution[test] = held_out / np.sqrt((held_out ** 2).mean())
    return attribution, logit


def window_features(block: np.ndarray, n_frames: np.ndarray, seed: int = 0) -> np.ndarray:
    """Mean over valid frames, standardised over all routes, PCA DIMS fit on all routes."""
    windows = np.stack([block[i, -n:].mean(0) for i, n in enumerate(n_frames)])
    return PCA(n_components=DIMS, random_state=seed).fit_transform(cache_methods.standardise(windows))


def window_positions(steps, failure_steps, n_frames) -> np.ndarray:
    return np.stack([frame_positions(window_steps(steps[i], failure_steps[i], n), float(np.nanmax(steps[i]))).mean(0)
                     for i, n in enumerate(n_frames)])


def j26_features(block, n_frames, steps, failure_steps, failing, seed=0, keep_position=False) -> dict:
    z = window_features(block, n_frames)
    removed, history = (np.zeros((DIMS, 0)), []) if keep_position else position_directions(
        z, window_positions(steps, failure_steps, n_frames), failing)
    x = z @ complement(removed, DIMS)
    attribution, logit = cross_fitted_attributions(x, failing, seed)
    return {"features": attribution, "inputs": x, "logit": logit, "removed": removed.shape[1], "r2_history": history,
            "auroc": float(roc_auc_score(failing, logit))}


def read_inputs(frames_path: Path, cache_path: Path, layer: int) -> dict:
    with np.load(frames_path) as frames, np.load(cache_path) as cache:
        ids = [str(v) for v in frames["route_id"].tolist()]
        if ids != [str(v) for v in cache["route_id"].tolist()]:
            raise SystemExit("j26: frames and cache rows differ")
        meta = [json.loads(str(m)) for m in frames["meta"]]
        position = int(np.flatnonzero(np.asarray(frames["layers"]) == layer)[0])
        return {"ids": ids, "failing": np.array([not m["success"] for m in meta]),
                "failure_steps": [m.get("failure_step") for m in meta],
                "block": np.asarray(frames["frames"][:, position], dtype=np.float64),
                "n_frames": np.asarray(frames["n_frames"], dtype=np.int64),
                "steps": np.asarray(cache["step"], dtype=np.float64)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("frames", type=Path)
    parser.add_argument("cache", type=Path)
    parser.add_argument("--layer", type=int, default=8)
    parser.add_argument("--seed", type=int, default=0, help="probe seed (fold models use seed * 100 + fold)")
    parser.add_argument("--keep-position", action="store_true", help="diagnostic: skip the position removal")
    parser.add_argument("--name", default=None)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    data = read_inputs(args.frames, args.cache, args.layer)
    result = j26_features(data["block"], data["n_frames"], data["steps"], data["failure_steps"], data["failing"],
                          args.seed, args.keep_position)
    name = args.name or f"j26-L{args.layer}-attr-seed{args.seed}"
    axes = cache_methods.axes_from(result["features"], data["failing"], data["ids"], name, "ward", (2, 3, 5))[:10]
    diagnostics = {"directions_removed": result["removed"], "position_r2_history": result["r2_history"],
                   "oof_pass_fail_auroc": round(result["auroc"], 4)}
    settings = vars(args) | {"frames": str(args.frames), "cache": str(args.cache), "output": str(args.output)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"method": name, "settings": settings, "diagnostics": diagnostics,
                                       "axes": axes}, indent=1) + "\n")
    print(json.dumps({"method": name, "axes": [len(a["rollouts"]) for a in axes]} | diagnostics))


if __name__ == "__main__":
    main()
