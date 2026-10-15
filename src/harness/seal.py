"""The sealing protocol of PRD 9.1: commit to the answer key before the test pool exists, reveal it after.

    python -m src.harness.seal commit gaps/sealed/key_v1.json gaps/sealed/salt   # writes src/harness/KEY_COMMITMENT.txt
    python -m src.harness.seal verify gaps/sealed/key_v1.json gaps/sealed/salt   # exit 0 if the key matches

The commitment is sha256(key bytes || salt bytes) over the files exactly as stored, so a reformatted key does not
verify. The salt is secret until the reveal; without it the commitment says nothing about the key.

Scoring is the only reader of the key (CI-enforced for discovery/, baselines/, gate/): `gaps_from_key` turns the
key's predicates, evaluated against the test pool's manifest entries, and the rollouts' outcomes into the Gap
objects harness.scoring matches against.

Key format (JSON): {"version": 1, "gaps": [{"gap_id", "tier", "decoy": bool, "predicate": [{field, op, value}],
"efficacy": {...}}]}, predicates in harness.predicates' syntax.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from .predicates import matches
from .schema import TIERS, Gap

COMMITMENT = Path(__file__).with_name("KEY_COMMITMENT.txt")


def commitment(key: Path, salt: Path) -> str:
    return hashlib.sha256(key.read_bytes() + salt.read_bytes()).hexdigest()


def write_commitment(key: Path, salt: Path, out: Path = COMMITMENT) -> str:
    """Write the commitment; refuses to overwrite an existing one (a new key is a new version, PRD 9.1)."""
    if out.exists():
        raise FileExistsError(f"{out} exists; a key is committed once")
    digest = commitment(key, salt)
    out.write_text(digest + "\n", newline="\n")
    return digest


def verify(key: Path, salt: Path, committed: Path = COMMITMENT) -> bool:
    return committed.read_text().strip() == commitment(key, salt)


def load_key(key: Path) -> list[dict[str, Any]]:
    data = json.loads(key.read_text())
    gaps = data["gaps"]
    for gap in gaps:
        if gap["tier"] not in TIERS:
            raise ValueError(f"{gap['gap_id']}: unknown tier {gap['tier']!r}")
        if not gap.get("predicate"):
            raise ValueError(f"{gap['gap_id']}: empty predicate")
    if len({gap["gap_id"] for gap in gaps}) != len(gaps):
        raise ValueError("duplicate gap ids in the key")
    return gaps


def gaps_from_key(key_gaps: Sequence[Mapping[str, Any]], manifest: Sequence[Mapping[str, Any]],
                  failed: Mapping[str, bool]) -> list[Gap]:
    """Slice = test-pool rollouts whose manifest entry matches the predicate; failing = the slice's failures.
    Rollouts with no outcome (absent from `failed`) are in no slice."""
    out = []
    for spec in key_gaps:
        in_slice = {str(e["id"]) for e in manifest if str(e["id"]) in failed and matches(spec["predicate"], e)}
        out.append(Gap(gap_id=spec["gap_id"], tier=spec["tier"],
                       failing_rollouts={r for r in in_slice if failed[r]}, slice_rollouts=in_slice,
                       efficacy=dict(spec.get("efficacy", {})), is_decoy=bool(spec.get("decoy", False))))
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("action", choices=("commit", "verify"))
    parser.add_argument("key", type=Path)
    parser.add_argument("salt", type=Path)
    args = parser.parse_args()
    load_key(args.key)
    if args.action == "commit":
        print(write_commitment(args.key, args.salt))
    else:
        ok = verify(args.key, args.salt)
        print("verified" if ok else "MISMATCH")
        raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
