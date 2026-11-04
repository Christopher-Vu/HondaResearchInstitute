"""B7's signal is frozen by docs/steps/b7-gap-signal.md. Any change to it, on purpose or not, must fail here.

A failure means the signal or its spec moved. Under the spec's own rule that change is post hoc wherever B7 is
reported, so update these pins only together with that label and a CONFLICTS.md entry. The golden numbers were
computed with this file's corpus and also reproduce on the code as signed off (f1dd409, 2026-10-16).
"""
import hashlib
import inspect
import re
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from baselines import activation_stats  # noqa: E402
from baselines.activation_stats import (  # noqa: E402
    ActivationStatsConfig,
    latent_scores,
    merge_latents,
    on_state,
)

SPEC = ROOT / "docs/steps/b7-gap-signal.md"
ROUTE_LIST = ROOT / "configs/baselines/b7_training_routes_v1.txt"
SPEC_SECTION_SHA256 = {
    "What B7 is for": "9f20f5192e164f057d5d6136f98871cea44921cf24329e1825b2fad3754468cb",
    "Decision 1: which activations the statistics are computed over": "a968a07d7bf4c30f14560ab55da3ba5ee35e34dd730f8e09a3cdae53c47f5e3b",
    "Procedure": "6f91bf516259714bbf1bc4c7d452a566fc17fa4e091b623df15afec8cae9dd6c",
    "What B7 may never use": "71fea39bd4895794075d06baae0e3fe92f7fec6760c6c1fe3b73673f897ec067",
    "Parameters": "c3a9cd07bae9c924fc1d58711368a268dc9366484d66bbf4e812e23a00d3d83f",
    "Settled 2026-10-09": "4d292ef2a16a6dfc9890b211a7b5fbc4ae042c43ca33db382762215a93676ea8",
    "Variant A sample drawn, 2026-10-15": "f8747ee270ccd315888d51690dcf71b75542fc73217a524042a4c373d21d88cc",
    "Signed off, 2026-10-16 (Chris)": "04db5374065f91998b2b652190e3e1edbb5512ab42295b58b10a3928d745f581",
}
ROUTE_LIST_SHA256 = "d163dd273a96b53b9bf7cb9c16e55189cd903d60a79584debae9a1b117e35ab1"
N_LATENTS = 12
GOLDEN_IDS = [1, 0, 2, 3, 5, 4, 6, 7]
GOLDEN_KAPPA = [3.5618648969, 2.718650799, 1.5923046986, 0.6519083894, -0.7445678785, -1.0699685273, -2.2455792314, -4.4646131467]
GOLDEN_AXES = [([1], ['e008', 'e014', 'e020'], 6), ([0], ['e003', 'e013', 'e028'], 5), ([2], ['e000', 'e001', 'e010'], 8), ([3], ['e009', 'e013', 'e015'], 8)]


def spec_sections():
    parts = re.split(r"^## (.+)$", SPEC.read_text(), flags=re.MULTILINE)
    return dict(zip(parts[1::2], parts[2::2]))


def sparse_episode(rng, frames):
    """Mostly exact zeros, as TopK leaves inactive latents, with runs of activation of varied strength on some latents."""
    acts = np.zeros((frames, N_LATENTS))
    for latent in range(N_LATENTS):
        for _ in range(rng.poisson(latent / 12 + 0.1)):
            start = rng.integers(0, frames)
            acts[start:start + rng.integers(1, 12), latent] = rng.uniform(0.02, 1.5)
    return acts


def corpus(seed, n):
    rng = np.random.default_rng(seed)
    return {"e%03d" % i: sparse_episode(rng, int(rng.integers(30, 90))) for i in range(n)}


def spec_on_state(column, tau=0.1):
    """Eq. 7, written out: on above tau, off at exactly 0, otherwise whatever it was."""
    state, states = False, []
    for value in column:
        if value > tau:
            state = True
        elif value == 0:
            state = False
        states.append(state)
    return states


def spec_statistics(episodes, latent):
    """Step 4 for one latent, over E+, the episodes where it is ever above 0. Coverage is |E+| over all episodes."""
    onsets, peaks, runs, active = [], [], [], 0
    for acts in episodes.values():
        column = acts[:, latent]
        if not (column > 0).any():
            continue
        active += 1
        states = spec_on_state(column)
        onset = sum(now and not before for before, now in zip([False] + states[:-1], states))
        onsets.append(onset)
        peaks.append(column.max())
        runs.append(sum(states) / onset / len(states) if onset else 0.0)
    return active, active / len(episodes), np.mean(onsets), np.mean(peaks), np.mean(runs)


def spec_kappa(episodes):
    """Steps 5 and 6: drop by floor and ceiling, then four equally weighted z-scores across the survivors."""
    rows = {}
    for latent in range(N_LATENTS):
        active, coverage, onsets, peak, run = (spec_statistics(episodes, latent) if any(
            (acts[:, latent] > 0).any() for acts in episodes.values()) else (0, 0.0, 0.0, 0.0, 0.0))
        if active >= 3 and coverage <= 0.5 and onsets > 0:
            rows[latent] = (-np.log(coverage), -abs(np.log(onsets)), peak, -run)
    table = np.array(list(rows.values()))
    z = (table - table.mean(axis=0)) / np.where(table.std(axis=0) == 0, 1.0, table.std(axis=0))
    return dict(zip(rows, z.sum(axis=1)))


def test_spec_sections_are_unchanged():
    sections = spec_sections()
    found = {title: hashlib.sha256(sections[title].encode()).hexdigest() for title in SPEC_SECTION_SHA256}
    assert found == SPEC_SECTION_SHA256


def test_route_list_is_the_committed_draw():
    assert hashlib.sha256(ROUTE_LIST.read_text().encode()).hexdigest() == ROUTE_LIST_SHA256
    assert sum(not line.startswith("#") for line in ROUTE_LIST.read_text().splitlines()) == 1000


def test_defaults_are_the_spec_parameters():
    cfg = ActivationStatsConfig()
    assert (cfg.tau_on, cfg.min_episodes, cfg.max_coverage, cfg.merge_jaccard) == (0.1, 3, 0.5, 0.5)
    assert cfg.variant == "A"
    table = spec_sections()["Parameters"]
    assert "| τ_on | 0.1," in table and "3 episodes; 50% of episodes" in table and "Jaccard ≥ 0.5" in table
    assert "N = 1,000 route directories (or all, if fewer), seed 0" in table and "Equal, 1 each" in table


def test_scores_match_the_golden_values():
    scores = latent_scores(corpus(20261104, 40), ActivationStatsConfig())
    assert scores.latent_ids.tolist() == GOLDEN_IDS
    assert scores.kappa.tolist() == pytest.approx(GOLDEN_KAPPA, abs=1e-9)


@pytest.mark.parametrize("seed", [1, 2, 3, 4])
def test_scores_match_an_independent_reading_of_the_spec(seed):
    episodes = corpus(seed, 30)
    expected = spec_kappa(episodes)
    scores = latent_scores(episodes, ActivationStatsConfig())
    assert set(scores.latent_ids.tolist()) == set(expected)
    for latent, kappa in zip(scores.latent_ids.tolist(), scores.kappa.tolist()):
        assert kappa == pytest.approx(expected[latent], abs=1e-9)
    assert scores.kappa.tolist() == sorted(scores.kappa.tolist(), reverse=True)


def test_firing_is_eq7_hysteresis_strictly_above_tau():
    column = np.array([0.05, 0.1, 0.11, 0.05, 0.001, 0.0, 0.05, 0.2, 0.0])
    assert on_state(column[:, None], 0.1)[:, 0].tolist() == spec_on_state(column)
    assert spec_on_state(column) == [False, False, True, True, True, False, False, True, False]


def test_axes_match_the_golden_merge():
    cfg = ActivationStatsConfig(budget_m=4)
    axes = merge_latents(latent_scores(corpus(20261104, 40), cfg), corpus(777, 40), cfg)
    assert [(axis.latents, sorted(axis.fire_set)[:3], len(axis.fire_set)) for axis in axes] == GOLDEN_AXES


def test_the_statistics_read_no_labels_and_no_frozen_input_signal():
    assert list(inspect.signature(latent_scores).parameters) == ["stat_episodes", "cfg"]
    assert "stale" not in inspect.getsource(activation_stats).lower()
