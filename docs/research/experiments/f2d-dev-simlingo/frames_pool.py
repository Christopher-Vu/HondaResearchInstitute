#!/usr/bin/env python3
"""One site's last F frames before failure, right-aligned, for a temporal method.

    PYTHONPATH=src python docs/research/experiments/f2d-dev-simlingo/frames_pool.py SHARDS \
        --output OUT.npz [--site driving_queries] [--frames 50] [--layer ...] \
        [--depth-fractions 5/23 8/23 10/23 20/23]

Rows follow cache_pool.py: salted order via its order_key and SALT, skip when success is
None, and the same meta json (success, failure_step, n_steps, infractions). No scenario,
town, route-config or category field is written.

frames is (routes, layers, F, width) float16. The newest kept frame is at index F-1 and
shorter routes are NaN-padded at the front. Kept frames are the last F with step strictly
below the failure step (frame 0 when that slice is empty; every frame when failure_step
is None), the same slice cache_pool.summaries uses. Default layers are
round(f * (depth - 1)) for f in 5/23, 8/23, 10/23, 20/23, which is 5, 8, 10, 20 at
depth 24. One slot is stored per fraction, in that order.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from collections.abc import Iterable, Sequence
from pathlib import Path

import numpy as np

from harness.failure_time import failure_step


def _load_cache_pool():
    path = Path(__file__).with_name("cache_pool.py")
    spec = importlib.util.spec_from_file_location("cache_pool_for_frames", path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_CACHE_POOL = _load_cache_pool()
order_key = _CACHE_POOL.order_key
SALT = _CACHE_POOL.SALT

# Fractions of (depth - 1), not a fixed 24-layer decoder. 5, 8, 10, 20 at depth 24.
DEFAULT_FRACTIONS = (5 / 23, 8 / 23, 10 / 23, 20 / 23)


def parse_fraction(text: str) -> float:
    token = text.strip()
    if "/" in token:
        num, den = token.split("/", 1)
        try:
            value = float(num) / float(den)
        except ZeroDivisionError as exc:
            raise argparse.ArgumentTypeError(f"not a finite fraction: {text}") from exc
    else:
        value = float(token)
    if not np.isfinite(value):
        raise argparse.ArgumentTypeError(f"not a finite fraction: {text}")
    return value


def layer_indices(depth: int, fractions: Iterable[float] = DEFAULT_FRACTIONS) -> list[int]:
    """round(f * (depth - 1)) for each fraction, clamped into 0..depth-1.

    Order follows `fractions`. A repeated index is kept, so each fraction has a slot.
    """
    if depth < 1:
        raise SystemExit(f"frames_pool: depth {depth} is not positive")
    last = depth - 1
    picked = []
    for frac in fractions:
        index = int(round(float(frac) * last))
        picked.append(min(max(index, 0), last))
    return picked


def resolve_layers(depth: int, requested: Sequence[int] | None,
                   fractions: Iterable[float] = DEFAULT_FRACTIONS) -> list[int]:
    """Explicit --layer indices, or the default fractions of this tensor's depth."""
    if requested:
        picked = [int(layer) for layer in requested]
        bad = [layer for layer in picked if layer < 0 or layer >= depth]
        if bad:
            raise SystemExit(f"frames_pool: layers {bad} outside 0..{depth - 1} for depth {depth}")
        return picked
    return layer_indices(depth, fractions)


def kept_frame_indices(steps: np.ndarray, failed_at: int | None, n_keep: int) -> np.ndarray:
    """Row indices to store, oldest first.

    Same selection as cache_pool.summaries. failed_at None keeps every frame (a pass,
    or a failure with no timed infraction). Otherwise keep steps < failed_at, or row 0
    when that slice is empty. Then keep the newest n_keep of those rows.
    """
    if n_keep < 1:
        raise SystemExit("frames_pool: --frames must be at least 1")
    steps = np.asarray(steps)
    if failed_at is not None:
        idx = np.flatnonzero(steps < failed_at)
        if len(idx) == 0:
            idx = np.arange(min(1, steps.shape[0]), dtype=np.int64)
    else:
        idx = np.arange(steps.shape[0], dtype=np.int64)
    return np.asarray(idx[-n_keep:], dtype=np.int64)


def _arrays(archive: np.lib.npyio.NpzFile, site: str) -> dict[str, np.ndarray]:
    """The keys cache_pool.py would load, plus the requested site, so failure_step agrees."""
    names = (*_CACHE_POOL.LAYERED, "vision_bridge", "step", "ego_speed", "ego_x", "ego_y", site)
    return {name: archive[name] for name in dict.fromkeys(names) if name in archive.files}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("shards", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--site", default="driving_queries")
    parser.add_argument("--frames", type=int, default=50)
    parser.add_argument("--layer", type=int, nargs="*", default=None,
                        help="absolute layer indices; default is --depth-fractions of (depth-1)")
    parser.add_argument("--depth-fractions", type=parse_fraction, nargs="+", default=None,
                        help="fractions of (depth-1); default 5/23 8/23 10/23 20/23")
    args = parser.parse_args()
    if args.frames < 1:
        raise SystemExit("frames_pool: --frames must be at least 1")
    if not args.shards.is_dir():
        raise SystemExit(f"frames_pool: {args.shards} is not a directory")
    fractions = DEFAULT_FRACTIONS if args.depth_fractions is None else tuple(args.depth_fractions)
    # order_key applies SALT inside cache_pool.py. Do not reimplement it here.
    sidecars = sorted(args.shards.glob("*.json"), key=lambda path: order_key(path.stem))
    ids: list[str] = []
    metas: list[dict] = []
    blocks: list[np.ndarray] = []
    speeds: list[np.ndarray] = []
    counts: list[int] = []
    layers: list[int] | None = None
    depth = width = None
    for sidecar in sidecars:
        info = json.loads(sidecar.read_text())
        if info.get("success") is None:
            continue
        npz_path = sidecar.with_suffix(".npz")
        if not npz_path.is_file():
            raise SystemExit(f"frames_pool: missing {npz_path.name} for route {sidecar.stem}")
        with np.load(npz_path) as archive:
            arrays = _arrays(archive, args.site)
            if args.site not in arrays:
                raise SystemExit(f"frames_pool: {sidecar.name} has no {args.site}")
            if "step" not in arrays or "ego_speed" not in arrays:
                raise SystemExit(f"frames_pool: {sidecar.name} is missing step or ego_speed")
            site_arr = np.asarray(arrays[args.site])
            if site_arr.ndim != 3:
                raise SystemExit(
                    f"frames_pool: {args.site} in {sidecar.name} has shape {tuple(site_arr.shape)}, "
                    "expected (frames, layers, width)")
            n_time = int(site_arr.shape[0])
            if int(arrays["step"].shape[0]) != n_time or int(arrays["ego_speed"].shape[0]) != n_time:
                raise SystemExit(
                    f"frames_pool: {sidecar.name} step/ego_speed length does not match "
                    f"{args.site} frames ({n_time})")
            this_depth = int(site_arr.shape[1])
            this_width = int(site_arr.shape[2])
            if layers is None:
                layers = resolve_layers(this_depth, args.layer, fractions)
                depth, width = this_depth, this_width
            elif this_depth != depth or this_width != width:
                raise SystemExit(
                    f"frames_pool: {sidecar.name} has shape {tuple(site_arr.shape)}, "
                    f"expected (frames, {depth}, {width})")
            steps = np.asarray(arrays["step"], dtype=np.int64)
            failed_at = failure_step(info, arrays)
            if failed_at is not None:
                failed_at = int(failed_at)
            idx = kept_frame_indices(steps, failed_at, args.frames)
            k = int(len(idx))
            block = np.full((len(layers), args.frames, this_width), np.nan, dtype=np.float16)
            speed = np.full(args.frames, np.nan, dtype=np.float32)
            if k:
                picked = np.asarray(site_arr[idx], dtype=np.float16)
                block[:, -k:, :] = np.stack([picked[:, layer, :] for layer in layers], axis=0)
                speed[-k:] = np.asarray(arrays["ego_speed"], dtype=np.float32)[idx]
        ids.append(str(info["route_id"]))
        metas.append({"success": bool(info["success"]), "failure_step": failed_at, "n_steps": info.get("n_steps"),
                      "infractions": {key: len(value) if isinstance(value, list) else value
                                      for key, value in (info.get("infractions") or {}).items()}})
        blocks.append(block)
        speeds.append(speed)
        counts.append(k)
    if not ids or layers is None or width is None:
        raise SystemExit(f"frames_pool: no routes with a success field under {args.shards}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    np.savez(args.output,
             route_id=np.array(ids),
             meta=np.array([json.dumps(item) for item in metas]),
             layers=np.asarray(layers, dtype=np.int64),
             site=np.asarray(args.site),
             frames=np.stack(blocks),
             n_frames=np.asarray(counts, dtype=np.int64),
             ego_speed=np.stack(speeds))
    print(json.dumps({"routes": len(ids), "failing": sum(not item["success"] for item in metas),
                      "site": args.site, "layers": layers,
                      "frames": [len(ids), len(layers), args.frames, width]}))


if __name__ == "__main__":
    main()
