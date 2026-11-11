import importlib.util
from pathlib import Path

import numpy as np

spec = importlib.util.spec_from_file_location("b4_split", Path(__file__).resolve().parents[1] / "scripts/b4_split.py")
b4_split = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b4_split)


def states(**overrides):
    n = 4
    base = {key: np.full(n, np.nan) for key in ("lead_distance", "lead_relative_speed", "pedestrian_distance",
                                                "junction_distance", "two_wheeler_distance", "animal_distance",
                                                "obstacle_distance")}
    base.update(ego_speed=np.full(n, 10.0), vehicles_50m=np.full(n, 5.0), occluded=np.zeros(n),
                step=np.arange(0, 4 * 5, 5).astype(float))
    base.update({k: np.asarray(v, dtype=float) for k, v in overrides.items()})
    return base


def test_levels_come_from_logged_states_and_weather():
    levels = b4_split.levels_of(states(obstacle_distance=[np.nan, 40, np.nan, np.nan]),
                                [{"sun_altitude_angle": -5, "fog_density": 2}], seconds=20.0, n_steps=20)
    assert levels == {"illumination.night", "novel_object_class.unusual_obstacle"}


def test_a_gap_is_named_only_when_one_level_reaches_the_threshold():
    members = {"a": {"x"}, "b": {"x"}, "c": {"y"}, "d": {"y"}}
    failed = dict.fromkeys(members, True)
    report = b4_split.split(members, failed, {"G1": {"a", "b"}, "G2": {"a", "c", "x9", "x8", "x7"}})
    assert report["G1"]["split"] == "B4-named" and report["G1"]["best_jaccard"] == 1.0
    assert report["G2"]["split"] == "B4-unnamed"
