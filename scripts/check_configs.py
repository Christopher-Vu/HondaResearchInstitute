#!/usr/bin/env python3
"""Validate every config under configs/ and report unresolved placeholders.

Runs anywhere, no GPU:  python scripts/check_configs.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from harness.config import describe, find_tbd, load  # noqa: E402

def main() -> int:
    root = Path(__file__).resolve().parents[1] / "configs"
    files = sorted(root.rglob("*.yaml")) + sorted(root.rglob("*.yml"))
    if not files:
        print("no configs found under", root)
        return 1
    total_tbd = 0
    for f in files:
        rel = f.relative_to(root.parent)
        try:
            print(describe(f).replace(str(f), str(rel)))
        except Exception as exc:
            print("%s\n  ERROR: %s" % (rel, exc))
            return 1
        total_tbd += len(find_tbd(load(f)))
    print("\n%d config(s), %d unresolved placeholder(s)." % (len(files), total_tbd))
    if total_tbd:
        print("Unresolved values are expected while Steps 0-1 are blocked;")
        print("harness.config.require_resolved() refuses to run with them set.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
