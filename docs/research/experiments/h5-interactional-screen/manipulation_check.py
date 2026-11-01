"""H5's C24 checks, per route, from each screen's shards and the raw frames.

Run on Savio from the repo root with the policy venv:
    .runtime/policy-venv/bin/python docs/research/experiments/h5-interactional-screen/manipulation_check.py OUT.json
"""

import json
import re
import sys
from pathlib import Path

import numpy as np
from PIL import Image

SCREENS = {"P10": ("step5-pilot-p10-screen", "40727203"),
           "P11": ("step5-pilot-p11-screen", "40727205"),
           "P12": ("step5-pilot-p12-screen", "40727207")}
BLIND_BOX = (0.55, 0.25, 1.0, 0.65)
MIRROR_BOX = (0.0, 0.25, 0.45, 0.65)
NEAR_METRES = 15.0
MOVING_METRES_PER_SECOND = 4.0
BLACK_LEVEL = 8
MIN_BLACK_FRACTION = 0.99
CHECK_ROUTES = 5
CHECK_REQUIRED = 4
EARLY_SIGHT_METRES = 30.0
TASK_ROUTE = re.compile(r"^=== route (\d+) ", re.MULTILINE)


def box_black_fraction(frame_path: Path, box: tuple[float, float, float, float]) -> float:
    pixels = np.asarray(Image.open(frame_path).convert("L"))
    height, width = pixels.shape
    left, top, right, bottom = box
    region = pixels[int(top * height):int(bottom * height), int(left * width):int(right * width)]
    return float((region <= BLACK_LEVEL).mean())


def lowest_black_fraction(route_dir: Path, box: tuple[float, float, float, float]) -> float | None:
    frames = sorted((route_dir / "frames").glob("*.png"))
    return min((box_black_fraction(frame, box) for frame in frames), default=None)


def walker_reading(shard: Path) -> dict[str, float | bool | None]:
    data = np.load(shard)
    distance, speed = data["pedestrian_distance"], data["ego_speed"]
    seen = ~np.isnan(distance)
    if not seen.any():
        return {"min_walker_m": None, "speed_at_min": None, "near_while_moving": False}
    nearest = int(np.nanargmin(distance))
    near_moving = bool(((distance < NEAR_METRES) & (speed > MOVING_METRES_PER_SECOND))[seen].any())
    early = np.flatnonzero(distance < EARLY_SIGHT_METRES)
    return {"min_walker_m": round(float(distance[nearest]), 2), "speed_at_min": round(float(speed[nearest]), 2),
            "near_while_moving": near_moving,
            "speed_when_first_within_30m": round(float(speed[early[0]]), 2) if early.size else None}


def walker_struck(route: dict) -> bool:
    return route["infractions"].get("collisions_pedestrian", 0) > 0


def route_row(gap: str, job: str, shards: Path, route: dict) -> dict:
    route_id = route["id"]
    row = {"id": route_id, "arm": "slice" if route_id[-2] == "7" else "neighbourhood", "base": route_id[:-2],
           "success": route.get("success"), "status": route.get("status"), "infractions": route.get("infractions", {}),
           "stationary_s": route.get("longest_stationary_sim_seconds"), "duration_s": route.get("duration_game")}
    shard = shards / f"{route_id}.npz"
    row |= walker_reading(shard) if shard.is_file() else {}
    row["walker_struck"] = walker_struck(row)
    if gap == "P11":
        box = BLIND_BOX if row["arm"] == "slice" else MIRROR_BOX
        row["lowest_black_fraction"] = lowest_black_fraction(Path("results/savio") / job / f"route-{route_id}", box)
    return row


def arm_rows(gap: str, name: str, job: str) -> list[dict]:
    folder = Path("results/savio") / name
    routes = [json.loads(line) for line in (folder / "routes.jsonl").read_text().splitlines()]
    return [route_row(gap, job, folder / "shards", route) for route in routes]


def run_order(job: str) -> list[str]:
    """Route ids in array order, read from each task's own log: 'first 5' in C24 means first to run."""
    ordered: list[str] = []
    for log in sorted(Path(".").glob(f"route-sample-{job}_*.out"), key=lambda path: int(path.stem.split("_")[1])):
        ordered += TASK_ROUTE.findall(log.read_text(errors="replace"))
    return ordered


def passes_check(row: dict) -> bool:
    return row.get("near_while_moving", False)


def passes_blind_check(row: dict) -> bool:
    walker_close = row.get("min_walker_m") is not None and row["min_walker_m"] < NEAR_METRES
    return walker_close and (row.get("lowest_black_fraction") or 0) >= MIN_BLACK_FRACTION


def check_summary(gap: str, job: str, rows: list[dict]) -> dict:
    passes = passes_blind_check if gap == "P11" else passes_check
    by_id = {row["id"]: row for row in rows}
    scored = [by_id[route_id] for route_id in run_order(job)
              if by_id[route_id]["arm"] == "slice" and by_id[route_id]["duration_s"] is not None]
    first_five = scored[:CHECK_ROUTES]
    return {"first_five": [row["id"] for row in first_five], "first_five_passing": sum(map(passes, first_five)),
            "required": CHECK_REQUIRED, "holds": sum(map(passes, first_five)) >= CHECK_REQUIRED,
            "all_slices_passing": sum(map(passes, scored)), "all_slices": len(scored)}


def main() -> None:
    table = {gap: arm_rows(gap, name, job) for gap, (name, job) in SCREENS.items()}
    checks = {gap: check_summary(gap, SCREENS[gap][1], table[gap]) for gap in SCREENS}
    Path(sys.argv[1]).write_text(json.dumps({"checks": checks, "routes": table}, indent=1) + "\n")


if __name__ == "__main__":
    main()
