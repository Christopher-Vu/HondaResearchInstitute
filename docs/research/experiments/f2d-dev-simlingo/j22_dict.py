#!/usr/bin/env python3
"""j22: a sparse dictionary on single frames, read by what the atoms do late in the window.

m14 trained a dictionary on 6-frame windows and read it with B7's statistics, which need long episodes, and scored
0.000. j22 keeps the dictionary but reads it with a temporal statistic B7 does not use: how much each atom's use rises
in the last frames before the route ends, against the same route's earlier frames.

- Frames: every valid frame of every route (passing and failing) of one layer of the per-frame file, right-aligned
  as j09 reads it. Each unit is standardised over all valid frames, PCA --dims is fit on all valid frames, and the
  scores are divided by their one global root-mean-square.
- Dictionary: sklearn MiniBatchDictionaryLearning, --atoms atoms, fixed --alpha, --seed as random_state, codes by
  lasso_lars at the same alpha (the training objective).
- Statistics per route and atom: the mean absolute code over the last --late valid frames minus the mean over the
  route's earlier valid frames (frames 1-40 of a full 50-frame window), and the share of the last --late frames where
  the atom is active (nonzero code).
- j23 (`--columns change`): only the late-minus-early columns; the late active share is dropped.
- Axes: the columns (2 x atoms, or atoms with --columns change) are standardised over all routes and the failing routes are Ward-clustered at cuts
  2/3/5 (cache_methods.axes_from, A2), in that order, largest first within a cut; top 10.

Only route_id, meta.success, layers, site, frames and n_frames are read, in the file's salted row order.

    PYTHONPATH=src python docs/research/experiments/f2d-dev-simlingo/j22_dict.py FRAMES --output OUT.json
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

import numpy as np
from sklearn.decomposition import PCA, MiniBatchDictionaryLearning


def _load(name: str):
    path = Path(__file__).with_name(f"{name}.py")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


cache_methods = _load("cache_methods")
j09 = _load("j09_hmm")


def reduce_frames(frames: np.ndarray, dims: int) -> np.ndarray:
    """Standardise units over all frames, PCA to `dims`, divide by the scores' global RMS."""
    scores = PCA(n_components=dims, svd_solver="full", random_state=0).fit_transform(cache_methods.standardise(frames))
    rms = float(np.sqrt(np.mean(scores * scores)))
    return scores / rms if rms > 0 else scores


def sparse_codes(z: np.ndarray, atoms: int, alpha: float, seed: int, epochs: int) -> np.ndarray:
    model = MiniBatchDictionaryLearning(n_components=atoms, alpha=alpha, batch_size=256, max_iter=epochs,
                                        transform_algorithm="lasso_lars", transform_alpha=alpha, random_state=seed)
    return model.fit(z).transform(z)


def late_early_statistics(codes: np.ndarray, lengths: list[int], late: int) -> np.ndarray:
    """(routes, 2 * atoms): late-minus-early mean |code| per atom, then the late active share per atom."""
    if min(lengths) <= late:
        raise SystemExit(f"j22: every route needs more than {late} valid frames")
    rows, start = [], 0
    for length in lengths:
        size = np.abs(codes[start:start + length])
        start += length
        early, recent = size[:-late], size[-late:]
        rows.append(np.concatenate([recent.mean(0) - early.mean(0), (recent > 0).mean(0)]))
    return np.asarray(rows)


def j22_axes(sequences: list[np.ndarray], failing: np.ndarray, ids: list[str], name: str, dims: int = 32,
             atoms: int = 64, alpha: float = 1.0, seed: int = 0, epochs: int = 20, late: int = 10,
             columns: str = "both") -> tuple[list, dict]:
    z = reduce_frames(np.concatenate(sequences, axis=0), dims)
    codes = sparse_codes(z, atoms, alpha, seed, epochs)
    statistics = late_early_statistics(codes, [len(s) for s in sequences], late)
    features = cache_methods.standardise(statistics[:, :atoms] if columns == "change" else statistics)
    active = (codes != 0).sum(1)
    fit = {"frames": int(len(z)), "mean_active_atoms_per_frame": float(active.mean()),
           "frames_with_no_active_atom": float(np.mean(active == 0)),
           "atoms_never_used": int(np.sum((codes != 0).sum(0) == 0))}
    return cache_methods.axes_from(features, failing, ids, name, "ward", (2, 3, 5), seed=seed)[:10], fit


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("frames", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--layer", type=int, default=None,
                        help="stored layer index; default is round(8/23*(depth-1)) as in j09")
    parser.add_argument("--depth", type=int, default=24)
    parser.add_argument("--dims", type=int, default=32)
    parser.add_argument("--atoms", type=int, default=64)
    parser.add_argument("--alpha", type=float, default=1.0)
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--late", type=int, default=10)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--columns", choices=("both", "change"), default="both",
                        help="j23: change keeps only the late-minus-early columns")
    parser.add_argument("--name", default="j22")
    args = parser.parse_args()
    with np.load(args.frames) as cache:
        ids = [str(value) for value in np.asarray(cache["route_id"]).tolist()]
        failing = np.array([not json.loads(str(item))["success"] for item in np.asarray(cache["meta"])])
        layer, position = j09.resolve_layer(np.asarray(cache["layers"]), args.layer, args.depth)
        block = np.asarray(cache["frames"][:, position], dtype=np.float64)
        n_frames = np.asarray(cache["n_frames"], dtype=np.int64)
    sequences = j09.sequences_from_block(block, n_frames)
    axes, fit = j22_axes(sequences, failing, ids, args.name, args.dims, args.atoms, args.alpha, args.seed,
                         args.epochs, args.late, args.columns)
    settings = vars(args) | {"frames": str(args.frames), "output": str(args.output), "layer": int(layer)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"method": args.name, "settings": settings, "fit": fit, "axes": axes},
                                      indent=1) + "\n")
    print(json.dumps({"method": args.name, "fit": fit, "axes": [len(axis["rollouts"]) for axis in axes]}))


if __name__ == "__main__":
    main()
