"""B3 behavioral stratification tests (docs/steps/b3-behavioral.md)."""
import ast
import json
import random
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from baselines import behavioral  # noqa: E402
from baselines.behavioral import (  # noqa: E402
    BehavioralConfig, Rollout, behavioral_directive, features, load_shard, window_rows,
)
from harness.schema import Gap  # noqa: E402
from harness.scoring import score  # noqa: E402

STEPS = np.arange(0, 400, 5)


def rollout(rid, *, failed=True, speed=8.0, lead=None, infractions=None, failure_step=None, rng=None):
    rng = rng or random.Random(rid)
    n = len(STEPS)
    states = {
        "ego_speed": np.full(n, speed) + (np.array([rng.uniform(-0.3, 0.3) for _ in range(n)]) if speed else 0.0),
        "lead_distance": np.full(n, np.nan if lead is None else lead),
        "lead_relative_speed": np.full(n, np.nan if lead is None else -2.0),
        "pedestrian_distance": np.full(n, np.nan),
        "junction_distance": np.full(n, 50.0),
        "time_to_junction": np.full(n, np.nan),
        "red_light": np.zeros(n),
        "occluded": np.zeros(n),
    }
    return Rollout(rid, STEPS.copy(), states, failed, dict(infractions or {}), failure_step)


def crashes(prefix, n):
    return [rollout("%s%02d" % (prefix, i), speed=12.0, lead=4.0, failure_step=300,
                    infractions={"collisions_vehicle": 1}) for i in range(n)]


def stalls(prefix, n):
    return [rollout("%s%02d" % (prefix, i), speed=0.0, infractions={"route_timeout": 1}) for i in range(n)]


def test_two_behaviors_become_two_axes_that_recover_matching_gaps():
    rollouts = crashes("c", 12) + stalls("s", 8) + [rollout("ok%d" % i, failed=False) for i in range(10)]
    d = behavioral_directive(rollouts, BehavioralConfig(budget_m=2))
    assert [len(a.rollouts) for a in d.axes] == [12, 8]
    gaps = [Gap("crash", "T2_interactional", {"c%02d" % i for i in range(12)}),
            Gap("stall", "T2_interactional", {"s%02d" % i for i in range(8)})]
    assert score(d, gaps).recall_by_tier["T2_interactional"] == 1.0


def test_axes_hold_failing_rollouts_only():
    rollouts = crashes("c", 5) + [rollout("ok%d" % i, failed=False, speed=12.0, lead=4.0) for i in range(5)]
    d = behavioral_directive(rollouts, BehavioralConfig(budget_m=3))
    claimed = set().union(*(a.rollouts for a in d.axes))
    assert claimed == {"c%02d" % i for i in range(5)}


def test_result_does_not_depend_on_input_order():
    rollouts = crashes("c", 10) + stalls("s", 7)
    shuffled = rollouts[:]
    random.Random(1).shuffle(shuffled)
    first = behavioral_directive(rollouts, BehavioralConfig(budget_m=3))
    second = behavioral_directive(shuffled, BehavioralConfig(budget_m=3))
    assert [a.rollouts for a in first.axes] == [a.rollouts for a in second.axes]


def test_axes_rank_by_size_and_score_is_share_of_failures():
    d = behavioral_directive(crashes("c", 4) + stalls("s", 9), BehavioralConfig(budget_m=2))
    assert [a.rank for a in d.axes] == [1, 2]
    assert d.axes[0].rollouts == {"s%02d" % i for i in range(9)}
    assert abs(d.axes[0].score - 9 / 13) < 1e-12


def test_fewer_failures_than_budget_caps_k_and_none_gives_empty_directive():
    assert len(behavioral_directive(crashes("c", 3), BehavioralConfig(budget_m=10)).axes) <= 3
    assert len(behavioral_directive(crashes("c", 1), BehavioralConfig()).axes) == 1
    assert behavioral_directive([rollout("ok", failed=False)], BehavioralConfig()).axes == []


def test_window_ends_at_first_collision_else_rollout_end():
    cfg = BehavioralConfig()
    hit = rollout("hit", failure_step=100)
    assert STEPS[window_rows(hit, cfg)].tolist() == list(range(40, 100, 5))
    timeout = rollout("timeout")
    assert STEPS[window_rows(timeout, cfg)].tolist() == list(range(340, 400, 5))


def test_window_uses_only_the_moments_before_failure():
    early = rollout("r", speed=2.0, failure_step=100)
    early.states["ego_speed"][STEPS >= 100] = 30.0
    row = dict(zip(behavioral.FEATURES, features(early, BehavioralConfig())))
    assert row["ego_speed_max"] < 3.0


def test_missing_actors_read_as_far_not_zero():
    row = dict(zip(behavioral.FEATURES, features(rollout("r"), BehavioralConfig())))
    assert row["lead_distance_min"] == 100.0 and row["pedestrian_distance_min"] == 100.0
    assert row["time_to_junction_min"] == 10.0 and row["lead_relative_speed_mean"] == 0.0


def test_stalls_and_infractions_are_features():
    row = dict(zip(behavioral.FEATURES, features(stalls("s", 1)[0], BehavioralConfig())))
    assert row["stationary_frac"] == 1.0
    assert row["infraction_route_timeout"] == 1.0 and row["infraction_collisions_vehicle"] == 0.0


def test_every_axis_is_named_and_schema_valid():
    d = behavioral_directive(crashes("c", 6) + stalls("s", 6), BehavioralConfig(budget_m=2))
    d.validate()
    names = [a.name for a in d.axes]
    assert all(n.strip() for n in names) and len(set(names)) == len(names)


def test_load_shard_reads_export_activations_output(tmp_path):
    sidecar = tmp_path / "123.json"
    sidecar.write_text(json.dumps({"route_id": "123", "success": False, "first_collision_step": 50,
                                   "infractions": {"collisions_vehicle": 2}}))
    np.savez(tmp_path / "123.npz", step=STEPS, ego_speed=np.ones(len(STEPS), dtype=np.float32))
    r = load_shard(sidecar)
    assert r.rollout_id == "123" and r.failed and r.failure_step == 50
    assert r.infractions == {"collisions_vehicle": 2} and "lead_distance" not in r.states
    (tmp_path / "124.json").write_text(json.dumps({"route_id": "124", "success": None}))
    assert load_shard(tmp_path / "124.json") is None


def test_penalized_copy_matches_the_adapter():
    tree = ast.parse((ROOT / "adapters/simlingo/sweep_local.py").read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", None) == "PENALIZED":
            assert ast.literal_eval(node.value) == behavioral.PENALIZED
            return
    raise AssertionError("PENALIZED not found in sweep_local.py")
