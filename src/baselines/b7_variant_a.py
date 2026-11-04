"""B7 variant A's fixed inputs, its route-head check's bend test, and the rule that reads Step 6's stop condition.

docs/steps/b7-gap-signal.md fixes the episode set (a seeded list of training route directories, every stored frame)
and docs/research/experiments/h16-b7-rollout-free/protocol.md fixes the rule. Neither reads an activation, and the rule
never reads the frozen-input signal, which is post hoc wherever it is reported.

Must never read the answer key. CI-enforced; see scripts/check_sealed_imports.py.
"""
from __future__ import annotations

import gzip
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from harness.bootstrap import MARGIN

ROUTE_LIST = Path(__file__).resolve().parents[2] / "configs/baselines/b7_training_routes_v1.txt"
CHUNKS = (
    "data_simlingo_lb1_split_routes_training_OppositeVehicleRunningRedLight_chunk_001.tar.gz",
    "data_simlingo_training_1_scenario_routes_training_random_weather_seed_1_balanced_150_chunk_009.tar.gz",
    "data_simlingo_training_3_scenarios_routes_training_random_weather_seed_3_balanced_100_chunk_005.tar.gz",
    "data_simlingo_training_3_scenarios_routes_training_random_weather_seed_3_balanced_100_chunk_007.tar.gz",
    "data_simlingo_training_3_scenarios_routes_training_random_weather_seed_3_balanced_100_chunk_012.tar.gz",
    "data_simlingo_training_3_scenarios_routes_training_random_weather_seed_3_balanced_100_chunk_013.tar.gz",
)
MIN_ROUTES = 950
MIN_DICTIONARIES = 9
MARGIN_TOLERANCE = 1e-9
MIN_BEND_M = 2.0
MATCHES, BELOW, NO_RECOVERY = "matches", "below", "no_recovery"
FIRES, PARTIAL, CLEAR, UNTESTED = "fires", "partial", "clear", "untested"
GAP_CLASS = {"P4_camera_occlusion": "T0_control", "P7_camera_freeze": "T0_control",
             "P8_camera_latency": "T0_control", "P19_wide_invading_turn": "T2_interactional"}


def read_route_list(path: Path = ROUTE_LIST) -> list[str]:
    """The committed route directories, as paths inside the released tars."""
    routes = [line.strip() for line in path.read_text().splitlines() if line.strip() and not line.startswith("#")]
    keys = [route_key(route) for route in routes]
    if len(set(keys)) != len(keys):
        raise ValueError("route list holds two directories with one name")
    return routes


def route_key(route: str) -> str:
    return route.rstrip("/").rsplit("/", 1)[-1]


def frame_stems(route_dir: Path) -> list[str]:
    """Every stored frame of a route, in order. A frame without its measurement loses the route, not the frame."""
    images = sorted(path.stem for path in (route_dir / "rgb").glob("*.jpg"))
    measurements = sorted(path.name.removesuffix(".json.gz") for path in (route_dir / "measurements").glob("*.json.gz"))
    if not images or images != measurements:
        raise ValueError(f"{route_dir.name}: {len(images)} images and {len(measurements)} measurements do not pair up")
    return images


def driving_prompt(speed: float) -> str:
    """The sentence SimLingo's agent builds in target-point mode (agent_simlingo.py, tick)."""
    return f"Current speed: {speed} m/s. Target waypoint: <TARGET_POINT><TARGET_POINT>. Predict the waypoints."


def read_measurement(route_dir: Path, stem: str) -> dict:
    with gzip.open(route_dir / "measurements" / f"{stem}.json.gz", "rt") as handle:
        return json.load(handle)


def measurement_inputs(measurement: dict) -> tuple[float, np.ndarray]:
    """Rounded speed and the two ego-frame target points, as the training loader reads them (dataset_driving.py)."""
    target_points = np.array([measurement["target_point"], measurement["target_point_next"]])
    if target_points.shape != (2, 2):
        raise ValueError(f"target points have shape {target_points.shape}")
    return round(measurement["speed"], 1), target_points


@dataclass(frozen=True)
class GapEvidence:
    """One gap and one B7 variant, over the dictionaries that count, on the plain latents only."""
    b7_recovers: bool
    b7_best: float
    b7_median: float
    methods_recover: bool
    methods_best: float
    methods_median: float
    claim_b_holds: bool


def gap_reading(evidence: GapEvidence) -> str:
    """MATCHES when B7 recovers the gap and our methods are not shown ahead of it, on both best and median."""
    if not evidence.b7_recovers:
        return BELOW if evidence.methods_recover else NO_RECOVERY
    median_ahead = evidence.methods_median - evidence.b7_median >= MARGIN - MARGIN_TOLERANCE
    return BELOW if evidence.claim_b_holds and median_ahead else MATCHES


def class_reading(gap_readings: dict[str, str]) -> str:
    """FIRES when every gap matches, PARTIAL when some do, NO_RECOVERY when nothing recovers any gap, else CLEAR."""
    if not gap_readings:
        return UNTESTED
    if set(gap_readings.values()) == {NO_RECOVERY}:
        return NO_RECOVERY
    matched = sum(reading == MATCHES for reading in gap_readings.values())
    if matched == len(gap_readings):
        return FIRES
    return PARTIAL if matched else CLEAR


def gap_scores(evidence: GapEvidence) -> dict[str, float]:
    """Reported beside every reading: a score under 0.5 cannot fire the rule, however close to our methods it sits."""
    return {"b7_best": evidence.b7_best, "b7_median": evidence.b7_median,
            "methods_best": evidence.methods_best, "methods_median": evidence.methods_median}


def stop_condition(evidence: dict[str, GapEvidence]) -> dict[str, dict]:
    """Per gap class: the class's reading, each gap's, and their scores. A gap with no known class is an error."""
    gaps = {gap_id: gap_reading(item) for gap_id, item in evidence.items()}
    by_class: dict[str, dict[str, str]] = {}
    for gap_id, reading in gaps.items():
        by_class.setdefault(GAP_CLASS[gap_id], {})[gap_id] = reading
    return {name: {"reading": class_reading(members), "gaps": members,
                   "scores": {gap_id: gap_scores(evidence[gap_id]) for gap_id in members}}
            for name, members in sorted(by_class.items())}


def variant_a_tested(routes_read: int, dictionaries_counting: int) -> bool:
    """Below these floors the rule is not read: variant A is reported as untested, which is not a clear."""
    return routes_read >= MIN_ROUTES and dictionaries_counting >= MIN_DICTIONARIES


def equal_spaced_route(points: np.ndarray) -> np.ndarray:
    """The 20 route points the route head is trained on, as dataset_base.equal_spacing_route computes them."""
    route = np.concatenate((np.zeros_like(points[:1]), points))
    shift = np.roll(route, 1, axis=0)
    shift[0] = shift[1]
    along = np.cumsum(np.linalg.norm(route - shift, axis=1)) + np.arange(len(route)) * 1e-4
    metres = np.arange(0, 20, 1)
    return np.stack([np.interp(metres, along, route[:, 0]), np.interp(metres, along, route[:, 1])], axis=1)


def route_bend_m(stored_route: np.ndarray) -> float:
    """How far sideways the stored route goes within the 20 m the route head predicts."""
    return float(np.abs(equal_spaced_route(stored_route)[:, 1]).max())


def route_check_saw_a_bend(rows: list[dict]) -> bool:
    """The route head catches wrong target points only on bends, so a check with no bend has tested nothing."""
    return any(row["route_bend_m"] >= MIN_BEND_M for row in rows)
