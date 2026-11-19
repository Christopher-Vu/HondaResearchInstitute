#!/usr/bin/env python3
"""Does TransFuser++'s re-drive reproduce its first drive? (protocol.md in this folder, "Other models".)

    PYTHONPATH=src python docs/research/experiments/f2d-unpooled/match_rate.py REDRIVE_SHARDS FIRST_SHARDS ROUTES \
        MANIFEST --output reproducing-pairs.json

REDRIVE_SHARDS is export_activations.py's output for the re-driven route folders (as tfpp_unpooled.sbatch writes it),
FIRST_SHARDS the first drive's (results/savio/f2d-test-tfpp/shards), ROUTES its routes.jsonl and MANIFEST the pool's
manifest (base_id and seed per route id).

A route matches when the re-drive has the first drive's status (routes.jsonl `status`; a re-drive with no valid
outcome has status None and never matches) and the same first infraction type. The first infraction type is the
type whose earliest logged location the ego reached first, timed as failure_time.located_step does (the earliest step
within 0.5 m of the ego's nearest approach), collisions included. A failing route with no timed infraction gets the
sorted set of its types instead (e.g. a timeout), and a passing route gets None.

A pair (the routes sharing a base_id, a generalisation route and its base twin) reproduces when it was re-driven
because it held a failure, and every one of its routes was re-driven and matches. Routes not re-driven yet are
counted as pending, not as mismatches. Prints the route and pair match rate per seed and overall; writes the
reproducing pairs, with their route ids, to --output.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

from harness.failure_time import located_step


def first_infraction(sidecar: Path) -> str | None:
    meta = json.loads(sidecar.read_text())
    types = sorted(meta.get("infractions") or {})
    if meta.get("success") is not False or not types:
        return None
    with np.load(sidecar.with_suffix(".npz")) as archive:
        steps = archive["step"].astype(np.int64)
        x = archive["ego_x"].astype(np.float64) if "ego_x" in archive.files else None
        y = archive["ego_y"].astype(np.float64) if "ego_y" in archive.files else None
    timed = {}
    if x is not None and y is not None and np.isfinite(x).any():
        for name, points in (meta.get("infraction_locations") or {}).items():
            times = [t for t in (located_step(steps, x, y, point) for point in points) if t is not None]
            if times:
                timed[name] = min(times)
    if timed:
        return min(sorted(timed), key=timed.get)
    return "+".join(types)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("redrive", type=Path)
    parser.add_argument("first", type=Path)
    parser.add_argument("routes", type=Path)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    first_status = {row["id"]: row.get("status") for row in map(json.loads, args.routes.read_text().splitlines())}
    first_success = {row["id"]: row.get("success") for row in map(json.loads, args.routes.read_text().splitlines())}
    manifest = {r["id"]: r for r in json.loads(args.manifest.read_text())}
    pairs = defaultdict(list)
    for rid, route in manifest.items():
        pairs[route["base_id"]].append(rid)

    match: dict[str, bool] = {}
    for sidecar in sorted(args.redrive.glob("*.json")):
        rid = sidecar.stem
        status = json.loads(sidecar.read_text()).get("status")
        first = args.first / sidecar.name
        if rid not in first_status or not first.is_file():
            print(f"{rid}: no first drive to compare with, left out")
            continue
        same_status = status is not None and status == first_status[rid]
        same_first = first_infraction(sidecar) == first_infraction(first)
        match[rid] = same_status and same_first
        if not match[rid]:
            print(f"{rid}: no match (status {first_status[rid]} -> {status}, "
                  f"first infraction {first_infraction(first)} -> {first_infraction(sidecar)})")

    per_seed = defaultdict(lambda: {"routes": 0, "routes_match": 0, "pairs": 0, "pairs_done": 0, "pairs_match": 0})
    reproducing = []
    for base_id, ids in sorted(pairs.items()):
        if not any(first_success.get(rid) is False for rid in ids):
            continue  # not a re-drive pair
        row = per_seed[manifest[ids[0]]["seed"]]
        row["pairs"] += 1
        row["routes"] += sum(rid in match for rid in ids)
        row["routes_match"] += sum(match.get(rid, False) for rid in ids)
        if all(rid in match for rid in ids):
            row["pairs_done"] += 1
            if all(match[rid] for rid in ids):
                row["pairs_match"] += 1
                reproducing.append({"base_id": base_id, "seed": manifest[ids[0]]["seed"], "routes": sorted(ids)})

    rate = lambda a, b: f"{a}/{b} = {a / b:.3f}" if b else f"{a}/0"
    total = defaultdict(int)
    for seed in sorted(per_seed):
        row = per_seed[seed]
        for key, value in row.items():
            total[key] += value
        print(f"seed {seed}: routes {rate(row['routes_match'], row['routes'])}, "
              f"pairs {rate(row['pairs_match'], row['pairs_done'])} ({row['pairs'] - row['pairs_done']} pending)")
    print(f"overall: routes {rate(total['routes_match'], total['routes'])}, "
          f"pairs {rate(total['pairs_match'], total['pairs_done'])} ({total['pairs'] - total['pairs_done']} pending)")
    args.output.write_text(json.dumps(reproducing, indent=1) + "\n")
    print(f"{len(reproducing)} reproducing pairs -> {args.output}")


if __name__ == "__main__":
    main()
