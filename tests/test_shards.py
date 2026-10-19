"""The shard contract every adapter writes; the SimLingo export's own conformance is in test_export_activations."""
import json

import numpy as np
import pytest

from harness.shards import shard_problems

T, LAYERS, HIDDEN = 6, 3, 4
META = {"route_id": "r1", "base_id": "b1", "success": False, "infractions": {"red_light": 1},
        "first_collision_step": None}


def arrays(**changes):
    base = {"step": np.arange(0, 5 * T, 5), "site": np.zeros((T, LAYERS, HIDDEN), np.float16),
            "site_episode_mean": np.zeros((LAYERS, HIDDEN), np.float32), "ego_speed": np.ones(T, np.float32)}
    return {name: value for name, value in (base | changes).items() if value is not None}


def write(tmp_path, meta=META, **changes):
    (tmp_path / "r1.json").write_text(json.dumps(meta))
    np.savez(tmp_path / "r1.npz", **arrays(**changes))
    return tmp_path / "r1.json"


def test_a_minimal_policy_neutral_shard_conforms(tmp_path):
    assert shard_problems(write(tmp_path)) == []


def test_a_crashed_rollout_with_null_success_still_conforms(tmp_path):
    assert shard_problems(write(tmp_path, META | {"success": None})) == []


@pytest.mark.parametrize("key", ["route_id", "base_id", "success", "infractions", "first_collision_step"])
def test_each_required_sidecar_key_is_checked(tmp_path, key):
    meta = {name: value for name, value in META.items() if name != key}
    assert shard_problems(write(tmp_path, meta)) == [f"sidecar lacks {key}"]


@pytest.mark.parametrize("changes, problem", [
    ({"site": None, "site_episode_mean": None}, "npz has no (T, layers, hidden) activation site"),
    ({"site_episode_mean": None}, "site lacks a matching site_episode_mean"),
    ({"ego_speed": np.ones(T + 1)}, "state ego_speed has 7 rows for 6 steps"),
    ({"step": np.zeros(T, int)}, "step is not a 1-d increasing integer array"),
    ({"driving_query_tokens": np.zeros((T, 1, 2, HIDDEN))},
     "driving_query_tokens and driving_query_token_layers come together"),
])
def test_array_violations_are_named(tmp_path, changes, problem):
    assert problem in shard_problems(write(tmp_path, **changes))
