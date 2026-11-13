"""Controls for the action residual (H18): what residualization removes, without the visual fit.

    PYTHONPATH=src python -m discovery.residual_controls shuffle SHARD_DIR [...] --layer 10 --seed 18 --output OUT_DIR
    PYTHONPATH=src python -m discovery.residual_controls top-variance SHARD_DIR [...] --layer 10 \
        --match MODEL.npz --output OUT_DIR
    PYTHONPATH=src python -m discovery.residual_controls centre SHARD_DIR [...] --layer 10 --output OUT_DIR

`shuffle` fits the same ridge as `residualize`, with the visual frames permuted against the query frames, so it keeps the
fit's form and removes nearly nothing that vision predicts. `top-variance` removes the leading principal components of
the success frames' query states, as many as it takes to reach the share of total variance the real fit removes from
those frames, so it removes as much variance as residualization does with no reference to vision. That share is
variance-weighted; the fit's own `explained_on_fit` is sklearn's per-unit average R squared, a different number. Both write shards the way `residualize` does,
tagged `residual_control` beside `preprocessing`, so the same downstream code reads them. `centre` removes only the
success frames' mean, the part of `shuffle` that H18 found carries much of the residualization gain.

Must never read the answer key. CI-enforced; see scripts/check_sealed_imports.py.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from sklearn.linear_model import RidgeCV
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from discovery.probe_residual import RIDGE_ALPHAS
from discovery.residualize import ActionResidual, read_sites, sidecars, write_shard


def success_sites(shard_dirs: list[Path], layer: int) -> tuple[np.ndarray, np.ndarray]:
    successes = [path for path in sidecars(shard_dirs) if json.loads(path.read_text()).get("success") is True]
    if not successes:
        raise ValueError(f"no successful rollout in {shard_dirs} to fit the control on")
    queries, visual = zip(*(read_sites(path, layer) for path in successes))
    return np.concatenate(queries), np.concatenate(visual)


def shuffled_fit(shard_dirs: list[Path], layer: int, seed: int) -> ActionResidual:
    targets, features = success_sites(shard_dirs, layer)
    features = features[np.random.default_rng(seed).permutation(len(features))]
    pipeline = make_pipeline(StandardScaler(), RidgeCV(alphas=RIDGE_ALPHAS)).fit(features, targets)
    scaler, ridge = pipeline.steps[0][1], pipeline.steps[1][1]
    return ActionResidual(layer, scaler.mean_, scaler.scale_, ridge.coef_, ridge.intercept_, float(ridge.alpha_),
                          len(targets), float(pipeline.score(features, targets)))


@dataclass
class TopVarianceRemoval:
    """Removes the mean and the span of `components` (orthonormal rows) from the query states; vision is ignored."""
    layer: int
    mean: np.ndarray
    components: np.ndarray
    explained_on_fit: float

    def residual(self, queries: np.ndarray, visual: np.ndarray) -> np.ndarray:
        centred = queries - self.mean
        return centred - centred @ self.components.T @ self.components


def removed_share(model: ActionResidual, queries: np.ndarray, visual: np.ndarray) -> float:
    """The share of the queries' total variance that the real fit removes: variance-weighted, unlike `explained_on_fit`."""
    kept = model.residual(queries, visual)
    return float(1 - np.sum((kept - kept.mean(axis=0)) ** 2) / np.sum((queries - queries.mean(axis=0)) ** 2))


def top_variance_fit(shard_dirs: list[Path], layer: int, target: float) -> TopVarianceRemoval:
    """The fewest leading components whose share of the success frames' variance reaches `target`."""
    targets, _ = success_sites(shard_dirs, layer)
    mean = targets.mean(axis=0)
    _, singular, rows = np.linalg.svd(targets - mean, full_matrices=False)
    shares = np.cumsum(singular ** 2) / np.sum(singular ** 2)
    count = int(np.searchsorted(shares, target) + 1)
    return TopVarianceRemoval(layer, mean, rows[:count], float(shares[count - 1]))


def centre_fit(shard_dirs: list[Path], layer: int) -> TopVarianceRemoval:
    """Removes the success frames' mean and nothing else."""
    targets, _ = success_sites(shard_dirs, layer)
    return TopVarianceRemoval(layer, targets.mean(axis=0), np.zeros((0, targets.shape[1])), 0.0)


def write_control_shards(shard_dirs: list[Path], model, control: str, output: Path) -> int:
    output.mkdir(parents=True, exist_ok=True)
    written = 0
    for sidecar in sidecars(shard_dirs):
        if write_shard(sidecar, model, output):
            tagged = output / f"{sidecar.stem}.json"
            tagged.write_text(json.dumps({**json.loads(tagged.read_text()), "residual_control": control}, indent=2) + "\n")
            written += 1
    return written


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("control", choices=["shuffle", "top-variance", "centre"])
    parser.add_argument("shards", type=Path, nargs="+")
    parser.add_argument("--layer", type=int, required=True)
    parser.add_argument("--seed", type=int, default=18, help="shuffle only: the permutation's seed")
    parser.add_argument("--match", type=Path, help="top-variance only: the residualize fit whose explained share to match")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.control == "centre":
        model = centre_fit(args.shards, args.layer)
        summary = {"removed": "success-frame mean"}
    elif args.control == "shuffle":
        model = shuffled_fit(args.shards, args.layer, args.seed)
        summary = {"alpha": model.alpha, "explained_on_fit": model.explained_on_fit}
    else:
        if args.match is None:
            parser.error("top-variance needs --match, the residualize fit whose explained share it matches")
        real = ActionResidual.load(args.match)
        if real.layer != args.layer:
            parser.error(f"{args.match} was fitted at layer {real.layer}, not {args.layer}")
        target = removed_share(real, *success_sites(args.shards, args.layer))
        model = top_variance_fit(args.shards, args.layer, target)
        summary = {"components": len(model.components), "removed_share": model.explained_on_fit,
                   "real_removed_share": target, "real_explained_on_fit": real.explained_on_fit}
    written = write_control_shards(args.shards, model, args.control, args.output)
    print(json.dumps({"control": args.control, "layer": args.layer, **summary, "shards_written": written}))


if __name__ == "__main__":
    main()
