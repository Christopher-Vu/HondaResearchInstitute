"""Expected B2 score of a candidate gap, before any rollout exists (PRD 13 Step 5's 0.4 limit).

    python docs/research/experiments/h13-cross-family-gap/b2_precheck.py ROUTE_OUTCOMES OUTPUT.json

ROUTE_OUTCOMES holds <run>/routes.jsonl for the runs named below. The candidate's failures are simulated at assumed rates on real
roads and added to H12's pool without P19, then B2's own strata are scored against the simulated key. No CARLA, no SU.
"""
from __future__ import annotations

import argparse
import collections
import json
import random
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from statistics import mean
from typing import Any

ROOT = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "adapters/simlingo")]

from baselines.taxonomy import TaxonomyConfig, build_strata  # noqa: E402
from cut_routes import cuts_from  # noqa: E402
from pilot_routes import route_length  # noqa: E402
from scipy.stats import fisher_exact  # noqa: E402

UNPLANTED_RUNS = ("step2-bench2drive220", "step4-dev-pool", "step4-dev-pool-wave2", "step5-background-wave3")
POOL_RUNS = ("step5-background-wave3", "step5-confirm-p4", "step5-confirm-p7")
ROUTE_DATA = ROOT / ".runtime/simlingo/leaderboard/data"
CUT_SPEC = {"lead_m": 20, "tail_m": 60, "min_spacing_m": 100}
LENGTH_RANGE_M = (100, 800)
TRIALS = 200
EIGHT_ONCOMING = ("ConstructionObstacleTwoWays", "AccidentTwoWays", "ParkedObstacleTwoWays", "HazardAtSideLaneTwoWays",
                  "VehicleOpensDoorTwoWays", "SignalizedJunctionLeftTurn", "NonSignalizedJunctionLeftTurn", "InvadingTurn")
CANDIDATES: dict[str, tuple[str, ...]] = {
    "P19 as run, to validate against the measured 0.857": ("InvadingTurn",),
    "eight oncoming-traffic families": EIGHT_ONCOMING,
    "five low-baseline families, four sharing the Overtaking ability": (
        "AccidentTwoWays", "ParkedObstacleTwoWays", "HazardAtSideLaneTwoWays", "VehicleOpensDoorTwoWays", "InvadingTurn"),
    "four families across three abilities": (
        "ParkedObstacleTwoWays", "VehicleOpensDoorTwoWays", "InvadingTurn", "NonSignalizedJunctionLeftTurn"),
}


def outcomes(routes_dir: Path, run: str) -> dict[str, dict[str, Any]]:
    rows = map(json.loads, (routes_dir / run / "routes.jsonl").read_text().splitlines())
    return {str(row["id"]): row for row in rows if row.get("success") is not None}


def pool_records(routes_dir: Path) -> list[dict[str, Any]]:
    records = []
    for run in POOL_RUNS:
        known = outcomes(routes_dir, run)
        for entry in json.loads((ROOT / f"configs/rollout/{run}.manifest.json").read_text()):
            if str(entry["id"]) in known:
                records.append({"id": str(entry["id"]), "scenario": entry["scenario"], "town": entry["town"],
                                "weather": entry["weather"], "failed": not known[str(entry["id"])]["success"]})
    return records


def family_rates(routes_dir: Path) -> dict[str, list[int]]:
    counts: dict[str, list[int]] = collections.defaultdict(lambda: [0, 0])
    for run in UNPLANTED_RUNS:
        for row in outcomes(routes_dir, run).values():
            counts[row["scenario"]][0] += 1
            counts[row["scenario"]][1] += not row["success"]
    return dict(counts)


def roads_of(families: tuple[str, ...]) -> list[dict[str, str]]:
    long_routes = [route for name in ("routes_validation.xml", "routes_training.xml")
                   for route in ET.parse(ROUTE_DATA / name).getroot().iter("route")]
    stock = [route for route in ET.parse(ROUTE_DATA / "bench2drive220.xml").getroot().iter("route")
             if next(route.iter("scenario")).get("type") in families]
    bases = stock + cuts_from(long_routes, set(families), [], CUT_SPEC, 90000)
    return [{"scenario": next(base.iter("scenario")).get("type", ""), "town": base.get("town", "")} for base in bases
            if LENGTH_RANGE_M[0] <= route_length(base) <= LENGTH_RANGE_M[1]]


def draw_evenly(roads: list[dict[str, str]], pairs: int, rng: random.Random) -> list[dict[str, str]]:
    by_family: dict[str, list[dict[str, str]]] = collections.defaultdict(list)
    for road in rng.sample(roads, len(roads)):
        by_family[road["scenario"]].append(road)
    chosen: list[dict[str, str]] = []
    while len(chosen) < pairs and any(by_family.values()):
        for family in sorted(by_family):
            if by_family[family] and len(chosen) < pairs:
                chosen.append(by_family[family].pop())
    return chosen


def passes_prd_91(slice_failures: int, neighbour_failures: int, pairs: int) -> bool:
    slice_rate, neighbour_rate = slice_failures / pairs, neighbour_failures / pairs
    table = [[slice_failures, pairs - slice_failures], [neighbour_failures, pairs - neighbour_failures]]
    return bool(slice_rate - neighbour_rate >= 0.2 and slice_rate >= 2 * neighbour_rate
                and fisher_exact(table, alternative="greater")[1] < 0.01)


def trial(pool: list[dict[str, Any]], roads: list[dict[str, str]], rates: dict[str, list[int]], slice_rate: float,
          patch_effect: float, pairs: int, rng: random.Random) -> tuple[float, str, bool]:
    records, key = list(pool), set()
    neighbour_failures = 0
    for index, road in enumerate(draw_evenly(roads, pairs, rng)):
        total, failed = rates[road["scenario"]]
        weather = rng.choice(pool)["weather"]
        slice_failed = rng.random() < slice_rate
        neighbour_failed = rng.random() < min(0.95, (failed + 1) / (total + 2) + patch_effect)
        records += [{**road, "weather": weather, "id": f"S{index}", "failed": slice_failed},
                    {**road, "weather": weather, "id": f"N{index}", "failed": neighbour_failed}]
        key |= {f"S{index}"} if slice_failed else set()
        neighbour_failures += neighbour_failed
    score, stratum = 0.0, ""
    for name, members in build_strata(records, TaxonomyConfig()).items():
        failing = {record["id"] for record in members if record["failed"]}
        overlap = len(failing & key) / max(1, len(failing | key))
        if overlap > score:
            score, stratum = overlap, f"{name[0]} = {name[1]}"
    return score, stratum, passes_prd_91(len(key), neighbour_failures, pairs)


def assess(pool: list[dict[str, Any]], families: tuple[str, ...], rates: dict[str, list[int]], slice_rate: float,
           patch_effect: float, pairs: int) -> dict[str, Any]:
    rng = random.Random(7)
    roads = roads_of(families)
    runs = [trial(pool, roads, rates, slice_rate, patch_effect, pairs, rng) for _ in range(TRIALS)]
    return {"pairs": pairs, "slice_failure_rate": slice_rate, "added_neighbour_failure_rate": patch_effect,
            "roads": len(roads), "expected_b2": round(mean(run[0] for run in runs), 3),
            "commonest_top_stratum": collections.Counter(run[1] for run in runs).most_common(1)[0][0],
            "chance_of_passing_prd_91": round(mean(float(run[2]) for run in runs), 3)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("routes_dir", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    pool, rates = pool_records(args.routes_dir), family_rates(args.routes_dir)
    results: dict[str, Any] = {"family_rates_n_failed": rates, "candidates": {}}
    results["candidates"]["P19 as run, to validate against the measured 0.857"] = [
        assess(pool, ("InvadingTurn",), rates, 0.79, 0.09, 53)]
    for name, families in list(CANDIDATES.items())[1:]:
        results["candidates"][name] = [assess(pool, families, rates, slice_rate, patch_effect, 40)
                                       for slice_rate in (0.5, 0.65, 0.8) for patch_effect in (0.0, 0.12, 0.24)]
    args.output.write_text(json.dumps(results, indent=1) + "\n")
    for name, rows in results["candidates"].items():
        print(name)
        for row in rows:
            print(" ", row)


if __name__ == "__main__":
    main()
