#!/usr/bin/env python3
"""Dev scorer for the Fail2Drive test pool: H22's reading, with the gaps as an argument.

    PYTHONPATH=src python docs/research/experiments/f2d-dev-simlingo/score.py --directives DIR --shared PLAIN_DIR \
        --manifest MANIFEST --routes routes.jsonl --variant plain --gaps F2D_A F2D_B --output report.json

Reuses docs/research/experiments/h22-f2d-frozen-eval/score.py unchanged except for its category list. Dev only:
the best axis is chosen using the gap's failing set, and variants are iterated on this pool (VARIANTS.md).
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

from harness.scoring_run import load_emitted, load_pool

H22 = Path(__file__).resolve().parents[1] / "h22-f2d-frozen-eval" / "score.py"


def load_h22():
    spec = importlib.util.spec_from_file_location("h22_score", H22)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--directives", type=Path, required=True)
    parser.add_argument("--shared", type=Path, required=True, help="plain directives; only B1, B2 and B3 are taken")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--routes", type=Path, required=True)
    parser.add_argument("--variant", required=True)
    parser.add_argument("--gaps", nargs="+", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    h22 = load_h22()
    h22.CATEGORIES = tuple(args.gaps)
    h22.LABEL = "DEV ONLY: Fail2Drive test pool, variants iterated on this pool"
    own = [item for item in load_emitted([args.directives]) if item.family not in h22.SHARED]
    shared = [item for item in load_emitted([args.shared]) if item.family in h22.SHARED]
    manifest, failed = load_pool([args.manifest], [args.routes])
    record = h22.report(own + shared, manifest, failed, "plain")
    record["variant"] = args.variant
    args.output.write_text(json.dumps(record, indent=1) + "\n")
    print(json.dumps({k: record[k] for k in ("variant", "outcome", "comparison", "counted")}))
    for family, row in record["families"].items():
        print(family, json.dumps(row))


if __name__ == "__main__":
    main()
