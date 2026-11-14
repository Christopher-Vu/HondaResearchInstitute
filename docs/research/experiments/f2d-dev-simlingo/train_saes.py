#!/usr/bin/env python3
"""discovery.sae's --frame-means training for several k and seeds, loading the shards once.

    PYTHONPATH=src python docs/research/experiments/f2d-dev-simlingo/train_saes.py SHARDS --layer 10 \
        --ks 32 48 64 --seeds 0 1 2 --output RUN/sae

Writes RUN/sae/L{layer}_k{k}_s{seed}/{sae.pt,metrics.json} exactly as `python -m discovery.sae` does, and skips a
dictionary whose metrics.json exists. One sae.py run re-reads every shard; on the 1,188-route pool that took about
13 of each run's minutes.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

import torch

from discovery import sae


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("shards", type=Path, nargs="+")
    parser.add_argument("--layer", type=int, required=True)
    parser.add_argument("--ks", type=int, nargs="+", required=True)
    parser.add_argument("--seeds", type=int, nargs="+", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    todo = [(k, s) for s in args.seeds for k in args.ks
            if not (args.output / f"L{args.layer}_k{k}_s{s}" / "metrics.json").exists()]
    if not todo:
        return
    tokens, bases = sae.load_frame_means(args.shards, args.layer)
    x = sae.normalise(tokens.float())
    for k, seed in todo:
        config = sae.SaeConfig(layer=args.layer, k=k, seed=seed, inputs="frame_means")
        held = sae.held_out_mask(bases, seed)
        model, curve = sae.train(x[torch.from_numpy(~held)].to(device), config, device)
        metrics = {"config": asdict(config), "train_tokens": int((~held).sum()), "held_out_tokens": int(held.sum()),
                   "dead_fraction_at_end": curve[-1]["dead_fraction"],
                   "held_out": sae.evaluate(model, x[torch.from_numpy(held)].to(device), config.batch),
                   "curve": curve}
        out = args.output / f"L{args.layer}_k{k}_s{seed}"
        out.mkdir(parents=True, exist_ok=True)
        torch.save({"config": asdict(config), "state": model.state_dict()}, out / "sae.pt")
        (out / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")
        print(json.dumps({"dictionary": out.name, "explained_variance": metrics["held_out"]["explained_variance"]}),
              flush=True)


if __name__ == "__main__":
    main()
