"""Layer sweep (PRD 9.2, Step 4) on synthetic shards with signals planted in known (site, layer) pairs.

The sweep exists to pick layers, so the behaviour to trust is that it ranks the planted layer first for the
metric it was planted in, that grouped cross-validation keeps variants of one base route together, and that
data a real capture may lack is skipped with a recorded reason instead of crashing.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pytest
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.discovery import layer_sweep  # noqa: E402

LAYERS, HIDDEN, FRAMES = 4, 16, 10
SITES = ("all_tokens", "driving_queries")
STATE_NAMES = (*layer_sweep.CONTINUOUS_STATES, *layer_sweep.BINARY_STATES)
FAILURE_PAIR = ("all_tokens", 2)
GAP_PAIR = ("driving_queries", 1)
DIRECTIONS = np.random.default_rng(7).normal(size=(4, HIDDEN))
FAIL_DIRECTION, GAP_DIRECTION, SPEED_DIRECTION, RED_DIRECTION = (
    direction / np.linalg.norm(direction) for direction in DIRECTIONS)


def write_shard(directory, index, base_id, success, rng, *, gaps=(), plant=True, states=True, vision=True):
    means = {site: rng.normal(size=(LAYERS, HIDDEN)) for site in SITES}
    frames = {site: rng.normal(size=(FRAMES, LAYERS, HIDDEN)) for site in SITES}
    speed = rng.normal(size=FRAMES)
    red = (rng.random(FRAMES) < 0.4).astype(float)
    if plant:
        means["all_tokens"][FAILURE_PAIR[1]] += 4 * FAIL_DIRECTION * (not success)
        means["driving_queries"][GAP_PAIR[1]] += 8 * GAP_DIRECTION * bool(gaps)
        frames["all_tokens"][:, FAILURE_PAIR[1]] += 2 * np.outer(speed, SPEED_DIRECTION) + 3 * np.outer(red, RED_DIRECTION)
    arrays = {"step": np.arange(5, 5 * (FRAMES + 1), 5, dtype=np.int32)}
    for site in SITES:
        arrays[site] = frames[site].astype(np.float16)
        arrays[f"{site}_episode_mean"] = means[site].astype(np.float32)
    if vision:
        arrays["vision_bridge"] = rng.normal(size=(FRAMES, HIDDEN)).astype(np.float16)
        arrays["vision_bridge_episode_mean"] = rng.normal(size=HIDDEN).astype(np.float32)
    for name in STATE_NAMES:
        arrays[name] = np.full(FRAMES, np.nan, dtype=np.float32)
    if states:
        arrays["ego_speed"], arrays["red_light"] = speed.astype(np.float32), red.astype(np.float32)
    route_id = f"r{index:03d}"
    np.savez(directory / f"{route_id}.npz", **arrays)
    (directory / f"{route_id}.json").write_text(json.dumps({
        "route_id": route_id, "base_id": base_id, "success": success, "practice_gaps": list(gaps),
        "dtype": "torch.float32", "n_steps": 5 * FRAMES}))


def build_pool(directory, *, bases=24, variants=2, failing_every=3, gap_size=8, **options):
    rng = np.random.default_rng(0)
    failing = [index for index in range(bases * variants) if index % failing_every == 0]
    gap = set(failing[:gap_size])
    for index in range(bases * variants):
        write_shard(directory, index, f"base{index // variants}", index not in failing, rng,
                    gaps=["P1"] if index in gap else (), **options)


def pair_values(report, metric):
    return {(row["site"], row["layer"]): row["metrics"][metric] for row in report["pairs"]}


def best_pair(report, metric):
    values = pair_values(report, metric)
    return max(values, key=values.get)


@pytest.fixture(scope="module")
def planted_report(tmp_path_factory):
    directory = tmp_path_factory.mktemp("planted")
    build_pool(directory)
    return layer_sweep.run_sweep(directory)


def test_each_planted_signal_ranks_its_layer_first(planted_report):
    assert best_pair(planted_report, "failure_auroc") == FAILURE_PAIR
    assert best_pair(planted_report, "state_r2:ego_speed") == FAILURE_PAIR
    assert best_pair(planted_report, "state_auroc:red_light") == FAILURE_PAIR
    assert best_pair(planted_report, "gap_jaccard:P1") == GAP_PAIR
    assert pair_values(planted_report, "gap_jaccard:P1")[GAP_PAIR] == 1.0


def test_selection_keeps_the_failure_layer_and_adds_the_gap_layer(planted_report):
    chosen = [(pick["site"], pick["layer"]) for pick in planted_report["chosen"]]
    assert FAILURE_PAIR in chosen and GAP_PAIR in chosen
    assert 2 <= len(chosen) <= 3
    assert len(planted_report["pairs"]) == len(SITES) * LAYERS + 1
    assert ("vision_bridge", 0) in pair_values(planted_report, "failure_auroc")


def test_report_records_counts_dtypes_and_skipped_states(planted_report):
    assert planted_report["episodes"] == {"success": 32, "failure": 16, "excluded_no_outcome": 0}
    assert planted_report["shards"] == 48
    assert planted_report["input_dtypes"] == ["torch.float32"]
    skipped = {entry["metric"] for entry in planted_report["skipped"]}
    assert skipped == {f"state:{name}" for name in STATE_NAMES} - {"state:ego_speed", "state:red_light"}
    assert planted_report["families_used"] == ["failure_auroc", "practice_gap_recovery", "state_probes"]


def test_grouped_folds_never_split_a_base_route(tmp_path):
    build_pool(tmp_path, bases=20, variants=3)
    shards = layer_sweep.load_shards(tmp_path)
    plans, _ = layer_sweep.build_plans(shards, layer_sweep.MIN_CLASS_EPISODES)
    folded = [(shards.base_ids, plans.failure.folds)]
    folded += [(shards.base_ids[shards.frame_episode[plan.rows]], plan.folds) for plan in plans.states]
    assert len(folded) == 3
    for groups, folds in folded:
        for train, test in folds:
            assert not set(groups[train]) & set(groups[test])


def test_variants_of_one_base_route_do_not_leak_the_outcome(tmp_path):
    rng = np.random.default_rng(3)
    for base in range(12):
        template = {site: rng.normal(size=(LAYERS, HIDDEN)) for site in SITES}
        for variant in range(5):
            index = base * 5 + variant
            write_shard(tmp_path, index, f"base{base}", bool(base % 2), rng, plant=False, states=False)
            archive = dict(np.load(tmp_path / f"r{index:03d}.npz"))
            for site in SITES:
                archive[f"{site}_episode_mean"] = (template[site] + 0.05 * rng.normal(size=(LAYERS, HIDDEN))).astype(np.float32)
            np.savez(tmp_path / f"r{index:03d}.npz", **archive)
    report = layer_sweep.run_sweep(tmp_path)
    assert np.mean(list(pair_values(report, "failure_auroc").values())) < 0.7
    shards = layer_sweep.load_shards(tmp_path)
    labels = (~shards.success).astype(int)
    ungrouped = list(StratifiedKFold(5, shuffle=True, random_state=0).split(labels, labels))
    scores = layer_sweep.out_of_fold(layer_sweep.logistic_probe(), "decision_function",
                                     shards.means["all_tokens"][:, 0, :], labels, ungrouped)
    assert roc_auc_score(labels, scores) > 0.9


def test_missing_states_gaps_and_small_classes_are_skipped_with_reasons(tmp_path):
    build_pool(tmp_path, bases=20, failing_every=15, gap_size=0, plant=False, states=False, vision=False)
    report = layer_sweep.run_sweep(tmp_path)
    reasons = {entry["metric"]: entry["reason"] for entry in report["skipped"]}
    assert set(reasons) == {"failure_auroc", "gap_jaccard", *(f"state:{name}" for name in STATE_NAMES)}
    assert all(reasons.values())
    assert "failing" in reasons["failure_auroc"]
    assert report["chosen"] == [] and report["families_used"] == []
    assert len(report["pairs"]) == len(SITES) * LAYERS


def test_a_lowered_class_minimum_runs_the_failure_probe(tmp_path):
    build_pool(tmp_path, bases=20, failing_every=15, gap_size=0, states=False, vision=False)
    report = layer_sweep.run_sweep(tmp_path, min_class_episodes=3)
    assert "failure_auroc" in report["pairs"][0]["metrics"]


def test_a_gap_with_two_failures_is_skipped(tmp_path):
    build_pool(tmp_path, gap_size=2)
    report = layer_sweep.run_sweep(tmp_path)
    reasons = {entry["metric"]: entry["reason"] for entry in report["skipped"]}
    assert "need 3" in reasons["gap:P1"]


def test_episodes_without_an_outcome_are_left_out(tmp_path):
    build_pool(tmp_path)
    sidecar = tmp_path / "r000.json"
    sidecar.write_text(json.dumps({**json.loads(sidecar.read_text()), "success": None}))
    report = layer_sweep.run_sweep(tmp_path)
    assert report["episodes"]["excluded_no_outcome"] == 1
    assert report["episodes"]["success"] + report["episodes"]["failure"] == 47


def row(site, layer, **metrics):
    return {"site": site, "layer": layer, "metrics": metrics, "gap_best_k": {}}


def ranked(rows):
    layer_sweep.add_ranks(rows)
    return rows


def test_ranks_average_ties_and_combine_families_by_mean():
    rows = ranked([row("all_tokens", 0, **{"failure_auroc": 0.9, "state_r2:ego_speed": 0.5, "state_auroc:red_light": 0.6}),
                   row("all_tokens", 1, **{"failure_auroc": 0.9, "state_r2:ego_speed": 0.1, "state_auroc:red_light": 0.9})])
    assert rows[0]["ranks"]["failure_auroc"] == rows[1]["ranks"]["failure_auroc"] == 1.5
    assert rows[0]["family_ranks"] == {"failure_auroc": 1.5, "state_probes": 1.5}
    assert rows[1]["combined_rank"] == 1.5


def test_choose_takes_two_best_combined_and_breaks_ties_by_site_then_layer():
    rows = ranked([row("all_tokens", 0, failure_auroc=0.9, **{"gap_jaccard:P1": 0.1}),
                   row("all_tokens", 1, failure_auroc=0.8, **{"gap_jaccard:P1": 0.2}),
                   row("driving_queries", 0, failure_auroc=0.7, **{"gap_jaccard:P1": 0.9}),
                   row("driving_queries", 1, failure_auroc=0.1, **{"gap_jaccard:P1": 0.3})])
    chosen = [(pick["site"], pick["layer"]) for pick in layer_sweep.choose(rows)]
    assert chosen == [("driving_queries", 0), ("all_tokens", 0)]


def test_choose_adds_the_best_gap_pair_when_it_is_not_in_the_top_two():
    rows = ranked([row("all_tokens", 0, failure_auroc=0.9, **{"gap_jaccard:P1": 0.2}),
                   row("all_tokens", 1, failure_auroc=0.8, **{"gap_jaccard:P1": 0.3}),
                   row("driving_queries", 0, failure_auroc=0.1, **{"gap_jaccard:P1": 0.9}),
                   row("driving_queries", 1, failure_auroc=0.2, **{"gap_jaccard:P1": 0.1})])
    chosen = layer_sweep.choose(rows)
    assert [(pick["site"], pick["layer"]) for pick in chosen] == [
        ("all_tokens", 0), ("all_tokens", 1), ("driving_queries", 0)]
    assert chosen[-1]["reason"] == "best practice-gap recovery"
