#!/usr/bin/env python3
"""Route ids to re-drive with input capture: every within-seed Fail2Drive pair (both routes of a base_id) in which
either route failed on the first drive (protocol.md, "Other models").

    python docs/research/experiments/f2d-unpooled/redrive_ids.py SHARDS MANIFEST [--exclude-done RESULTS...]

Prints one line per seed: `<seed> <id> <id> ...`. Outcomes come from the shards' `success` field. With
--exclude-done, ids whose route folder under any RESULTS/<job>/route-<id> already holds capture/inputs are left out,
so the same command lists what is still missing for a resubmit.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("shards", type=Path)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--exclude-done", type=Path, nargs="*", default=[])
    args = parser.parse_args()
    failed = {p.stem for p in args.shards.glob("*.json") if json.loads(p.read_text()).get("success") is False}
    pairs = defaultdict(list)
    for route in json.loads(args.manifest.read_text()):
        pairs[route["base_id"]].append(route)
    done = {d.name.removeprefix("route-") for root in args.exclude_done for d in root.glob("*/route-*")
            if any((d / "capture/inputs").glob("*.pt"))}
    by_seed = defaultdict(list)
    for routes in pairs.values():
        if any(r["id"] in failed for r in routes):
            by_seed[routes[0]["seed"]] += [r["id"] for r in routes if r["id"] not in done]
    for seed in sorted(by_seed):
        print(seed, *sorted(by_seed[seed]))


if __name__ == "__main__":
    main()
