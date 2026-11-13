#!/usr/bin/env python3
"""H26's reading of `score_sets.py`'s report for H24's primary arm on H3's pool.

    python docs/research/experiments/h26-activation-grouping-replication/read.py results/savio/h26/h26-report.json \
        --output docs/research/data/h26_result.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

PRIMARY = "H24_act"
# H24_act on H1's pool scored on P4 and P7 only (docs/research/data/h24_h1_p4p7_report.json), and B3 on H3's pool
# from H3's earlier run (docs/research/data/h3_layer10_plain.json). Both measured before H26 was locked.
REFERENCE = {"median_delta": 0.155, "route_bootstrap": [0.045, 0.221], "vs_random_only": 0.190,
             "median": {"P4_camera_occlusion": 0.447, "P7_camera_freeze": 0.214},
             "category_delta": {"P4_camera_occlusion": 0.270, "P7_camera_freeze": 0.038}}
B3_KNOWN = {"P4_camera_occlusion": 0.194, "P7_camera_freeze": 0.367}
SENTENCES = {
    "untested": "H26 is untested: H24_act produced fewer than 12 runs with an axis on H3's pool.",
    "replicates": "On H3's pool, grouping routes by their activations recovers P4 and P7 better than B3 and random "
                  "groups of the same sizes, by a median of at least 0.15 Jaccard on both faults, as it did on H1's pool.",
    "weaker": "On H3's pool, grouping routes by their activations beats B3 and random groups of the same sizes on "
              "both faults, but by a median under 0.15 Jaccard, less than on H1's pool.",
    "not_replicated": "On H3's pool, grouping routes by their activations is not shown to beat B3 and random groups "
                      "of the same sizes on both faults.",
}


def outcome(report: dict) -> str:
    if report["outcome"] == "untested":
        return "untested"
    if report["outcome"] == "ahead":
        return "replicates"
    beats = (report["median_delta"] > 0 and report["route_bootstrap"][0] > 0
             and all(row["median_delta"] > 0 for row in report["categories"].values()))
    return "weaker" if beats else "not_replicated"


def beside(report: dict, b3: dict) -> dict:
    """Fixed secondary reading: did the method fall, or did B3 rise? Never changes the outcome."""
    return {"h1_reference": REFERENCE, "b3_known": B3_KNOWN,
            "b3_matches_known": all(abs(b3[c] - v) < 1e-3 for c, v in B3_KNOWN.items()),
            "h3_median": {c: row["median"] for c, row in report["categories"].items()},
            "h3_vs_random_only": report["median_delta_vs_random_only"]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("report", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = json.loads(args.report.read_text())
    primary = report["methods"][PRIMARY]
    result = outcome(primary)
    record = {"label": "DEV ONLY: H26, replication of H24_act on H3's pool", "outcome": result,
              "reading": SENTENCES[result], "primary": primary, "b3": report["b3"],
              "beside": beside(primary, report["b3"]) if result != "untested" else None,
              "secondary": {name: {k: row.get(k) for k in ("outcome", "median_delta", "route_bootstrap")}
                            for name, row in report["methods"].items() if name != PRIMARY}}
    args.output.write_text(json.dumps(record, indent=1) + "\n")
    print(result, "|", record["reading"])


if __name__ == "__main__":
    main()
