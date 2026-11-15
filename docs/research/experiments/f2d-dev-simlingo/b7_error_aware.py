#!/usr/bin/env python3
"""Sprint m01 and m02 (VARIANTS.md batch 1): error-aware B7 on v1's dictionaries, whole route and approach window.

    PYTHONPATH=src python docs/research/experiments/f2d-dev-simlingo/b7_error_aware.py SHARDS --layer 10 \
        --sae RUN/sae/L10_k64_s0 RUN/sae/L10_k32_s0 --output-dir OUT

B7-pool (variant B, the pool as its own statistics set) with one change: latents are ranked by z(kappa) plus
z(log enrichment), where enrichment is the failing share of the latent's fire set over the pool's failing share. The
pass/fail outcome is a fleet signal; the failure type stays hidden. Then B7's own merge and axes. m02 runs the same on
the approach window only: the last 6 captured frames before the failure step, or before the end when it passed.
The shards are read once for every dictionary and both windows; one file per method and dictionary.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import torch

from baselines.activation_stats import (ActivationStatsConfig, LatentScores, _fire_sets, _zscore, build_axes,
                                        latent_scores, merge_latents)
from discovery.dev_eval import encode_frames, load_sae, load_shards, read_frames

WINDOW = 6


def window(latents: np.ndarray, steps: np.ndarray, failure_step: int | None) -> np.ndarray:
    keep = steps < failure_step if failure_step is not None else np.ones(len(steps), bool)
    rows = latents[keep] if keep.any() else latents[:1]
    return rows[-WINDOW:]


def error_aware(episodes: dict[str, np.ndarray], failing: set[str], cfg: ActivationStatsConfig) -> list[set[str]]:
    scores = latent_scores(episodes, cfg)
    fired = _fire_sets(episodes, cfg.tau_on)
    base = len(failing) / len(episodes)
    enrich = np.array([(len(fired.get(int(l), set()) & failing) / max(1, len(fired.get(int(l), set()))) + 1e-3) / base
                       for l in scores.latent_ids])
    combined = _zscore(scores.kappa) + _zscore(np.log(enrich))
    order = np.lexsort((scores.latent_ids, -combined))
    ranked = LatentScores(scores.latent_ids[order], combined[order])
    axes = build_axes(merge_latents(ranked, episodes, cfg), episodes, failing, cfg)
    return [card.rollouts for card in axes]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("shards", type=Path)
    parser.add_argument("--layer", type=int, default=10)
    parser.add_argument("--sae", type=Path, nargs="+", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    frames = [read_frames(shard, args.layer) for shard in load_shards([args.shards])]
    failing = {f.rollout_id for f in frames if f.failed}
    cfg = ActivationStatsConfig(variant="B")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for run in args.sae:
        model, _ = load_sae(run, device)
        rollouts, explained = encode_frames(model, frames, device)
        views = {"m01": {r.rollout_id: r.latents for r in rollouts},
                 "m02": {r.rollout_id: window(r.latents, r.steps, r.failure_step) for r in rollouts}}
        for method, episodes in views.items():
            name = f"{method}-{run.name}"
            axes = error_aware(episodes, failing, cfg)
            out = {"method": name, "explained_variance": explained,
                   "axes": [{"name": f"{name} axis {i + 1}", "rollouts": sorted(a)} for i, a in enumerate(axes)]}
            (args.output_dir / f"{name}.json").write_text(json.dumps(out, indent=1) + "\n")
            print(json.dumps({"method": name, "explained": round(explained, 3), "axes": [len(a) for a in axes]}),
                  flush=True)


if __name__ == "__main__":
    main()
