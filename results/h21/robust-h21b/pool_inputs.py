#!/usr/bin/env python3
"""Inputs for the H21b robustness rescores (VARIANTS.md "H21b robustness").

    python pool_inputs.py manifest SRC OUT
    python pool_inputs.py subset POOL_DIR ROUTES MANIFEST --seeds 24 25 --out DIR
    python pool_inputs.py window FRAMES CACHE --last 20 --out cache-w20.npz [--expect cache-w50.npz]
    python pool_inputs.py round-robin --cap 15 --name NAME --source a.json --source b.json --output out.json

manifest: pair = base_id without its -sNN seed suffix (prereg A1), so a pair carries all its seeds.
subset: rows of cache.npz, cache-w50.npz and frames.npz whose seed is in --seeds, in the pooled order; routes.jsonl
and the manifest cut to the same routes. The seed is the base_id suffix; no suffix is seed 24.
window: the mean of the last N stored frames written into driving_queries' window slot at the stored layers, as the
pool builder does for N = 50. --expect checks the rebuild against an existing window cache, byte for byte.
round-robin: pool_axes.py's rule (round-robin over sources, skip Jaccard >= 0.8 with a kept axis) with its cap of 10
replaced by --cap.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
from itertools import zip_longest
from pathlib import Path

import numpy as np

from harness.scoring import jaccard

SEED_SUFFIX = re.compile(r"-s(\d+)$")
DEFAULT_SEED = 24
EXPERIMENT = Path(__file__).resolve().parents[3] / "docs/research/experiments/f2d-dev-simlingo"


def base_pair(base_id: str) -> str:
    return SEED_SUFFIX.sub("", base_id)


def seed_of(entry: dict) -> int:
    found = SEED_SUFFIX.search(entry["base_id"])
    return int(found.group(1)) if found else DEFAULT_SEED


def correct_manifest(src: Path, out: Path) -> None:
    manifest = [entry | {"pair": base_pair(entry["base_id"])} for entry in json.loads(src.read_text())]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=1) + "\n")
    print(json.dumps({"entries": len(manifest), "pairs": len({e["pair"] for e in manifest})}))


def load_npz(path: Path) -> dict[str, np.ndarray]:
    with np.load(path) as archive:
        return {key: archive[key] for key in archive.files}


def subset_archive(path: Path, keep: np.ndarray) -> dict[str, np.ndarray]:
    archive = load_npz(path)
    n = len(archive["route_id"])
    return {key: value[keep] if value.ndim and value.shape[0] == n else value for key, value in archive.items()}


def subset(pool: Path, routes: Path, manifest_path: Path, seeds: set[int], out: Path) -> None:
    manifest = json.loads(manifest_path.read_text())
    wanted = {str(e["id"]) for e in manifest if seed_of(e) in seeds}
    ids = [str(r) for r in load_npz(pool / "cache.npz")["route_id"].tolist()]
    keep = np.array([r in wanted for r in ids])
    out.mkdir(parents=True, exist_ok=True)
    for name in ("cache.npz", "cache-w50.npz", "frames.npz"):
        part = subset_archive(pool / name, keep)
        if [str(r) for r in part["route_id"].tolist()] != [r for r, k in zip(ids, keep) if k]:
            raise SystemExit(f"{name}: route order differs from cache.npz")
        np.savez(out / name, **part)
    kept = {r for r, k in zip(ids, keep) if k}
    lines = [line for line in routes.read_text().splitlines() if line.strip() and str(json.loads(line)["id"]) in kept]
    (out / "routes.jsonl").write_text("\n".join(lines) + "\n")
    (out / "manifest.json").write_text(json.dumps([e for e in manifest if str(e["id"]) in kept], indent=1) + "\n")
    failing = sum(not json.loads(line)["success"] for line in lines)
    print(json.dumps({"seeds": sorted(seeds), "routes": int(keep.sum()), "routes_jsonl": len(lines),
                      "failing": failing}))


def window_cache(frames_path: Path, cache_path: Path, last: int, out: Path, expect: Path | None) -> None:
    frames, cache = load_npz(frames_path), load_npz(cache_path)
    if not np.array_equal(frames["route_id"], cache["route_id"]):
        raise SystemExit("frames and cache route ids differ")
    stored = frames["frames"].shape[2]
    if last > stored:
        raise SystemExit(f"--last {last} exceeds the {stored} frames stored per route")
    layers = [int(v) for v in frames["layers"].tolist()]
    with np.errstate(invalid="ignore"):
        mean = np.nanmean(frames["frames"][:, :, -last:].astype(np.float32), axis=2)
    dq = cache["driving_queries"].astype(np.float32)
    dq[:, 1] = np.nan
    dq[:, 1, np.array(layers)] = mean
    cache["driving_queries"] = dq.astype(np.float16)
    np.savez(out, **cache)
    check = {"last": last, "layers": layers, "nan_rows": int(np.isnan(mean).any(axis=(1, 2)).sum())}
    if expect is not None:
        check["equals_expected"] = bool(np.array_equal(cache["driving_queries"], load_npz(expect)["driving_queries"],
                                                       equal_nan=True))
        if not check["equals_expected"]:
            raise SystemExit(f"rebuild differs from {expect}: {check}")
    print(json.dumps(check))


def round_robin(sources: list[str], cap: int, name: str, output: Path) -> None:
    spec = importlib.util.spec_from_file_location("sprint_score", EXPERIMENT / "sprint_score.py")
    sprint_score = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sprint_score)
    ranked = [sprint_score.read_method(source)[1] for source in sources]
    kept: list[set[str]] = []
    for layer in zip_longest(*ranked):
        for axis in layer:
            if axis and len(kept) < cap and all(jaccard(axis, k) < 0.8 for k in kept):
                kept.append(axis)
    out = {"method": name, "sources": sources, "cap": cap,
           "axes": [{"name": f"{name} axis {i + 1}", "rollouts": sorted(a)} for i, a in enumerate(kept)]}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({"method": name, "cap": cap, "axes": [len(a) for a in kept]}))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("manifest")
    p.add_argument("src", type=Path)
    p.add_argument("out", type=Path)
    p = sub.add_parser("subset")
    p.add_argument("pool", type=Path)
    p.add_argument("routes", type=Path)
    p.add_argument("manifest", type=Path)
    p.add_argument("--seeds", type=int, nargs="+", required=True)
    p.add_argument("--out", type=Path, required=True)
    p = sub.add_parser("window")
    p.add_argument("frames", type=Path)
    p.add_argument("cache", type=Path)
    p.add_argument("--last", type=int, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--expect", type=Path)
    p = sub.add_parser("round-robin")
    p.add_argument("--cap", type=int, required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--source", action="append", required=True)
    p.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "manifest":
        correct_manifest(args.src, args.out)
    elif args.command == "subset":
        subset(args.pool, args.routes, args.manifest, set(args.seeds), args.out)
    elif args.command == "window":
        window_cache(args.frames, args.cache, args.last, args.out, args.expect)
    else:
        round_robin(args.source, args.cap, args.name, args.output)


if __name__ == "__main__":
    main()
