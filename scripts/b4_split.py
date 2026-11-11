"""The B4 split of docs/prereg-fail2drive.md section 2, on one model's scored Fail2Drive test pool.

A gap is B4-unnamed when no single level of configs/baselines/b4_factors_v1.yaml has failing rollouts whose
Jaccard with the gap's failing slice rollouts reaches 0.4. Levels are decided from the logged states in the
exported shards and the route's weather in the route XML; nothing reads scenario labels. Pairwise conjunctions
are reported as secondary.

Readings of the factor file's prose predicates, made here because the file states them in words:
- Weather: the route's weather keypoints are all checked; a level holds if any keypoint meets it.
- Fail2Drive routes have no dust storm or camera fault, so those levels are empty.
- cyclist_near uses two_wheeler_distance (bicycles and motorbikes).
- Lead deceleration: lead speed is ego_speed - lead_relative_speed; time between rows is the route's simulated
  seconds times its share of policy steps.
- cut_in: lead_distance < 10 m where the previous row had no lead or a lead more than 5 m farther away.

    python scripts/b4_split.py <shards dir> <routes.jsonl> <manifest.json> <route xml> --output <split.json>
"""
from __future__ import annotations

import argparse
import itertools
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from harness.scoring import jaccard  # noqa: E402

THRESHOLD = 0.4


def weather_by_route(xml_path: Path) -> dict[str, list[dict[str, float]]]:
    return {route.get("id"): [{k: float(v) for k, v in w.attrib.items()} for w in route.iter("weather")]
            for route in ET.parse(xml_path).getroot().iter("route")}


def any_weather(weathers: list[dict[str, float]], test) -> bool:
    return any(test(w) for w in weathers)


def levels_of(states: dict[str, np.ndarray], weathers: list[dict[str, float]], seconds: float, n_steps: int
              ) -> set[str]:
    """The B4 levels a rollout belongs to."""
    def anyof(key: str, test) -> bool:
        values = states[key]
        return bool(np.any(test(values[~np.isnan(values)])))
    out = set()
    if any_weather(weathers, lambda w: 0 <= w.get("sun_altitude_angle", 90) < 15):
        out.add("illumination.dusk")
    if any_weather(weathers, lambda w: w.get("sun_altitude_angle", 90) < 0):
        out.add("illumination.night")
    if any_weather(weathers, lambda w: 10 <= w.get("precipitation", 0) <= 60):
        out.add("precipitation.moderate")
    if any_weather(weathers, lambda w: w.get("precipitation", 0) > 60):
        out.add("precipitation.heavy")
    if any_weather(weathers, lambda w: 10 <= w.get("fog_density", 0) <= 50):
        out.add("fog.moderate")
    if any_weather(weathers, lambda w: w.get("fog_density", 0) > 50):
        out.add("fog.dense")
    if any_weather(weathers, lambda w: w.get("dust_storm", 0) > 0):
        out.add("airborne_particulate.dust_storm")
    vehicles = states["vehicles_50m"][~np.isnan(states["vehicles_50m"])]
    if len(vehicles) and vehicles.mean() < 3:
        out.add("traffic_density.low")
    if len(vehicles) and vehicles.mean() > 8:
        out.add("traffic_density.high")
    if anyof("pedestrian_distance", lambda v: v < 20):
        out.add("vulnerable_road_users.pedestrian_near")
    if anyof("two_wheeler_distance", lambda v: v < 20):
        out.add("vulnerable_road_users.cyclist_near")
    if anyof("animal_distance", lambda v: v < 50):
        out.add("novel_object_class.animal")
    if anyof("obstacle_distance", lambda v: v < 50):
        out.add("novel_object_class.unusual_obstacle")
    lead_speed = states["ego_speed"] - states["lead_relative_speed"]
    seconds_per_step = seconds / max(n_steps, 1)
    dt = np.diff(states["step"].astype(float)) * seconds_per_step
    with np.errstate(invalid="ignore", divide="ignore"):
        deceleration = -np.diff(lead_speed) / dt
    if np.any(deceleration[np.isfinite(deceleration)] > 4):
        out.add("lead_vehicle_behaviour.hard_brake")
    lead = states["lead_distance"]
    previous = np.concatenate([[np.nan], lead[:-1]])
    with np.errstate(invalid="ignore"):
        if np.any((lead < 10) & (np.isnan(previous) | (previous - lead > 5))):
            out.add("lead_vehicle_behaviour.cut_in")
        near_hazard = (states["pedestrian_distance"] < 30) | (lead < 30)
    if np.any((states["occluded"] > 0) & near_hazard):
        out.add("hazard_visibility.occluded")
    if anyof("junction_distance", lambda v: v < 10):
        out.add("road_geometry.junction")
    speed_kmh = states["ego_speed"][~np.isnan(states["ego_speed"])] * 3.6
    if len(speed_kmh) and speed_kmh.max() < 20:
        out.add("ego_speed_regime.low")
    if len(speed_kmh) and speed_kmh.max() > 60:
        out.add("ego_speed_regime.high")
    return out


def split(members: dict[str, set[str]], failed: dict[str, bool], gap_failing: dict[str, set[str]]
          ) -> dict[str, dict]:
    """Per gap: best single-level and best pairwise Jaccard against the gap's failing slice rollouts."""
    level_failing: dict[str, set[str]] = {}
    for route, levels in members.items():
        if failed.get(route):
            for level in levels:
                level_failing.setdefault(level, set()).add(route)
    pairs = {f"{a} & {b}": level_failing[a] & level_failing[b]
             for a, b in itertools.combinations(sorted(level_failing), 2)}
    report = {}
    for gap, failing in sorted(gap_failing.items()):
        single = sorted(((jaccard(failing, s), level) for level, s in level_failing.items()), reverse=True)
        pair = sorted(((jaccard(failing, s), name) for name, s in pairs.items()), reverse=True)
        best, level = single[0] if single else (0.0, None)
        report[gap] = {"failing_slice_rollouts": len(failing), "best_level": level, "best_jaccard": round(best, 4),
                       "split": "B4-named" if best >= THRESHOLD else "B4-unnamed",
                       "top_levels": [[name, round(j, 4)] for j, name in single[:3]],
                       "best_pairwise": [pair[0][1], round(pair[0][0], 4)] if pair else None}
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("shards", type=Path)
    parser.add_argument("routes", type=Path)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("xml", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = [json.loads(line) for line in args.routes.read_text().splitlines() if line.strip()]
    failed = {str(r["id"]): not r["success"] for r in rows if r.get("success") is not None}
    seconds = {str(r["id"]): float(r.get("duration_game") or 0) for r in rows}
    weathers = weather_by_route(args.xml)
    members = {}
    for sidecar in sorted(args.shards.glob("*.json")):
        route = sidecar.stem
        if route not in failed:
            continue
        data = np.load(sidecar.with_suffix(".npz"))
        n_steps = json.loads(sidecar.read_text())["n_steps"]
        members[route] = levels_of({k: data[k].astype(float) for k in data.files if data[k].ndim == 1},
                                   weathers.get(route, []), seconds[route], n_steps)
    manifest = json.loads(args.manifest.read_text())
    entries = manifest["rollouts"] if isinstance(manifest, dict) else manifest
    gap_failing: dict[str, set[str]] = {}
    for entry in entries:
        for gap in entry.get("practice_gaps", []):
            gap_failing.setdefault(gap, set())
            if failed.get(str(entry["id"])):
                gap_failing[gap].add(str(entry["id"]))
    report = {"rollouts_with_states": len(members), "threshold": THRESHOLD,
              "level_sizes": {}, "gaps": split(members, failed, gap_failing)}
    for levels in members.values():
        for level in levels:
            report["level_sizes"][level] = report["level_sizes"].get(level, 0) + 1
    args.output.write_text(json.dumps(report, indent=2))
    for gap, row in report["gaps"].items():
        print(f"{gap:32s} {row['split']:10s} {row['best_jaccard']:.3f} {row['best_level']}")


if __name__ == "__main__":
    main()
