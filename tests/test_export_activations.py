"""Shard export: which steps are kept, what the episode means cover, and how older captures are read.

The export is the contract between a rollout's capture/steps.pt and the layer sweep, so the last test feeds
its output straight into the sweep's loader.
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
import pytest

torch = pytest.importorskip("torch")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import export_activations  # noqa: E402
from src.discovery import layer_sweep  # noqa: E402

LAYERS, HIDDEN = 3, 8
STATE = {"ego_speed": 4.0, "lead_distance": 12.5, "lead_relative_speed": -1.0, "pedestrian_distance": None,
         "traffic_light": "red", "junction_distance": 30.0, "time_to_junction": 7.5, "occluded": True}


def record(step, **extra):
    base = float(step)
    return {"step": step, "sequence_length": 573, "driving_tokens": 30,
            "layer_mean": torch.full((LAYERS, HIDDEN), base), "layer_driving_mean": torch.full((LAYERS, HIDDEN), -base),
            **extra}


def write_route(root, route_id, records, *, status="Completed", infractions=None, **capture_extra):
    route = root / f"route-{route_id}"
    (route / "capture").mkdir(parents=True)
    torch.save({"capture_every": 10, "dtype": "torch.bfloat16", "device": "cuda", "records": records,
                **capture_extra}, route / "capture/steps.pt")
    result = {"_checkpoint": {"records": [{
        "route_id": f"RouteScenario_{route_id}_rep0", "status": status, "town_name": "Town05",
        "infractions": infractions or {}, "scores": {"score_route": 100}, "meta": {"duration_game": 12.0}}]}}
    (route / "result.json").write_text(json.dumps(result))
    return route


def exported(tmp_path, records, manifest=None, **options):
    route = write_route(tmp_path / "routes", "77", records, **options)
    shards = tmp_path / "shards"
    shards.mkdir()
    meta = export_activations.export_route(route, shards, manifest or {}, stride=5)
    return meta, np.load(shards / "77.npz")


def test_only_steps_divisible_by_the_stride_are_kept_but_means_cover_every_step(tmp_path):
    meta, archive = exported(tmp_path, [record(step) for step in range(1, 13)])
    assert archive["step"].tolist() == [5, 10]
    assert archive["all_tokens"].shape == (2, LAYERS, HIDDEN) and archive["all_tokens"].dtype == np.float16
    assert archive["all_tokens"][:, 0, 0].tolist() == [5.0, 10.0]
    assert archive["all_tokens_episode_mean"].dtype == np.float32
    assert np.allclose(archive["all_tokens_episode_mean"], 6.5)
    assert np.allclose(archive["driving_queries_episode_mean"], -6.5)
    assert "vision_bridge" not in archive.files
    assert meta["n_steps"] == 12 and meta["dtype"] == "torch.bfloat16"


def test_vision_bridge_is_exported_when_every_record_has_it(tmp_path):
    records = [record(step, vision_bridge_mean=torch.full((HIDDEN,), float(step))) for step in range(1, 11)]
    _, archive = exported(tmp_path, records)
    assert archive["vision_bridge"].shape == (2, HIDDEN)
    assert np.allclose(archive["vision_bridge_episode_mean"], 5.5)


def test_older_captures_without_state_give_nan_arrays(tmp_path):
    _, archive = exported(tmp_path, [record(step) for step in range(1, 11)])
    for name in (*export_activations.CONTINUOUS_STATES, "red_light", "occluded"):
        assert archive[name].shape == (2,) and np.isnan(archive[name]).all()


def test_state_values_traffic_light_and_errors_map_to_floats_and_nan(tmp_path):
    records = [record(step, state=STATE if step == 5 else {"error": "no sensor"} if step == 10 else None)
               for step in range(1, 16)]
    _, archive = exported(tmp_path, records)
    assert archive["ego_speed"][0] == 4.0 and math.isnan(archive["ego_speed"][1]) and math.isnan(archive["ego_speed"][2])
    assert math.isnan(archive["pedestrian_distance"][0])
    assert archive["red_light"][0] == 1.0 and archive["occluded"][0] == 1.0
    assert math.isnan(archive["red_light"][1])


def test_green_yellow_and_no_light_are_not_red(tmp_path):
    lights = {5: "green", 10: "yellow", 15: "none"}
    records = [record(step, state={**STATE, "traffic_light": lights.get(step, "red")}) for step in range(1, 16)]
    _, archive = exported(tmp_path, records)
    assert archive["red_light"].tolist() == [0.0, 0.0, 0.0]


def test_outcome_manifest_and_first_collision_land_in_the_sidecar(tmp_path):
    manifest = {"77": {"id": "77", "base_id": "26956", "scenario": "DynamicObjectCrossing", "role": "p2_slice",
                       "practice_gaps": ["P2"]}}
    collisions = [{"step": 9, "frame": 90, "other": "car", "intensity": 5.0},
                  {"step": 7, "frame": 70, "other": "car", "intensity": 1.0}]
    meta, _ = exported(tmp_path, [record(step) for step in range(1, 11)], manifest, collisions=collisions,
                       infractions={"collisions_vehicle": ["hit"]})
    assert meta["base_id"] == "26956" and meta["practice_gaps"] == ["P2"] and meta["role"] == "p2_slice"
    assert meta["scenario"] == "DynamicObjectCrossing"
    assert meta["success"] is False and meta["infractions"] == {"collisions_vehicle": 1}
    assert meta["first_collision_step"] == 7


def test_a_route_without_a_valid_outcome_has_null_success_and_no_manifest_defaults(tmp_path):
    meta, _ = exported(tmp_path, [record(step) for step in range(1, 11)], status="Failed - Simulation crashed")
    assert meta["success"] is None
    assert meta["base_id"] == "77" and meta["practice_gaps"] == [] and meta["first_collision_step"] is None


def test_route_id_falls_back_to_the_result_file(tmp_path):
    route = write_route(tmp_path, "26956", [record(1)])
    route = route.rename(tmp_path / "attempt-1")
    assert export_activations.route_id_of(route) == "26956"


def test_export_all_finds_routes_under_a_parent_and_the_sweep_loads_the_shards(tmp_path):
    for route_id in ("a1", "b2"):
        write_route(tmp_path / "job", route_id, [record(step) for step in range(1, 21)])
    exported_routes = export_activations.export_all([tmp_path / "job"], tmp_path / "shards", stride=5)
    assert [meta["route_id"] for meta in exported_routes] == ["a1", "b2"]
    shards = layer_sweep.load_shards(tmp_path / "shards")
    assert shards.means["all_tokens"].shape == (2, LAYERS, HIDDEN)
    assert shards.frames["driving_queries"].shape == (8, LAYERS, HIDDEN)
    assert shards.frame_episode.tolist() == [0] * 4 + [1] * 4
