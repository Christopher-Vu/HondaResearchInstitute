#!/usr/bin/env python3
"""H15's throwaway keys. DEV DRY RUN: public practice predicates, not sealed, not blind, and never a verdict.

    python docs/research/experiments/h15-scoring-dry-run/build_key.py as-labelled results/savio/h15/throwaway/as-labelled

Each predicate is copied verbatim from gaps/practice/. A neighbourhood is read from the manifest's own
`neighbourhood_of` label, so no new predicate exists. Roles in the `branch` key are assigned to exercise the decoy
path and say nothing about P7. The commitment goes beside the key, and the output must not be under gaps/ or src/.
"""
from __future__ import annotations

import argparse
import json
import secrets
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "src"))

from harness.seal import load_key, write_commitment  # noqa: E402

PRACTICE_FILES = ("gaps/practice/practice_v2.yaml", "gaps/practice/practice_v3.yaml")
P4, P7, P19 = "P4_camera_occlusion", "P7_camera_freeze", "P19_wide_invading_turn"
KEYS = {"as-labelled": {P4: False, P7: False, P19: False}, "branch": {P4: False, P19: False, P7: True}}
LABEL = "DEV DRY RUN, NOT A VERDICT: throwaway key of public practice gaps (H15)"


def practice_gaps(repo: Path = REPO) -> dict[str, dict]:
    return {gap["gap_id"]: gap for name in PRACTICE_FILES for gap in yaml.safe_load((repo / name).read_text())["gaps"]}


def key_document(name: str, repo: Path = REPO) -> dict:
    known = practice_gaps(repo)
    return {"version": 1, "label": LABEL, "dry_run": True, "gaps": [
        {"gap_id": gap_id, "tier": known[gap_id]["tier"], "decoy": decoy, "predicate": known[gap_id]["predicate"],
         "neighbourhood_predicate": [{"field": "neighbourhood_of", "op": "==", "value": [gap_id]}]}
        for gap_id, decoy in KEYS[name].items()]}


def refuse_real_locations(output: Path, repo: Path = REPO) -> None:
    resolved = output.resolve()
    for protected in (repo / "gaps", repo / "src"):
        if resolved.is_relative_to(protected.resolve()):
            raise ValueError(f"{output} is under {protected}: a throwaway key stays in the experiment's own output")


def write_key(name: str, output: Path, repo: Path = REPO) -> str:
    refuse_real_locations(output, repo)
    output.mkdir(parents=True, exist_ok=True)
    key, salt = output / "key.json", output / "salt"
    key.write_text(json.dumps(key_document(name, repo), indent=1) + "\n")
    salt.write_text(secrets.token_hex(32))
    load_key(key)
    return write_commitment(key, salt, output / "commitment.txt")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("key", choices=sorted(KEYS))
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(f"{LABEL}: {args.key} committed as {write_key(args.key, args.output)}")


if __name__ == "__main__":
    main()
