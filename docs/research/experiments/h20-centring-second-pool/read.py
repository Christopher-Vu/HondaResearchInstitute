#!/usr/bin/env python3
"""H20's read: does removing the success-frame mean move method medians on H1's pool? DEV DRY RUN, NOT A VERDICT.

    python docs/research/experiments/h20-centring-second-pool/read.py results/savio/h20 --output results/savio/h20/result.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

VARIANTS = ("plain", "centre", "vision")
GAPS = ("P4_camera_occlusion", "P7_camera_freeze", "P8_camera_latency")
FAMILIES = ("M1_raw", "M1_capped", "B7_pool")
MOVE, MIN_COUNTED, DICTIONARIES = 0.1, 12, 18
PREPROCESSING = {"plain": "non_residualized", "centre": "action_residual", "vision": "action_residual"}
SENTENCES = {
    "untested": "H20 is untested: a variant did not run in full.",
    "replicates": "On H1's pool, removing only the mean moves a method's median Jaccard on a planted gap by at least "
                  "0.1, so method readings depend on a preprocessing step the PRD does not fix.",
    "not_replicated": "On H1's pool, removing only the mean moves no method's median Jaccard on a planted gap by 0.1 "
                      "or more.",
}


def scores(report: dict, family: str, gap: str, preprocessing: str) -> list[float]:
    return [m["best_jaccard"][gap] for m in report["methods"].values()
            if m["family"] == family and m["preprocessing"] == preprocessing and m["counts"]]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    table, complete = {}, True
    for variant in VARIANTS:
        path = args.out / variant / "report.json"
        if not path.is_file() or len(list((args.out / variant).glob("sae/L10_*/metrics.json"))) != DICTIONARIES:
            complete = False
            continue
        report = json.loads(path.read_text())
        table[variant] = {}
        for family in FAMILIES:
            for gap in GAPS:
                values = scores(report, family, gap, PREPROCESSING[variant])
                if len(values) < MIN_COUNTED:
                    complete = False
                    continue
                table[variant][f"{family}|{gap}"] = {"best": max(values), "median": float(np.median(values)),
                                                     "at_or_above_0_5": sum(v >= 0.5 for v in values),
                                                     "dictionaries": len(values)}
    moves = {}
    if complete:
        moves = {cell: table["centre"][cell]["median"] - table["plain"][cell]["median"] for cell in table["plain"]}
    result = "untested" if not complete else ("replicates" if any(abs(v) >= MOVE - 1e-9 for v in moves.values()) else "not_replicated")
    record = {"label": "DEV DRY RUN, NOT A VERDICT: H20 centring on H1's pool", "note": "The best axis is chosen using the key.",
              "fits": {v: json.loads((args.out / v / "fit.json").read_text()) for v in ("centre", "vision")
                       if (args.out / v / "fit.json").is_file()},
              "table": table, "centre_minus_plain_median": moves, "outcome": result, "reading": SENTENCES[result]}
    args.output.write_text(json.dumps(record, indent=1) + "\n")
    print(json.dumps({"centre_minus_plain_median": {k: round(v, 3) for k, v in moves.items()}, "outcome": result,
                      "reading": record["reading"]}, indent=1))


if __name__ == "__main__":
    main()
