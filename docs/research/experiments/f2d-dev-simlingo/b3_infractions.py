#!/usr/bin/env python3
"""B3-infraction, a proposed second fleet rival (m21, batch 3; post hoc, to be added to amendment A1 if Chris agrees).

    PYTHONPATH=src python docs/research/experiments/f2d-dev-simlingo/b3_infractions.py CACHE --output b3i.json

What a fleet team does first: group failures by the infraction the car incurred. One axis per infraction type: the
failing routes with at least one of it. Plus one axis for failing routes with no recorded infraction. Ranked by size,
largest first; only the first 10 score. Reads the cache's outcome fields only.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("cache", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with np.load(args.cache) as cache:
        ids, meta = cache["route_id"].tolist(), [json.loads(m) for m in cache["meta"]]
    failing = [(r, m) for r, m in zip(ids, meta) if not m["success"]]
    groups: dict[str, set[str]] = {}
    for route, m in failing:
        kinds = [k for k, v in m["infractions"].items() if v]
        for kind in kinds or ["no_recorded_infraction"]:
            groups.setdefault(kind, set()).add(route)
    ranked = sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    axes = [{"name": f"infraction: {kind}", "rollouts": sorted(members)} for kind, members in ranked]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"method": "B3_infraction", "axes": axes}, indent=1) + "\n")
    print(json.dumps({"failing": len(failing), "axes": {kind: len(m) for kind, m in ranked}}))


if __name__ == "__main__":
    main()
