#!/usr/bin/env python3
"""One pass over a pool's shards into a single per-route summary file, so a method reads ~0.3 GB, not 44 GB.

    PYTHONPATH=src python docs/research/experiments/f2d-dev-simlingo/cache_pool.py SHARDS --output cache.npz

For every route and every site with a layer axis (all_tokens, driving_queries: frames x layers x width) and
vision_bridge (frames x width), three float16 means: the whole route, the approach window (the last WINDOW captured
frames before the failure step, or before the route ends when it passed) and the early route (the first WINDOW
frames). Also per-frame ego speed and step, padded with NaN, for fleet-observable kinematics.

Label hiding: rows are in salted-hash order, never route-id order (raw ids sort by category, the H25 leak), and no
scenario, town or route-config field is written. Outcome fields kept: success, infraction counts, failure step.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from harness.failure_time import failure_step

WINDOW = 6
SALT = "f2d-cache-v1"
LAYERED = ("all_tokens", "driving_queries")


def order_key(route_id: str) -> str:
    return hashlib.sha256((SALT + route_id).encode()).hexdigest()


def summaries(frames: np.ndarray, steps: np.ndarray, failed_at: int | None) -> np.ndarray:
    """(3, ...) float32: route mean, approach-window mean, early mean."""
    before = frames[steps < failed_at] if failed_at is not None else frames
    if len(before) == 0:
        before = frames[:1]
    return np.stack([frames.mean(0), before[-WINDOW:].mean(0), frames[:WINDOW].mean(0)])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("shards", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-frames", type=int, default=100)
    args = parser.parse_args()
    sidecars = sorted(args.shards.glob("*.json"), key=lambda p: order_key(p.stem))
    ids, meta, sites, speed, step = [], [], {}, [], []
    for sidecar in sidecars:
        info = json.loads(sidecar.read_text())
        if info.get("success") is None:
            continue
        with np.load(sidecar.with_suffix(".npz")) as archive:
            arrays = {k: archive[k] for k in (*LAYERED, "vision_bridge", "step", "ego_speed", "ego_x", "ego_y")
                      if k in archive.files}
        steps = arrays["step"].astype(np.int64)
        failed_at = failure_step(info, arrays)
        for site in (*LAYERED, "vision_bridge"):
            if site in arrays:
                sites.setdefault(site, []).append(summaries(arrays[site].astype(np.float32), steps, failed_at)
                                                  .astype(np.float16))
        pad = np.full(args.max_frames, np.nan, np.float32)
        s = pad.copy(); s[:len(steps)] = arrays["ego_speed"][:args.max_frames]
        t = pad.copy(); t[:len(steps)] = steps[:args.max_frames]
        speed.append(s); step.append(t)
        ids.append(str(info["route_id"]))
        meta.append({"success": bool(info["success"]), "failure_step": failed_at, "n_steps": info.get("n_steps"),
                     "infractions": {k: len(v) if isinstance(v, list) else v
                                     for k, v in (info.get("infractions") or {}).items()}})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    np.savez(args.output, route_id=np.array(ids), meta=np.array([json.dumps(m) for m in meta]),
             ego_speed=np.stack(speed), step=np.stack(step), **{site: np.stack(v) for site, v in sites.items()})
    print(json.dumps({"routes": len(ids), "failing": sum(not m["success"] for m in meta),
                      "sites": {site: list(np.stack(v).shape) for site, v in sites.items()}}))


if __name__ == "__main__":
    main()
