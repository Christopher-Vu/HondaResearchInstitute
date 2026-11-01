"""H1 dev evaluation (docs/research/experiments/h1-planted-gap-recovery/protocol.md) on small synthetic corpora."""
import dataclasses
import json
import shutil
import sys
import zlib
from pathlib import Path

import numpy as np
import pytest

torch = pytest.importorskip("torch")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from baselines import behavioral  # noqa: E402
from discovery import contrastive, dev_eval, probe_residual, sae  # noqa: E402
from discovery.probe_residual import STATES  # noqa: E402
from harness.schema import AxisCard, Directive, Gap, SupportingEpisode  # noqa: E402

CPU = torch.device("cpu")
GAP = "G_planted"
STEPS = np.arange(0, 300, 5)
HIDDEN, LAYERS, LAYER = 24, 2, 1
MIXING = np.random.default_rng(0).normal(size=(len(STATES), HIDDEN))
SPIKE = 12.0


def true_states(rng):
    return {"lead_distance": rng.uniform(5, 50, len(STEPS)), "lead_relative_speed": rng.uniform(-5, 5, len(STEPS)),
            "pedestrian_distance": rng.uniform(5, 50, len(STEPS)), "red_light": rng.integers(0, 2, len(STEPS)).astype(float),
            "time_to_junction": rng.uniform(0, 10, len(STEPS)), "occluded": rng.integers(0, 2, len(STEPS)).astype(float),
            "ego_speed": rng.uniform(2, 10, len(STEPS))}


def spiked_frames(rng, states, planted):
    """Pure noise at every layer; a planted rollout gets a large component on hidden unit 0 at the chosen layer."""
    frames = rng.normal(size=(len(STEPS), LAYERS, HIDDEN))
    if planted:
        frames[:, LAYER, 0] += SPIKE
    return frames


def misperceived_frames(rng, states, planted):
    """The chosen layer encodes the perceived state list; a planted rollout perceives the lead as 30 m further."""
    frames = rng.normal(size=(len(STEPS), LAYERS, HIDDEN))
    perceived = np.stack([states[name] + (30.0 if planted and name == "lead_distance" else 0.0) for name in STATES], axis=1)
    frames[:, LAYER] = perceived @ MIXING + rng.normal(scale=0.05, size=(len(STEPS), HIDDEN))
    return frames


def write_rollout(directory, route_id, base_id, *, success, frames, states, role=None, gaps=()):
    np.savez(directory / f"{route_id}.npz", driving_queries=frames, step=STEPS.astype(np.int32),
             **{name: values.astype(np.float32) for name, values in states.items()})
    (directory / f"{route_id}.json").write_text(json.dumps({
        "route_id": route_id, "base_id": base_id, "scenario": "S%d" % (zlib.crc32(base_id.encode()) % 3),
        "town": "Town01", "success": success, "infractions": {} if success else {"collisions_vehicle": 1},
        "first_collision_step": None if success else 250, "practice_gaps": list(gaps), "role": role}))


def write_corpus(directory, make_frames, *, n_planted=25, n_neighbour_failures=5, n_background_failures=30,
                 n_successes=60):
    """Planted failures with their neighbourhood routes on shared base routes, plus background failures and successes."""
    directory.mkdir(parents=True, exist_ok=True)
    specs = []
    for i in range(n_planted):
        specs.append((f"gap{i:02d}", f"gb{i}", False, True, "pilot_slice", [GAP]))
        specs.append((f"nb{i:02d}", f"gb{i}", i < n_planted - n_neighbour_failures, False, "pilot_neighbourhood", []))
    specs += [(f"bgf{i:02d}", f"bf{i // 2}", False, False, None, []) for i in range(n_background_failures)]
    specs += [(f"ok{i:02d}", f"o{i // 3}", True, False, None, []) for i in range(n_successes)]
    for route_id, base_id, success, planted, role, gaps in specs:
        rng = np.random.default_rng(zlib.crc32(route_id.encode()))
        states = true_states(rng)
        write_rollout(directory, route_id, base_id, success=success, frames=make_frames(rng, states, planted),
                      states=states, role=role, gaps=gaps)
    write_manifest(directory, [spec[0] for spec in specs])


def write_manifest(directory, route_ids):
    entries = [{"id": route_id, "scenario": "S%d" % (zlib.crc32(route_id.encode()) % 3), "town": "Town01", "weather": {},
                "practice_gaps": [GAP], "sensor": {"camera_fault": {"kind": "occlusion"}}} for route_id in route_ids]
    (directory.parent / "manifest.json").write_text(json.dumps(entries))


def exact_sae(directory, *, seed=0, layer=LAYER, k=2 * HIDDEN):
    """A signed-pair SAE that reconstructs its input exactly; unit 0's positive latent fires only above 0.7."""
    identity = torch.eye(HIDDEN)
    pre_bias = torch.zeros(HIDDEN)
    pre_bias[0] = 0.7
    model = sae.TopKSae(HIDDEN, 2 * HIDDEN, k, pre_bias)
    model.encoder.data = torch.cat([identity, -identity])
    model.decoder.data = torch.cat([identity, -identity], dim=1)
    save_sae(directory, model, layer, k, seed)


def random_sae(directory, *, layer=LAYER):
    torch.manual_seed(0)
    save_sae(directory, sae.TopKSae(HIDDEN, HIDDEN, 2, torch.zeros(HIDDEN)), layer, 2, 0)


def save_sae(directory, model, layer, k, seed):
    directory.mkdir(parents=True, exist_ok=True)
    torch.save({"config": {"layer": layer, "k": k, "seed": seed}, "state": model.state_dict()}, directory / "sae.pt")


def run_evaluate(tmp_path, sae_runs=(), replicates=50):
    return dev_eval.evaluate([tmp_path / "shards"], LAYER, list(sae_runs), [GAP], [str(tmp_path / "manifest.json")],
                             CPU, replicates)


@pytest.fixture(scope="module")
def spiked(tmp_path_factory):
    root = tmp_path_factory.mktemp("spiked")
    write_corpus(root / "shards", spiked_frames)
    exact_sae(root / "exact")
    random_sae(root / "random")
    return root


def test_contrastive_over_an_sae_recovers_the_planted_failures_and_the_audit_says_slice_not_neighbourhood(spiked):
    result = run_evaluate(spiked, [spiked / "exact"])
    verdict = result["gaps"][GAP]
    assert result["saes"][0]["explained_variance"] > 0.99 and result["saes"][0]["counts"]
    for family in ("M1_raw", "M1_capped"):
        best = verdict["best_by_family"][family]
        assert best["best_jaccard"] > 0.9 and best["pilot_slice"] == 25 and best["pilot_neighbourhood"] == 0
    assert verdict["claim_a"] and verdict["key_size"] == 25
    assert verdict["catch_all"] == pytest.approx(25 / 60)


def test_neighbourhood_failures_are_background_not_part_of_the_key(spiked):
    corpus = run_evaluate(spiked)["corpus"]
    assert corpus["rollouts"] == 140 and corpus["failures"] == 60 and corpus["key"] == {GAP: 25}
    assert corpus["sources"][str(spiked / "shards")]["key"] == {GAP: 25}


def test_an_sae_that_explains_under_80_percent_is_reported_but_does_not_count(spiked):
    result = run_evaluate(spiked, [spiked / "exact", spiked / "random"])
    poor = next(info for info in result["saes"] if info["run"].endswith("random"))
    assert poor["explained_variance"] < dev_eval.MIN_EXPLAINED_VARIANCE and not poor["counts"]
    for label, method in result["methods"].items():
        assert method["counts"] == (not label.endswith("random"))
    verdict = result["gaps"][GAP]
    assert not verdict["best_activation"]["method"].endswith("random")
    assert not verdict["best_baseline"]["method"].endswith("random")


def test_an_sae_for_another_layer_is_skipped_with_a_note(spiked, tmp_path):
    exact_sae(tmp_path / "other", layer=14)
    result = run_evaluate(spiked, [tmp_path / "other", tmp_path / "missing"])
    assert result["saes"] == [] and len(result["skipped_saes"]) == 2
    assert "14" in result["skipped_saes"][0]["reason"]
    assert {run["family"] for run in result["methods"].values()} == {"M2_probe_residual", "B2_taxonomy", "B3_behavioral"}


def test_without_an_sae_probe_residual_alone_recovers_a_planted_misperception(tmp_path):
    write_corpus(tmp_path / "shards", misperceived_frames)
    result = run_evaluate(tmp_path)
    best = result["gaps"][GAP]["best_by_family"]["M2_probe_residual"]
    assert best["best_jaccard"] > 0.9 and best["pilot_neighbourhood"] == 0
    assert result["gaps"][GAP]["claim_a"] and result["B1_random"][0]["sizes_from"] == "fallback"


def directives_by_label(tmp_path, sae_runs):
    shards = dev_eval.load_shards([tmp_path / "shards"])
    frames = [dev_eval.read_frames(shard, LAYER) for shard in shards]
    records = dev_eval.taxonomy_records([str(tmp_path / "manifest.json")],
                                        {shard.route_id: not shard.meta["success"] for shard in shards})
    runs = dev_eval.run_saes(sae_runs, frames, LAYER, CPU)[0] + dev_eval.non_sae_methods(shards, LAYER, records)
    return {run.label: [sorted(axis.rollouts) for axis in run.directive.axes] for run in runs}


def test_methods_do_not_change_when_the_answer_key_and_roles_are_scrambled(spiked, tmp_path):
    shutil.copytree(spiked / "shards", tmp_path / "shards")
    shutil.copy(spiked / "manifest.json", tmp_path / "manifest.json")
    before = directives_by_label(tmp_path, [spiked / "exact"])
    for sidecar in (tmp_path / "shards").glob("*.json"):
        meta = json.loads(sidecar.read_text())
        sidecar.write_text(json.dumps({**meta, "practice_gaps": ["scrambled"], "role": "pilot_neighbourhood",
                                       "sensor": {"camera_fault": {"kind": "freeze"}}}))
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    (tmp_path / "manifest.json").write_text(json.dumps(
        [{**entry, "practice_gaps": [], "sensor": {"camera_fault": {"kind": "none"}}} for entry in manifest]))
    assert directives_by_label(tmp_path, [spiked / "exact"]) == before


def test_method_inputs_carry_no_answer_key_or_pilot_role():
    forbidden = {"practice_gaps", "sensor", "role", "neighbourhood_of", "base_id"}
    for kind in (contrastive.Rollout, probe_residual.Rollout, behavioral.Rollout, dev_eval.Frames):
        assert forbidden.isdisjoint(field.name for field in dataclasses.fields(kind))


def test_taxonomy_sees_only_scenario_weather_and_town(spiked):
    records = dev_eval.taxonomy_records([str(spiked / "manifest.json")], {"gap00": True, "ok00": False})
    assert {frozenset(record) for record in records} == {frozenset({"id", "scenario", "weather", "town", "failed"})}
    assert [record["failed"] for record in records] == [True, False]


def test_rollouts_without_an_outcome_are_left_out_and_repeated_ids_are_refused(tmp_path):
    directory = tmp_path / "a"
    directory.mkdir()
    rng = np.random.default_rng(0)
    states = true_states(rng)
    for route_id, success in (("done", True), ("unfinished", None)):
        write_rollout(directory, route_id, route_id, success=success, frames=spiked_frames(rng, states, False), states=states)
    assert [shard.route_id for shard in dev_eval.load_shards([directory])] == ["done"]
    other = tmp_path / "b"
    other.mkdir()
    write_rollout(other, "done", "done", success=True, frames=spiked_frames(rng, states, False), states=states)
    with pytest.raises(ValueError, match="done"):
        dev_eval.load_shards([directory, other])


def axis_directive(method, *rollout_sets):
    axes = [AxisCard(f"{method}-{i}", f"axis {i}", "test axis", i + 1, 1.0, method,
                     supporting_episodes=[SupportingEpisode(r, 1.0, (0, 0)) for r in sorted(members)])
            for i, members in enumerate(rollout_sets)]
    return Directive(method, axes)


def clustered_pool():
    rollouts = [f"r{i:02d}" for i in range(80)]
    return rollouts, {rollout: f"b{int(rollout[1:]) // 2}" for rollout in rollouts}


def test_bootstrap_interval_for_a_clear_advantage_excludes_zero_and_contains_the_point_delta():
    rollouts, base_of = clustered_pool()
    key = set(rollouts[:40])
    gap = Gap(GAP, "T0_control", key)
    runs = [dev_eval.MethodRun("M2_probe_residual", dev_eval.ACTIVATION, axis_directive("probe_residual", key)),
            dev_eval.MethodRun("B3_behavioral", dev_eval.BASELINE,
                               axis_directive("B3_behavioral", set(rollouts[:20]) | set(rollouts[40:60])))]
    deltas = dev_eval.bootstrap_deltas(runs, [gap], base_of, 300)[GAP]
    low, high = np.percentile(deltas, [2.5, 97.5])
    point = 1.0 - 20 / 60
    assert 0 < low <= point <= high
    assert np.array_equal(deltas, dev_eval.bootstrap_deltas(runs, [gap], base_of, 300)[GAP])


def test_bootstrap_retakes_the_best_baseline_in_every_replicate():
    rollouts, base_of = clustered_pool()
    gap = Gap(GAP, "T0_control", set(rollouts[:40]))
    exact = axis_directive("probe_residual", set(rollouts[:40]))
    first_half, second_half = (axis_directive("B3_behavioral", set(rollouts[:30])),
                               axis_directive("B2_taxonomy", set(rollouts[10:40])))
    runs = [dev_eval.MethodRun("M2_probe_residual", dev_eval.ACTIVATION, exact),
            dev_eval.MethodRun("B3_behavioral", dev_eval.BASELINE, first_half),
            dev_eval.MethodRun("B2_taxonomy", dev_eval.BASELINE, second_half)]
    both = dev_eval.bootstrap_deltas(runs, [gap], base_of, 300)[GAP]
    only_first = dev_eval.bootstrap_deltas(runs[:2], [gap], base_of, 300)[GAP]
    assert (both <= only_first + 1e-12).all() and (both < only_first - 1e-9).any()


def sae_run(seed, layer=10, k=48, explained=0.95):
    return dev_eval.MethodRun("M1_raw", dev_eval.ACTIVATION, axis_directive("contrastive"),
                              dev_eval.SaeInfo(f"dir-{seed}-{layer}-{k}", layer, k, seed, explained))


def results_for(runs, jaccards):
    return {run.label: {"gaps": {GAP: {"best_jaccard": value}}} for run, value in zip(runs, jaccards)}


def test_seeds_are_grouped_by_saved_layer_and_k_and_must_beat_the_best_baseline_to_count():
    same_cell = [sae_run(seed) for seed in range(6)]
    elsewhere = [sae_run(seed, k=96) for seed in range(2)] + [sae_run(0, layer=14)]
    weak = sae_run(6, explained=0.5)
    runs = same_cell + [weak] + elsewhere
    results = results_for(runs, [0.8, 0.8, 0.8, 0.8, 0.4, 0.4, 0.9, 1.0, 1.0, 1.0])
    stability = dev_eval.seed_stability(same_cell[0], runs, results, GAP, baseline_jaccard=0.5)
    assert stability == {"seeds_beating": 4, "seeds_total": 7}
    assert dev_eval.seed_stability(dev_eval.MethodRun("M2_probe_residual", dev_eval.ACTIVATION, axis_directive("probe_residual")),
                                   runs, results, GAP, 0.5) is None


def winner(jaccard, share):
    return {"best_jaccard": jaccard, "share_of_failures": share}


def test_claim_b_needs_the_margin_over_baseline_and_catch_all_a_clear_interval_and_a_bounded_axis():
    clear = dev_eval.claim_b(winner(0.8, 0.4), 0.6, 0.3, (0.05, 0.3), None)
    assert clear["holds"] and clear["stable"] is None
    assert not dev_eval.claim_b(winner(0.8, 0.4), 0.7, 0.3, (0.05, 0.3), None)["margin"]
    assert not dev_eval.claim_b(winner(0.8, 0.4), 0.3, 0.7, (0.05, 0.3), None)["margin"]
    assert not dev_eval.claim_b(winner(0.8, 0.4), 0.6, 0.3, (-0.01, 0.3), None)["margin"]
    assert not dev_eval.claim_b(winner(0.8, 0.6), 0.6, 0.3, (0.05, 0.3), None)["holds"]
    unstable = dev_eval.claim_b(winner(0.8, 0.4), 0.6, 0.3, (0.05, 0.3), {"seeds_beating": 3, "seeds_total": 6})
    assert unstable["margin"] and unstable["stable"] is False and not unstable["holds"]


def test_stale_frames_mark_only_repeats_of_the_previous_frame():
    means = np.array([[1.0, 0.0], [1.0, 0.0], [0.0, 1.0], [0.0, 1.0005], [0.0, 1.0]])
    assert dev_eval.stale_frames(means).tolist() == [0.0, 1.0, 0.0, 1.0, 1.0]
