#!/usr/bin/env python3
"""Sprint batch 4 methods on the per-frame file (frames_pool.py): m29 to m32, m35 and m36 (VARIANTS.md).

    PYTHONPATH=src python docs/research/experiments/f2d-dev-simlingo/frames_methods.py FRAMES --mode multiscale \
        --output OUT.json

FRAMES holds one site's last 50 frames before the failure step (or the end) at layers 5, 8, 10 and 20, right-aligned
and NaN-padded, with ego speed per frame. Pass/fail is read from meta.success; nothing else about a route is read.
Every mode builds one feature row per route, then the failing routes go through cache_methods.axes_from (Ward 2/3/5,
amendment A2's distinct-axis rule), first 10 axes.
- multiscale (m29): means of the last 5, 20 and 50 frames, concatenated, standardised, PCA 32.
- trend (m30): every frame projected on a PCA 16 fit to all frames; per route the mean and least-squares slope over
  time of each component.
- stopped (m31): mean of frames with speed below 0.5 m/s and mean of the others (zero, the pool average after
  standardising, when a route has none), concatenated, standardised, PCA 32, plus the stopped share.
- spread (m32): mean and standard deviation over the frames, concatenated, standardised, PCA 32.
- hmm+mean (m35): j09's HMM embedding beside the 50-frame mean's PCA 32, each block standardised and weighted equally.
- hmm-multi (m36): j09's pipeline on frames that concatenate the stored layers in --layer, each standardised.
--layer picks stored layers by index (default 8).
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

import numpy as np
from sklearn.decomposition import PCA


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(f"{name}.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


cache_methods = _load("cache_methods")
standardise = cache_methods.standardise


def valid(block: np.ndarray, n_frames: np.ndarray) -> list[np.ndarray]:
    return [block[i, block.shape[1] - int(n):].astype(np.float64) for i, n in enumerate(n_frames)]


def pca(x: np.ndarray, dims: int = 32) -> np.ndarray:
    return PCA(n_components=min(dims, *x.shape), random_state=0).fit_transform(standardise(x))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("frames", type=Path)
    parser.add_argument("--mode", choices=("multiscale", "trend", "stopped", "spread", "hmm+mean", "hmm-multi"),
                        required=True)
    parser.add_argument("--layer", type=int, nargs="+", default=[8])
    parser.add_argument("--name")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with np.load(args.frames) as cache:
        ids = [str(r) for r in cache["route_id"]]
        failing = np.array([not json.loads(str(m))["success"] for m in cache["meta"]])
        stored = [int(l) for l in cache["layers"]]
        slots = [stored.index(l) for l in args.layer]
        frames = np.asarray(cache["frames"][:, slots], dtype=np.float32)  # (routes, layers, F, width)
        n_frames = np.asarray(cache["n_frames"])
        speed = np.asarray(cache["ego_speed"])
    # each layer standardised over every valid frame of every route, then layers side by side per frame
    for j in range(frames.shape[1]):
        rows = np.concatenate([s for s in valid(frames[:, j], n_frames)])
        mu, sd = rows.mean(0), rows.std(0)
        frames[:, j] = (frames[:, j] - mu) / np.where(sd > 0, sd, 1.0)
    block = np.concatenate([frames[:, j] for j in range(frames.shape[1])], axis=-1)  # (routes, F, layers*width)
    seqs = valid(block, n_frames)
    mode = args.mode
    if mode == "multiscale":
        features = pca(np.hstack([np.stack([s[-w:].mean(0) for s in seqs]) for w in (5, 20, 50)]))
    elif mode == "trend":
        proj = PCA(n_components=16, random_state=0).fit(np.concatenate(seqs))
        rows = []
        for s in seqs:
            z = proj.transform(s)
            t = np.arange(len(z)) - (len(z) - 1) / 2
            slope = (t @ (z - z.mean(0))) / max(float(t @ t), 1.0)
            rows.append(np.r_[z.mean(0), slope])
        features = standardise(np.array(rows))
    elif mode == "stopped":
        rows, share = [], []
        for i, s in enumerate(seqs):
            v = speed[i, len(speed[i]) - len(s):]
            stop = v < 0.5
            rows.append(np.r_[s[stop].mean(0) if stop.any() else np.zeros(s.shape[1]),
                              s[~stop].mean(0) if (~stop).any() else np.zeros(s.shape[1])])
            share.append(stop.mean())
        z = standardise(pca(np.array(rows)))
        features = np.hstack([z / np.sqrt(z.shape[1]), standardise(np.array(share)[:, None])])
    elif mode == "spread":
        features = pca(np.hstack([np.stack([s.mean(0) for s in seqs]), np.stack([s.std(0) for s in seqs])]))
    else:
        j09 = _load("j09_hmm")
        sequences = j09.scale_and_project(seqs)
        chosen, _, _, model = j09.select_model(sequences)
        hmm = j09.embed_failing(sequences, failing, model)
        if mode == "hmm+mean":
            z = standardise(pca(np.stack([s.mean(0) for s in seqs])))
            h = standardise(hmm)
            features = np.hstack([h / np.sqrt(h.shape[1]), z / np.sqrt(z.shape[1])])
        else:
            features = hmm
    name = args.name or f"frames-{mode}-L{'+'.join(map(str, args.layer))}"
    axes = cache_methods.axes_from(features, failing, ids, name, "ward", cache_methods.CUTS)[:10]
    out = {"method": name, "frames_settings": vars(args) | {"frames": str(args.frames), "output": str(args.output)},
           "axes": axes}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({"method": name, "axes": [len(a["rollouts"]) for a in axes]}))


if __name__ == "__main__":
    main()
