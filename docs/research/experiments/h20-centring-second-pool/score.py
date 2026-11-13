#!/usr/bin/env python3
"""H20's scorer: each directive's best Jaccard per key gap, in `scoring_run`'s method-row shape. DEV DRY RUN.

`scoring_run` always evaluates condition 2, which needs an interactional gap, and H1's pool has none. H20 reads only
per-gap scores, so this computes those with the same loaders and the same `mean_best_jaccard`.

    PYTHONPATH=src python docs/research/experiments/h20-centring-second-pool/score.py --directives DIR [...] \
        --key KEY --manifests M [...] --routes R [...] --label LABEL --output report.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from harness.bootstrap import mean_best_jaccard
from harness.scoring_run import DRY_RUN_MARK, load_emitted, load_pool, require_scored_members
from harness.seal import gaps_from_key, key_is_dry_run, load_key


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--directives", type=Path, nargs="+", required=True)
    parser.add_argument("--key", type=Path, required=True)
    parser.add_argument("--manifests", type=Path, nargs="+", required=True)
    parser.add_argument("--routes", type=Path, nargs="+", required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not key_is_dry_run(args.key) or DRY_RUN_MARK not in args.label:
        parser.error("H20 scores only a dry-run key, under a label that says so")
    manifest, failed = load_pool(args.manifests, args.routes)
    emitted = load_emitted(args.directives)
    require_scored_members(emitted, failed)
    gaps = [gap for gap in gaps_from_key(load_key(args.key), manifest, failed) if not gap.is_decoy]
    methods = {item.label: {"family": item.family, "kind": item.kind, "dictionary": item.dictionary, "counts": item.counts,
                            "preprocessing": item.directive.preprocessing,
                            "best_jaccard": {gap.gap_id: mean_best_jaccard(item.directive, [gap]) for gap in gaps}}
               for item in emitted}
    report = {"dry_run": True, "label": args.label, "pool": {"rollouts": len(failed), "failures": sum(failed.values())},
              "key_sizes": {gap.gap_id: len(gap.failing_rollouts) for gap in gaps}, "methods": methods}
    args.output.write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps({"label": args.label, "key_sizes": report["key_sizes"], "directives": len(methods)}))


if __name__ == "__main__":
    main()
