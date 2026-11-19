#!/usr/bin/env python3
"""Units by rule (protocol.md, "Units and metrics"): every Fail2Drive type whose generalisation routes fail at least
RATIO times as often as their base twins, with at least MIN_FAILING failing generalisation routes.

    PYTHONPATH=src python docs/research/experiments/f2d-unpooled/units_rule.py MANIFEST ROUTES [--restrict IDS.txt]

Prints one line per type (failing/total for slices and twins, ratio, in or out) and, last, the units as MODEL:TYPE
arguments for view_score.py when --model is given. It reads outcomes only, never a method's axes or score.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from harness.scoring_run import load_pool

RATIO, MIN_FAILING = 1.5, 5


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("routes", type=Path, nargs="+")
    parser.add_argument("--restrict", type=Path)
    parser.add_argument("--model", default="")
    args = parser.parse_args()
    manifest, outcome = load_pool([args.manifest], args.routes)
    if args.restrict:
        keep = set(args.restrict.read_text().split())
        outcome = {r: v for r, v in outcome.items() if r in keep}
    slices, twins = defaultdict(list), defaultdict(list)
    for e in manifest:
        r = str(e["id"])
        if r not in outcome:
            continue
        for c in e["practice_gaps"] if e["role"] == "pilot_slice" else e.get("neighbourhood_of", []):
            (slices if e["role"] == "pilot_slice" else twins)[c].append(bool(outcome[r]))
    units = []
    for c in sorted(slices):
        s, t = slices[c], twins.get(c, [])
        rs, rt = sum(s) / len(s), (sum(t) / len(t) if t else 0.0)
        ok = sum(s) >= MIN_FAILING and (rt == 0 or rs >= RATIO * rt)
        units += [c] if ok else []
        print(json.dumps({"type": c, "slice": f"{sum(s)}/{len(s)}", "twin": f"{sum(t)}/{len(t)}",
                          "ratio": round(rs / rt, 2) if rt else None, "unit": ok}))
    if args.model:
        print(" ".join(f"{args.model}:{c}" for c in units))


if __name__ == "__main__":
    main()
