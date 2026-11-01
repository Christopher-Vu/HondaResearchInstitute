"""Contrastive diffing (PRD 9.2) on synthetic rollouts with a latent planted before some failures."""
import numpy as np

from discovery.contrastive import ContrastiveConfig, Rollout, contrastive_directive, window_rows, windows

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


def test_capping_the_failure_share_lets_a_specific_latent_lead():
    rng = np.random.default_rng(3)
    rollouts = []
    for index in range(80):
        failed, specific = index < 50, index < 25
        latents = rng.uniform(0, 0.05, size=(FRAMES, LATENTS))
        window = (STEPS >= 100) & (STEPS < 150)
        if failed:
            latents[window, 5] = 3.0
        if specific:
            latents[window, 3] = 1.0
        rollouts.append(Rollout(f"r{index}", latents, STEPS, failed, 150 if failed else None))
    plain, _ = contrastive_directive(rollouts, ContrastiveConfig())
    projected, _ = contrastive_directive(rollouts, ContrastiveConfig(max_failure_share=0.8))
    assert "latents [5" in plain.axes[0].description
    assert projected.axes[0].rollouts == {f"r{i}" for i in range(25)}



def test_firing_follows_b7s_hysteresis_so_a_latent_switched_on_before_the_window_stays_on():
    latents = np.zeros((FRAMES, LATENTS))
    latents[(STEPS >= 50) & (STEPS < 55), 3] = 1.0
    latents[STEPS >= 55, 3] = 0.05
    found = windows([Rollout("r0", latents, STEPS, True, 150)], ContrastiveConfig())
    assert found.fired[0, 3]
    latents[STEPS == 90, 3] = 0.0
    found = windows([Rollout("r0", latents, STEPS, True, 150)], ContrastiveConfig())
    assert not found.fired[0, 3]
