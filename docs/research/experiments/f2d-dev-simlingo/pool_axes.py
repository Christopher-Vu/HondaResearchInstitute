#!/usr/bin/env python3
"""Sprint m09 and m10 (VARIANTS.md batch 2): one top-10 from several methods' ranked axes.

    PYTHONPATH=src python docs/research/experiments/f2d-dev-simlingo/pool_axes.py --name m10 \
        --source a.json --source DIR:B7_pool:L10_k64_s0 --output m10.json

Round-robin in the order the sources are given: each source's first axis, then each one's second, and so on. An axis
whose Jaccard with one already kept is at least 0.8 is skipped. Stops at 10. Sources are read as sprint_score.py
reads them, so the pooled top-10 is fixed before scoring and nothing reads the key.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from itertools import zip_longest
from pathlib import Path

from harness.scoring import jaccard

SPEC = importlib.util.spec_from_file_location("sprint_score", Path(__file__).with_name("sprint_score.py"))
sprint_score = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sprint_score)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--name", required=True)
    parser.add_argument("--source", action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    ranked = [sprint_score.read_method(spec)[1] for spec in args.source]
    kept: list[set[str]] = []
    for layer in zip_longest(*ranked):
        for axis in layer:
            if axis and len(kept) < 10 and all(jaccard(axis, k) < 0.8 for k in kept):
                kept.append(axis)
    out = {"method": args.name, "sources": args.source,
           "axes": [{"name": f"{args.name} axis {i + 1}", "rollouts": sorted(a)} for i, a in enumerate(kept)]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({"method": args.name, "axes": [len(a) for a in kept]}))


if __name__ == "__main__":
    main()
