"""Probe-residual discovery (M3a) tests: docs/steps/probe-residual.md."""
import json
import sys
import zlib
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from discovery.probe_residual import (  # noqa: E402
    STATES, ProbeResidualConfig, Rollout, fit_probes, load_shard, probe_residual_directive, residuals,
)
from harness.schema import Gap  # noqa: E402
from harness.scoring import score  # noqa: E402

STEPS = np.arange(0, 300, 5)
HIDDEN = 24
MIXING = np.random.default_rng(0).normal(size=(len(STATES), HIDDEN))


def true_states(rng, n):
    return {"lead_distance": rng.uniform(5, 50, n), "lead_relative_speed": rng.uniform(-5, 5, n),
            "pedestrian_distance": rng.uniform(5, 50, n), "red_light": rng.integers(0, 2, n).astype(float),
            "time_to_junction": rng.uniform(0, 10, n), "occluded": rng.integers(0, 2, n).astype(float)}


def rollout(rid, *, failed, misperceive=None, seed=None):
    """Activations encode the *perceived* state; misperceive maps a state to an offset added to it."""
    rng = np.random.default_rng(seed if seed is not None else zlib.crc32(rid.encode()))
    states = true_states(rng, len(STEPS))
    perceived = np.stack([states[s] + (misperceive or {}).get(s, 0.0) for s in STATES], axis=1)
    activations = perceived @ MIXING + rng.normal(scale=0.05, size=(len(STEPS), HIDDEN))
    return Rollout(rid, STEPS.copy(), activations, states, failed)


def corpus(n_success=40, groups=None):
    rollouts = [rollout("ok%02d" % i, failed=False, seed=1000 + i) for i in range(n_success)]
    for prefix, (n, offsets) in (groups or {}).items():
        rollouts += [rollout("%s%02d" % (prefix, i), failed=True, misperceive=offsets, seed=zlib.crc32(prefix.encode()) % 997 * 100 + i)
                     for i in range(n)]
    return rollouts


def test_two_kinds_of_misperception_become_two_axes():
    rollouts = corpus(groups={"far": (25, {"lead_distance": 30.0}), "ped": (25, {"pedestrian_distance": -30.0})})
    d = probe_residual_directive(rollouts, ProbeResidualConfig(budget_m=4))
    gaps = [Gap("far", "T2_interactional", {"far%02d" % i for i in range(25)}),
            Gap("ped", "T2_interactional", {"ped%02d" % i for i in range(25)})]
    assert score(d, gaps).recall_by_tier["T2_interactional"] == 1.0
    names = " | ".join(a.name for a in d.axes)
    assert "over-estimates lead_distance" in names and "under-estimates pedestrian_distance" in names


def test_probes_are_fitted_on_successes_only():
    rollouts = corpus(groups={"far": (25, {"lead_distance": 30.0})})
    probes = fit_probes([r for r in rollouts if not r.failed])
    failing = [r for r in rollouts if r.failed][0]
    error = residuals(failing, np.arange(len(STEPS)), probes)
    sigma = probes["lead_distance"].sigma
    assert abs(error[:, STATES.index("lead_distance")].mean() - 30.0 / sigma) < 0.2


def test_small_groups_fall_below_the_support_floor():
    rollouts = corpus(groups={"far": (25, {"lead_distance": 30.0}), "few": (8, {"pedestrian_distance": -30.0})})
    d = probe_residual_directive(rollouts, ProbeResidualConfig())
    claimed = set().union(*(a.rollouts for a in d.axes)) if d.axes else set()
    assert not any(r.startswith("few") for r in claimed)


def test_missing_state_values_contribute_zero_not_nan():
    rollouts = corpus()
    probes = fit_probes(rollouts)
    r = rollout("gap", failed=True)
    r.states["pedestrian_distance"][:] = np.nan
    error = residuals(r, np.arange(len(STEPS)), probes)
    assert np.all(error[:, STATES.index("pedestrian_distance")] == 0.0) and np.isfinite(error).all()


def test_too_few_failure_frames_gives_an_empty_directive():
    rollouts = corpus(groups={"far": (2, {"lead_distance": 30.0})})
    assert probe_residual_directive(rollouts, ProbeResidualConfig()).axes == []


def test_axes_hold_failing_rollouts_only_and_validate():
    rollouts = corpus(groups={"far": (25, {"lead_distance": 30.0})})
    d = probe_residual_directive(rollouts, ProbeResidualConfig())
    d.validate()
    assert all(not rid.startswith("ok") for a in d.axes for rid in a.rollouts)


def test_load_shard_reads_one_layer_of_one_site(tmp_path):
    (tmp_path / "7.json").write_text(json.dumps({"route_id": "7", "success": True}))
    queries = np.zeros((len(STEPS), 3, HIDDEN), dtype=np.float16)
    queries[:, 2] = 1.0
    np.savez(tmp_path / "7.npz", step=STEPS, driving_queries=queries,
             lead_distance=np.ones(len(STEPS), dtype=np.float32))
    r = load_shard(tmp_path / "7.json", "driving_queries", 2)
    assert r.activations.shape == (len(STEPS), HIDDEN) and r.activations.min() == 1.0
    assert not r.failed and set(r.states) == {"lead_distance"}
