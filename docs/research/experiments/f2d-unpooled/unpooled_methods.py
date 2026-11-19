#!/usr/bin/env python3
"""The unpooled grid's rows (protocol.md in this folder): per-route features from replay_unpooled.py's files, then
m03 (cache_methods.py: standardise, PCA 32 on all routes, Ward on the failing routes, A2 axes, top 10).

    PYTHONPATH=src python docs/research/experiments/f2d-unpooled/unpooled_methods.py REPLAY_DIR OUT_DIR \
        [--sites vit llm10 dq dino] [--aggregations max topk codebook mean] [--restrict IDS.txt]

Writes OUT_DIR/<site>-<aggregation>.json (sprint method format) and OUT_DIR/features.npz (route ids, failing flag
and every row's route features, for the probe ceiling). Window: the last WINDOW saved frames before the failure step,
or the route's last WINDOW. Codebook: MiniBatchKMeans, k = 64, seed 0, on up to SAMPLE tokens drawn evenly from
every route's projected tokens; the feature is the route's normalised code histogram. Every fit is label-free and on
the routes given (all routes with a replay file, or --restrict).
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
from sklearn.cluster import MiniBatchKMeans

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("cache_methods", HERE.parent / "f2d-dev-simlingo/cache_methods.py")
cm = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cm)
WINDOW, K, SAMPLE, SALT = 25, 64, 200_000, "f2d-cache-v1"  # SALT and order as cache_pool.py


def window(steps: np.ndarray, failed: int) -> np.ndarray:
    before = np.flatnonzero(steps < failed) if failed >= 0 else np.arange(len(steps))
    return (before if len(before) else np.arange(1))[-WINDOW:]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("replay", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--sites", nargs="+", default=["vit", "llm10", "dq", "dino"])
    parser.add_argument("--aggregations", nargs="+", default=["max", "topk", "codebook", "mean"])
    parser.add_argument("--restrict", type=Path)
    args = parser.parse_args()
    files = sorted(args.replay.glob("*.npz"), key=lambda p: hashlib.sha256((SALT + p.stem).encode()).hexdigest())
    if args.restrict:
        wanted = set(args.restrict.read_text().split())
        files = [f for f in files if f.stem in wanted]
    ids, failing = [p.stem for p in files], []
    feats: dict[str, list] = {}
    codes: dict[str, list] = {s: [] for s in args.sites}
    for path in files:
        with np.load(path) as z:
            failing.append(not bool(z["success"]))
            w = window(z["step"], int(z["failure_step"]))
            for s in args.sites:
                if "max" in args.aggregations:
                    feats.setdefault(f"{s}-max", []).append(z[f"{s}_max"][w].astype(np.float32).max(0))
                for agg in ("topk", "mean"):
                    if agg in args.aggregations:
                        feats.setdefault(f"{s}-{agg}", []).append(z[f"{s}_{agg}"][w].astype(np.float32).mean(0))
                if "codebook" in args.aggregations:
                    codes[s].append(z[f"{s}_codes"].reshape(-1, z[f"{s}_codes"].shape[-1]))
    failing = np.array(failing)
    rng = np.random.default_rng(0)
    for s in args.sites:
        if "codebook" not in args.aggregations:
            break
        per = max(1, SAMPLE // len(codes[s]))
        sample = np.concatenate([c[rng.choice(len(c), min(per, len(c)), replace=False)] for c in codes[s]])
        km = MiniBatchKMeans(n_clusters=K, random_state=0, batch_size=4096, n_init=3).fit(sample.astype(np.float32))
        feats[f"{s}-codebook"] = [np.bincount(km.predict(c.astype(np.float32)), minlength=K) / len(c) for c in codes[s]]
    args.out.mkdir(parents=True, exist_ok=True)
    arrays = {}
    for name, rows in feats.items():
        x = np.stack(rows)
        arrays[name] = x
        z = cm.standardise(cm.embed("m03", x, failing, 32, 16, 0))
        axes = cm.axes_from(z, failing, ids, name)[:10]
        (args.out / f"{name}.json").write_text(json.dumps({"method": name, "settings": {"replay": str(args.replay),
                                                           "window": WINDOW, "routes": len(ids)}, "axes": axes}, indent=1) + "\n")
        print(json.dumps({"row": name, "width": x.shape[1], "axes": [len(a["rollouts"]) for a in axes]}), flush=True)
    np.savez(args.out / "features.npz", route_id=np.array(ids), failing=failing, **arrays)


if __name__ == "__main__":
    main()
