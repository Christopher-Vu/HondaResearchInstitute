#!/usr/bin/env python3
"""Step-2 gate and report tables for the H21b robustness rescores.

    python summarize.py check  --recorded results/h21/h21b --out results/h21/robust-h21b
    python summarize.py tables --recorded results/h21/h21b --out results/h21/robust-h21b > tables.md

check: the full pool's rebuilt axes must equal the recorded axes, and the m23, B3-behaviour and B3-infraction point
scores must equal the recorded ones exactly. Exits non-zero otherwise.
tables: markdown tables read from the report JSONs; every value is a measurement from those files.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from pool_inputs import seed_of

GAPS = ("F2D_CustomObstacles", "F2D_Wall", "F2D_PedestriansOnRoad")
POOLS = (("full", "24+25+26"), ("s24", "24"), ("s25", "25"), ("s26", "26"),
         ("no24", "25+26"), ("no25", "24+26"), ("no26", "24+25"))
METHODS = ("m23", "m40", "j09", "B3-behaviour", "B3-infraction")
AXES = ("m15-source", "route-L8", "m39-source", "route-L20", "j09", "b3_behaviour", "b3_infraction", "m23", "m40")
RIVALS = ("B3_behaviour", "B3_infraction")


def read(path: Path) -> dict:
    return json.loads(path.read_text())


def report_path(out: Path, pool: str, method: str, seed: int = 0) -> Path:
    suffix = f"m23-seed{seed}" if method == "m23" else method
    return out / pool / f"report-{suffix}.json"


def method_row(report: dict) -> dict:
    return next(row for row in report["rows"].values() if row["role"] == "method")


def check(recorded: Path, out: Path) -> None:
    failures = []
    for name in AXES:
        if read(recorded / "axes" / f"{name}.json")["axes"] != read(out / "full/axes" / f"{name}.json")["axes"]:
            failures.append(f"axes differ: {name}")
    m23 = read(report_path(out, "full", "m23"))
    old = read(recorded / "report-m23.json")
    pairs = {"m23": (method_row(old), method_row(m23)),
             "B3-behaviour": (old["rows"]["B3_behaviour"], m23["rows"]["B3_behaviour"]),
             "B3-infraction": (old["rows"]["B3_infraction"], m23["rows"]["B3_infraction"])}
    for name, (was, now) in pairs.items():
        same = was["mean_best"] == now["mean_best"] and was["per_gap"] == now["per_gap"]
        print(json.dumps({"row": name, "recorded": was["mean_best"], "reproduced": now["mean_best"], "equal": same}))
        if not same:
            failures.append(f"point score differs: {name}")
    if failures:
        raise SystemExit("; ".join(failures))
    print("step 2: axes and point scores equal the recorded run")


def fmt(x: float) -> str:
    return f"{x:+.3f}" if x < 0 else f"{x:.3f}"


def scores_table(out: Path) -> list[str]:
    lines = ["| pool (seeds) | routes failing in gaps (CO / W / PoR) | " + " | ".join(METHODS) + " | tag |",
             "|---|---|" + "---:|" * len(METHODS) + "---|"]
    for pool, seeds in POOLS:
        reports = {m: read(report_path(out, pool, m)) for m in METHODS}
        gaps = " / ".join(str(reports["m23"]["gaps"][g]) for g in GAPS)
        cells = [fmt(method_row(reports[m])["mean_best"]) for m in METHODS]
        lines.append(f"| {pool} ({seeds}) | {gaps} | " + " | ".join(cells) + " | measured |")
    return lines


def per_gap_table(out: Path) -> list[str]:
    lines = ["| pool | method | CustomObstacles | Wall | PedestriansOnRoad | tag |", "|---|---|---:|---:|---:|---|"]
    for pool, _ in POOLS:
        for m in METHODS:
            row = method_row(read(report_path(out, pool, m)))
            lines.append(f"| {pool} | {m} | " + " | ".join(fmt(row["per_gap"][g]) for g in GAPS) + " | measured |")
    return lines


def contrast_cell(c: dict) -> str:
    low, high = c["interval"]
    return f"{c['delta']:+.3f} [{low:+.3f}, {high:+.3f}] p {c['p_one_sided']:.3f}"


def contrast_table(recorded: Path, out: Path) -> list[str]:
    lines = ["| pool | bootstrap seed | pairs | m23 − B3-behaviour | m23 − B3-infraction | tag |",
             "|---|---:|---:|---|---|---|"]
    for pool, seeds in POOLS:
        pairs = pool_pairs(recorded, out, seeds)
        for seed in (0, 1, 2):
            report = read(report_path(out, pool, "m23", seed))
            vs = method_row(report)["vs"]
            lines.append(f"| {pool} | {seed} | {pairs} | {contrast_cell(vs['B3_behaviour'])} | "
                         f"{contrast_cell(vs['B3_infraction'])} | measured |")
    return lines


def pool_pairs(recorded: Path, out: Path, seeds: str) -> int:
    """Fail2Drive pairs the bootstrap resamples: distinct base pairs over the pool's routes."""
    wanted = {int(s) for s in seeds.split("+")}
    routes = {str(json.loads(line)["id"]) for line in (recorded / "routes.jsonl").read_text().splitlines() if line.strip()}
    return len({e["pair"] for e in read(out / "manifest.json") if str(e["id"]) in routes and seed_of(e) in wanted})


def sensitivity_table(out: Path) -> list[str]:
    lines = ["| setting | m23 axes scored | m23 score | CO / W / PoR | m23 − B3-behaviour | m23 − B3-infraction | tag |",
             "|---|---:|---:|---|---|---|---|"]
    rows = (("W 50, M 10 (recorded setting)", out / "full/report-m23-seed0.json"),
            ("W 20, M 10", out / "sensitivity/report-m23-W20.json"),
            ("W 50, M 5", out / "sensitivity/report-m23-M5.json"),
            ("W 50, M 15", out / "sensitivity/report-m23-M15.json"))
    for label, path in rows:
        row = method_row(read(path))
        tag = "measured" if "recorded" in label else "measured, exploratory"
        per_gap = " / ".join(fmt(row["per_gap"][g]) for g in GAPS)
        lines.append(f"| {label} | {row['axes']} | {fmt(row['mean_best'])} | {per_gap} | "
                     f"{contrast_cell(row['vs']['B3_behaviour'])} | {contrast_cell(row['vs']['B3_infraction'])} "
                     f"| {tag} |")
    lines.append("| W 100, M 10 | — | not computable: frames.npz stores at most 50 frames | — | — | — | — |")
    return lines


def tables(recorded: Path, out: Path) -> None:
    blocks = {"Scores (mean best Jaccard over the three gaps)": scores_table(out),
              "Per-gap best Jaccard": per_gap_table(out),
              "m23 against each rival, pair-clustered bootstrap, 2,000 replicates": contrast_table(recorded, out),
              "m23 sensitivity, full pool, bootstrap seed 0": sensitivity_table(out)}
    for title, lines in blocks.items():
        print(f"### {title}\n")
        print("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=("check", "tables"))
    parser.add_argument("--recorded", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "check":
        check(args.recorded, args.out)
    else:
        tables(args.recorded, args.out)


if __name__ == "__main__":
    main()
