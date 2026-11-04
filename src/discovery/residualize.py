"""Action-residual orthogonalization (PRD 9.2): remove from the action-query states what pooled vision predicts.

    PYTHONPATH=src python -m discovery.residualize SHARD_DIR [...] --layer 10 --model MODEL.npz --output OUT_DIR

Ridge-regresses the `driving_queries` frame means at one layer on the `vision_bridge` frame means, fitted on the
frames of successful rollouts, and writes shards holding the residual. Downstream code reads those shards like any
others, so the variant needs no change in the SAE trainer, contrastive diffing or probe-residual: a directive's
variant follows from the sidecars' `preprocessing` field. With an existing MODEL.npz nothing is refitted and no
outcome is read, which is how a frozen fit reaches a test pool whose outcome labels may not tune anything (PRD 9.2).

Interpretations, pending sign-off (PRD 9.2 is silent on these):
1. "Pooled visual tokens" is `vision_bridge`, InternVL's projector output averaged over its tokens, chosen because it
   is the only purely visual site in the shards. The handoff's M3 table pools visual tokens at the same decoder layer.
   The shards can approximate that: `all_tokens` and `driving_queries` are means over known token counts, so their
   difference recovers the mean of every other position, with prompt tokens mixed in with the visual ones. This is a
   choice for Chris to confirm, and only `vision_bridge` is built.
2. The fit is StandardScaler + RidgeCV over the alphas probe-residual uses, one alpha for all hidden units.
3. An output shard keeps `step` and the state arrays, drops the other sites and the per-token capture, and stores the
   residual at its original layer index in float32 with NaN at the layers below, so `--layer` means the same thing
   and reading any other layer fails loudly. Its episode mean is the residual of the two episode means, which equals
   the mean residual over every step because the fit is linear.
4. Rollouts with no outcome are not written, since every reader skips them.

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
from harness.schema import ACTION_RESIDUAL
from harness.shards import EPISODE_MEAN, TOKEN_ARRAYS

QUERY_SITE, VISUAL_SITE = "driving_queries", "vision_bridge"


@dataclass
class ActionResidual:
    """A frozen fit: decoded = (visual - mean) / scale @ coef.T + intercept."""
    layer: int
    mean: np.ndarray
    scale: np.ndarray
    coef: np.ndarray
    intercept: np.ndarray
    alpha: float
    success_frames: int
    explained_on_fit: float

    def residual(self, queries: np.ndarray, visual: np.ndarray) -> np.ndarray:
        return queries - ((visual - self.mean) / self.scale) @ self.coef.T - self.intercept

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez(path, layer=self.layer, mean=self.mean, scale=self.scale, coef=self.coef, intercept=self.intercept,
                 alpha=self.alpha, success_frames=self.success_frames, explained_on_fit=self.explained_on_fit)

    @classmethod
    def load(cls, path: Path) -> "ActionResidual":
        with np.load(path) as saved:
            return cls(int(saved["layer"]), saved["mean"], saved["scale"], saved["coef"], saved["intercept"],
                       float(saved["alpha"]), int(saved["success_frames"]), float(saved["explained_on_fit"]))


def sidecars(shard_dirs: list[Path]) -> list[Path]:
    return sorted(path for directory in shard_dirs for path in Path(directory).glob("*.json"))


def require_visual(archive: np.lib.npyio.NpzFile, sidecar: Path) -> None:
    if VISUAL_SITE not in archive.files:
        raise ValueError(f"{sidecar.stem} has no {VISUAL_SITE}: the residual needs a capture that logged it")


def read_sites(sidecar: Path, layer: int) -> tuple[np.ndarray, np.ndarray]:
    with np.load(sidecar.with_suffix(".npz")) as archive:
        require_visual(archive, sidecar)
        return archive[QUERY_SITE][:, layer].astype(np.float64), archive[VISUAL_SITE].astype(np.float64)


def fit(shard_dirs: list[Path], layer: int) -> ActionResidual:
    """Fit on every logged frame of every successful rollout; failures and rollouts with no outcome play no part."""
    successes = [path for path in sidecars(shard_dirs) if json.loads(path.read_text()).get("success") is True]
    if not successes:
        raise ValueError(f"no successful rollout in {shard_dirs} to fit the residual on")
    queries, visual = zip(*(read_sites(path, layer) for path in successes))
    targets, features = np.concatenate(queries), np.concatenate(visual)
    pipeline = make_pipeline(StandardScaler(), RidgeCV(alphas=RIDGE_ALPHAS)).fit(features, targets)
    scaler, ridge = pipeline.steps[0][1], pipeline.steps[1][1]
    return ActionResidual(layer, scaler.mean_, scaler.scale_, ridge.coef_, ridge.intercept_, float(ridge.alpha_),
                          len(targets), float(pipeline.score(features, targets)))


def residual_arrays(archive: np.lib.npyio.NpzFile, model: ActionResidual) -> dict[str, np.ndarray]:
    queries, visual = archive[QUERY_SITE], archive[VISUAL_SITE].astype(np.float64)
    stored = np.full((len(queries), model.layer + 1, queries.shape[-1]), np.nan, dtype=np.float32)
    stored[:, model.layer] = model.residual(queries[:, model.layer].astype(np.float64), visual)
    mean = np.full((model.layer + 1, queries.shape[-1]), np.nan, dtype=np.float32)
    mean[model.layer] = model.residual(archive[QUERY_SITE + EPISODE_MEAN][model.layer].astype(np.float64),
                                       archive[VISUAL_SITE + EPISODE_MEAN].astype(np.float64))
    return {QUERY_SITE: stored, QUERY_SITE + EPISODE_MEAN: mean}


def write_shard(sidecar: Path, model: ActionResidual, output: Path) -> bool:
    """Write one residual shard; False, writing nothing, when the rollout has no outcome."""
    meta = json.loads(sidecar.read_text())
    if meta.get("success") is None:
        return False
    with np.load(sidecar.with_suffix(".npz")) as archive:
        require_visual(archive, sidecar)
        kept = {name: archive[name] for name in archive.files
                if name not in TOKEN_ARRAYS and not name.endswith(EPISODE_MEAN) and archive[name].ndim == 1}
        arrays = {**kept, **residual_arrays(archive, model)}
    np.savez_compressed(output / f"{sidecar.stem}.npz", **arrays)
    tagged = {**meta, "preprocessing": ACTION_RESIDUAL, "residualized_layer": model.layer,
              "residualized_from": str(sidecar.parent)}
    (output / f"{sidecar.stem}.json").write_text(json.dumps(tagged, indent=2) + "\n")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("shards", type=Path, nargs="+")
    parser.add_argument("--layer", type=int, required=True)
    parser.add_argument("--model", type=Path, required=True, help="the fit: read if it exists, otherwise fitted here")
    parser.add_argument("--output", type=Path, required=True, help="directory for the residual shards")
    args = parser.parse_args()
    if args.model.is_file():
        model = ActionResidual.load(args.model)
        if model.layer != args.layer:
            parser.error(f"{args.model} was fitted at layer {model.layer}, not {args.layer}")
    else:
        model = fit(args.shards, args.layer)
        model.save(args.model)
    args.output.mkdir(parents=True, exist_ok=True)
    written = sum(write_shard(path, model, args.output) for path in sidecars(args.shards))
    print(json.dumps({"layer": model.layer, "alpha": model.alpha, "success_frames": model.success_frames,
                      "explained_on_fit": model.explained_on_fit, "shards_written": written}))


if __name__ == "__main__":
    main()
