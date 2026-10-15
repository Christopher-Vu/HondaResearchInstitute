"""Contrastive diffing (PRD 9.2) on synthetic rollouts with a latent planted before some failures."""
import numpy as np
import pytest

from discovery.contrastive import ContrastiveConfig, Rollout, contrastive_directive, window_rows

LATENTS, FRAMES = 12, 40
STEPS = np.arange(0, FRAMES * 5, 5)


def rollout(index, failed, plant=False, everywhere=False, rng=np.random.default_rng(0)):
    latents = rng.uniform(0, 0.05, size=(FRAMES, LATENTS))
    collision = 150 if failed else None
    if plant:
        latents[(STEPS >= 100) & (STEPS < 150), 3] = 1.0
    if everywhere:
        latents[:, 7] = 1.0
    return Rollout(f"r{index}", latents, STEPS, failed, collision)


def pool(planted=30, other_failures=20, successes=60, everywhere=False):
    rollouts = [rollout(i, True, plant=True, everywhere=everywhere) for i in range(planted)]
    rollouts += [rollout(100 + i, True, everywhere=everywhere) for i in range(other_failures)]
    rollouts += [rollout(200 + i, False, everywhere=everywhere) for i in range(successes)]
    return rollouts


def test_a_latent_planted_before_failures_becomes_the_top_axis_holding_exactly_those_rollouts():
    directive, effects = contrastive_directive(pool(), ContrastiveConfig())
    assert directive.axes and "latents [3]" in directive.axes[0].description
    assert directive.axes[0].rollouts == {f"r{i}" for i in range(30)}
    assert effects["q"][3] < 0.05


def test_a_latent_firing_everywhere_is_not_kept_and_small_support_is_dropped():
    directive, _ = contrastive_directive(pool(everywhere=True), ContrastiveConfig())
    assert all("7" not in axis.description.split("]")[0] for axis in directive.axes)
    small, _ = contrastive_directive(pool(planted=10), ContrastiveConfig())
    assert not small.axes


def test_failure_windows_end_at_the_first_collision_or_the_last_frame():
    import random
    config = ContrastiveConfig()
    crashed = Rollout("a", np.zeros((FRAMES, 1)), STEPS, True, 150)
    assert STEPS[window_rows(crashed, config, random.Random(0))].tolist() == list(range(90, 150, 5))
    timed_out = Rollout("b", np.zeros((FRAMES, 1)), STEPS, True, None)
    assert STEPS[window_rows(timed_out, config, random.Random(0))].max() == STEPS[-1]


def test_dev_eval_runs_end_to_end_on_synthetic_shards(tmp_path):
    torch = pytest.importorskip("torch")
    import json
    from discovery import dev_eval, sae
    shards = tmp_path / "shards"
    shards.mkdir()
    rng = np.random.default_rng(1)
    for index in range(12):
        failed = index < 6
        tokens = rng.normal(size=(8, 1, 30, 16)).astype(np.float16)
        np.savez(shards / f"r{index}.npz", driving_query_tokens=tokens, driving_query_token_layers=np.array([10]),
                 step=np.arange(0, 40, 5))
        (shards / f"r{index}.json").write_text(json.dumps({
            "route_id": f"r{index}", "base_id": f"b{index}", "success": not failed, "first_collision_step": None,
            "practice_gaps": ["G"] if index < 4 else []}))
    tokens, bases = sae.load_tokens([shards], 10)
    model, _ = sae.train(sae.normalise(tokens.float()), sae.SaeConfig(layer=10, k=4, epochs=2, batch=64),
                         torch.device("cpu"))
    (tmp_path / "run").mkdir()
    torch.save({"config": {"layer": 10, "k": 4}, "state": model.state_dict()}, tmp_path / "run/sae.pt")
    gaps = [dev_eval.Gap("G", "T0_control", dev_eval.gap_failures([shards], ["G"])["G"])]
    report = dev_eval.evaluate_run(tmp_path / "run", [shards], gaps, [], torch.device("cpu"))
    assert report["failing"] == 6 and gaps[0].failing_rollouts == {"r0", "r1", "r2", "r3"}
    assert set(report) >= {"contrastive", "B7_pool", "B2_taxonomy", "B1_random"}
