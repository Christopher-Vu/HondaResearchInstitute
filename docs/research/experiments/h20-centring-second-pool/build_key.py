#!/usr/bin/env python3
"""H20's throwaway key: P4, P7 and P8, verbatim from gaps/practice/, for H1's pool. DEV DRY RUN, NOT A VERDICT.

    python docs/research/experiments/h20-centring-second-pool/build_key.py results/savio/h20/throwaway

Reuses H15's builder, so the predicates and the refusal to write under gaps/ or src/ are H15's.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "h15-scoring-dry-run"))

import build_key as h15  # noqa: E402

NAME = "h1-pool"
h15.KEYS[NAME] = {"P4_camera_occlusion": False, "P7_camera_freeze": False, "P8_camera_latency": False}
h15.LABEL = "DEV DRY RUN, NOT A VERDICT: throwaway key of public practice gaps (H20, H1's pool)"

if __name__ == "__main__":
    print(f"{h15.LABEL}: committed as {h15.write_key(NAME, Path(sys.argv[1]))}")
