#!/usr/bin/env python3
"""H23's scorer: H22's scorer and rule unchanged, under H23's label. Post hoc, dev only, not blind.

    PYTHONPATH=src python docs/research/experiments/h23-f2d-m1-floor/score.py [H22 score.py arguments]
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

H22 = Path(__file__).resolve().parents[1] / "h22-f2d-frozen-eval" / "score.py"
spec = importlib.util.spec_from_file_location("h22_score", H22)
h22 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h22)

h22.LABEL = "DEV ONLY, NOT BLIND, POST HOC: H23, M1's group floor at 3 on Fail2Drive's categories, after H22"
h22.SENTENCES["untested"] = h22.SENTENCES["untested"].replace("H22", "H23")

if __name__ == "__main__":
    h22.main()
