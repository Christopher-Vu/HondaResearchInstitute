"""The scoring path end to end on a synthetic pool: residual shards, emitted directives, a key, one report."""
import json
import shutil
import sys
import zlib
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

torch = pytest.importorskip("torch")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from discovery import emit_directives, probe_residual, residualize, sae  # noqa: E402
from discovery.probe_residual import STATES  # noqa: E402
from harness import scoring_run, seal  # noqa: E402
from harness.schema import ACTION_RESIDUAL, NON_RESIDUALIZED, AxisCard, Directive, SchemaError  # noqa: E402

HIDDEN, LAYERS, LAYER, SPIKE = 24, 2, 1, 12.0
STEPS = np.arange(0, 300, 5)
PAIRS = 32
CONTROL, TURN, MERGE = "C_control", "I_turn", "I_merge"
UNIT = {CONTROL: 0, TURN: 1, MERGE: 2}
LABEL = "DEV DRY RUN, NOT A VERDICT: test"
DICTIONARY = "L1_exact"
SECRET = "ab" * 32


def spec_list():
    """A control gap's spike comes through vision; an interactional gap's sits in the decision only."""
    specs = []
    for gap in (CONTROL, TURN, MERGE):
        for i in range(PAIRS):
            specs.append((f"{gap}-s{i}", f"{gap}{i}", False, gap, "slice"))
            specs.append((f"{gap}-n{i}", f"{gap}{i}", i >= 4, gap, "neighbourhood"))
    specs += [(f"bg{i}", f"bg{i // 2}", False, None, None) for i in range(10)]
    specs += [(f"ok{i}", f"ok{i // 3}", True, None, None) for i in range(60)]
    return specs


def frames(rng, gap, arm):
    visual = rng.normal(size=(len(STEPS), HIDDEN))
    queries = rng.normal(size=(len(STEPS), LAYERS, HIDDEN))
    queries[:, LAYER] = visual + rng.normal(scale=0.05, size=(len(STEPS), HIDDEN))
    if arm == "slice" and gap == CONTROL:
        visual[:, UNIT[gap]] += SPIKE
        queries[:, LAYER, UNIT[gap]] += SPIKE
    elif arm == "slice":
        queries[:, LAYER, UNIT[gap]] += SPIKE
    return queries, visual


def write_shard(directory, route_id, base_id, success, gap, arm):
    rng = np.random.default_rng(zlib.crc32(route_id.encode()))
    queries, visual = frames(rng, gap, arm)
    states = {name: rng.uniform(1, 50, len(STEPS)).astype(np.float32) for name in (*STATES, "ego_speed")}
    np.savez(directory / f"{route_id}.npz", step=STEPS.astype(np.int32), driving_queries=queries.astype(np.float32),
             driving_queries_episode_mean=queries.mean(axis=0).astype(np.float32),
             vision_bridge=visual.astype(np.float32), vision_bridge_episode_mean=visual.mean(axis=0).astype(np.float32),
             **states)
    (directory / f"{route_id}.json").write_text(json.dumps({
        "route_id": route_id, "base_id": base_id, "scenario": "S%d" % (zlib.crc32(base_id.encode()) % 3), "town": "T",
        "success": success, "infractions": {} if success else {"collisions_vehicle": 1},
        "first_collision_step": None if success else 250, "practice_gaps": [gap] if arm == "slice" else [],
        "role": arm}))


def exact_sae(directory):
    """A signed-pair SAE that reconstructs its input; each unit's positive latent fires only above 0.7."""
    identity = torch.eye(HIDDEN)
    model = sae.TopKSae(HIDDEN, 2 * HIDDEN, 2 * HIDDEN, torch.zeros(HIDDEN))
    model.pre_bias.data[:3] = 0.7
    model.encoder.data = torch.cat([identity, -identity])
    model.decoder.data = torch.cat([identity, -identity], dim=1)
    directory.mkdir(parents=True)
    torch.save({"config": {"layer": LAYER, "k": 2 * HIDDEN, "seed": 0}, "state": model.state_dict()}, directory / "sae.pt")


def key_document():
    def spec(gap, tier):
        return {"gap_id": gap, "tier": tier, "predicate": [{"field": "arm", "op": "==", "value": f"{gap}/slice"}],
                "neighbourhood_predicate": [{"field": "arm", "op": "==", "value": f"{gap}/neighbourhood"}]}
    return {"version": 1, "gaps": [spec(CONTROL, "T0_control"), spec(TURN, "T2_interactional"),
                                   spec(MERGE, "T2_interactional")]}


def run_command(monkeypatch, module, arguments):
    monkeypatch.setattr(sys, "argv", ["command", *map(str, arguments)])
    module.main()


def score_arguments(root, output, *extra, directives=None):
    return ["--directives", *(directives or [root / "directives/non_residualized", root / "directives/action_residual"]),
            "--key", root / "key.json", "--salt", root / "salt", "--commitment", root / "commitment.txt",
            "--manifests", root / "manifest.json", "--routes", root / "routes.jsonl", "--efficacy-rule", "prd_9_1",
            "--label", LABEL, "--output", output, "--replicates", "20", *extra]


@pytest.fixture(scope="module")
def pool(tmp_path_factory):
    root = tmp_path_factory.mktemp("pool")
    shards = root / "shards"
    shards.mkdir()
    manifest, rows = [], []
    for route_id, base_id, success, gap, arm in spec_list():
        write_shard(shards, route_id, base_id, success, gap, arm)
        manifest.append({"id": route_id, "base_id": base_id, "scenario": "S%d" % (zlib.crc32(base_id.encode()) % 3),
                         "town": "T", "weather": {}, "arm": f"{gap}/{arm}"})
        rows.append({"id": route_id, "success": success})
    (root / "manifest.json").write_text(json.dumps(manifest))
    (root / "routes.jsonl").write_text("\n".join(map(json.dumps, rows)) + "\n")
    (root / "key.json").write_text(json.dumps(key_document()))
    (root / "salt").write_text(SECRET)
    seal.write_commitment(root / "key.json", root / "salt", root / "commitment.txt")
    exact_sae(root / "dictionaries" / DICTIONARY)
    with pytest.MonkeyPatch.context() as patch:
        run_command(patch, residualize, [shards, "--layer", LAYER, "--model", root / "fit.npz", "--output", root / "residual"])
        run_command(patch, emit_directives, [shards, "--layer", LAYER, "--sae", root / "dictionaries" / DICTIONARY,
                                             "--manifests", root / "manifest.json", "--primary-dictionary", DICTIONARY,
                                             "--output", root / "directives/non_residualized"])
        run_command(patch, emit_directives, [root / "residual", "--layer", LAYER, "--sae", root / "dictionaries" / DICTIONARY,
                                             "--output", root / "directives/action_residual"])
        run_command(patch, scoring_run, score_arguments(root, root / "report.json", "--dictionary", DICTIONARY))
    return root


def report_of(pool):
    return json.loads((pool / "report.json").read_text())


def by(report, family, variant):
    return next(row for row in report["methods"].values() if row["family"] == family and row["preprocessing"] == variant)


def test_both_variants_emit_and_only_the_raw_pool_runs_activation_free_baselines(pool):
    raw = {path.name for path in (pool / "directives/non_residualized").iterdir()}
    residual = {path.name for path in (pool / "directives/action_residual").iterdir()}
    assert {"B2_taxonomy@none@non_residualized.json", "B1_random@none@non_residualized.json",
            f"M1_raw@{DICTIONARY}@non_residualized.json", "M2_probe_residual@none@non_residualized.json"} <= raw
    assert residual == {f"M1_raw@{DICTIONARY}@action_residual.json", f"M1_capped@{DICTIONARY}@action_residual.json",
                        f"B7_pool@{DICTIONARY}@action_residual.json", "M2_probe_residual@none@action_residual.json"}


def test_residualizing_loses_the_perceptual_gap_and_keeps_the_decision_gaps(pool):
    report = report_of(pool)
    raw, residual = by(report, "M1_raw", "non_residualized"), by(report, "M1_raw", "action_residual")
    assert all(raw["best_jaccard"][gap] > 0.9 for gap in UNIT)
    assert residual["best_jaccard"][TURN] > 0.9 and residual["best_jaccard"][MERGE] > 0.9
    assert residual["best_jaccard"][CONTROL] < 0.5


def test_a_residualized_directive_never_recovers_the_control_for_validity(pool):
    report = report_of(pool)
    assert all("action_residual" not in label for label in report["condition_1"]["t0_recovered_by"])
    assert report["condition_1"]["by_rule"]["prd_9_1"]["valid"] is True


def test_relabelling_the_same_axes_as_residualized_takes_the_recovery_away(pool):
    """The axes recover the control gap; only the variant differs, and only the variant decides."""
    emitted = scoring_run.load_emitted([pool / "directives/non_residualized"])
    gaps = seal.gaps_from_key(key_document()["gaps"], *scoring_run.load_pool([pool / "manifest.json"], [pool / "routes.jsonl"]))
    raw = [item for item in emitted if item.family == "M1_raw"]
    reports = {item.label: scoring_run.score(item.directive, gaps) for item in raw}
    assert scoring_run.condition_1(raw, reports, gaps)["by_rule"]["prd_9_1"]["valid"] is True
    for item in raw:
        reports[item.label].preprocessing = ACTION_RESIDUAL
    relabelled = scoring_run.condition_1(raw, reports, gaps)
    assert relabelled["by_rule"]["prd_9_1"]["valid"] is False and "non-residualized" in relabelled["by_rule"]["prd_9_1"]["reason"]


def test_both_efficacy_rules_are_read_from_this_pool(pool):
    verdicts, gaps = report_of(pool)["condition_1"]["by_rule"], report_of(pool)["gaps"]
    assert gaps[TURN]["efficacy"]["n_in"] == PAIRS and gaps[TURN]["efficacy"]["c23_paired"]["pairs"] == PAIRS
    assert verdicts["prd_9_1"]["t2_reconfirming"] == sorted([TURN, MERGE])
    assert verdicts["c23"]["valid"] is False and verdicts["c23"]["t2_reconfirming"] == []


def test_condition_two_says_not_evaluated_while_baselines_are_missing(pool):
    second = report_of(pool)["condition_2"]
    assert second["evaluated"] is False and "B4_enumerated" in second["missing_baselines"]
    assert "B2_taxonomy" not in second["missing_baselines"] and "B7_actstats" not in second["missing_baselines"]
    assert second["arithmetic"]["replicates"] == 20 and second["dictionary"] == DICTIONARY


def test_the_report_holds_the_label_and_no_predicate_or_secret(pool):
    text = (pool / "report.json").read_text()
    assert report_of(pool)["label"] == LABEL
    assert "predicate" not in text and SECRET not in text and f"{TURN}/slice" not in text


def test_a_gaps_lost_routes_are_counted_and_never_named(pool, tmp_path):
    """A report goes out before the key is revealed, so it must not list which routes a gap holds."""
    routes = tmp_path / "routes.jsonl"
    kept = [line for line in (pool / "routes.jsonl").read_text().splitlines() if f"{TURN}-s0" not in line]
    routes.write_text("\n".join(kept) + "\n")
    manifest, failed = scoring_run.load_pool([pool / "manifest.json"], [routes])
    gaps = seal.gaps_from_key(key_document()["gaps"], manifest, failed)
    row = scoring_run.gap_row(next(gap for gap in gaps if gap.gap_id == TURN), sum(failed.values()))
    assert row["efficacy"]["routes_without_outcome"] == 1 and f"{TURN}-s0" not in json.dumps(row)


def test_best_and_median_cover_the_dictionaries(pool):
    spread = report_of(pool)["spread"]["M1_raw@action_residual"][TURN]
    assert spread["dictionaries"] == 1 and spread["best"] == spread["median"]


def test_a_report_is_written_once(pool):
    with pytest.MonkeyPatch.context() as patch, pytest.raises(SystemExit):
        run_command(patch, scoring_run, score_arguments(pool, pool / "report.json"))


def test_a_changed_key_stops_the_run_before_any_score(pool, tmp_path):
    changed = tmp_path / "pool"
    shutil.copytree(pool / "directives", changed / "directives")
    for name in ("manifest.json", "routes.jsonl", "salt", "commitment.txt"):
        shutil.copy(pool / name, changed / name)
    (changed / "key.json").write_text(json.dumps(key_document(), indent=2))
    with pytest.MonkeyPatch.context() as patch, pytest.raises(SystemExit, match="does not match"):
        run_command(patch, scoring_run, score_arguments(changed, tmp_path / "out.json"))
    assert not (tmp_path / "out.json").exists()


def copied_directive(pool, tmp_path, change):
    target = tmp_path / "directives"
    target.mkdir()
    raw = json.loads((pool / f"directives/non_residualized/M1_raw@{DICTIONARY}@non_residualized.json").read_text())
    change(raw["directive"])
    (target / "only.json").write_text(json.dumps(raw))
    return target


def test_a_directive_off_the_budget_or_without_one_is_refused(pool, tmp_path):
    for name, change in (("five", lambda d: d.update(budget_m=5)), ("none", lambda d: d.pop("budget_m"))):
        directory = tmp_path / name
        directory.mkdir()
        with pytest.raises(SchemaError, match="budget_m"):
            scoring_run.load_emitted([copied_directive(pool, directory, change)])


def test_a_directive_claiming_an_unscored_rollout_is_refused(pool, tmp_path):
    emitted = scoring_run.load_emitted([copied_directive(pool, tmp_path, lambda d: None)])
    manifest, failed = scoring_run.load_pool([pool / "manifest.json"], [pool / "routes.jsonl"])
    claimed = next(iter(emitted[0].directive.axes[0].rollouts))
    failed.pop(claimed)
    with pytest.raises(ValueError, match="no outcome"):
        scoring_run.scoring_report(emitted, key_document()["gaps"], manifest, failed, None, 5)


def test_scored_routes_outside_the_manifests_are_refused(pool, tmp_path):
    routes = tmp_path / "routes.jsonl"
    routes.write_text('{"id": "stranger", "success": true}\n')
    with pytest.raises(ValueError, match="outside the manifests"):
        scoring_run.load_pool([pool / "manifest.json"], [routes])


def test_emission_never_reads_practice_gaps_or_role(pool, tmp_path):
    blind = tmp_path / "shards"
    shutil.copytree(pool / "residual", blind)
    for sidecar in blind.glob("*.json"):
        meta = json.loads(sidecar.read_text())
        meta.pop("practice_gaps"), meta.pop("role")
        sidecar.write_text(json.dumps(meta))
    with pytest.MonkeyPatch.context() as patch:
        run_command(patch, emit_directives, [blind, "--layer", LAYER, "--sae", pool / "dictionaries" / DICTIONARY,
                                             "--output", tmp_path / "out"])
    for path in (tmp_path / "out").iterdir():
        assert json.loads(path.read_text())["directive"] == json.loads(
            (pool / "directives/action_residual" / path.name).read_text())["directive"]


def test_shards_mixing_variants_cannot_emit_one_directive(pool, tmp_path):
    with pytest.MonkeyPatch.context() as patch, pytest.raises(ValueError, match="mix"):
        mixed = tmp_path / "mixed"
        mixed.mkdir()
        for name in ("ok0", "bg0"):
            shutil.copy(pool / "shards" / f"{name}.json", mixed / f"{name}.json")
            shutil.copy(pool / "shards" / f"{name}.npz", mixed / f"{name}.npz")
        for suffix in (".json", ".npz"):
            shutil.copy(pool / "residual" / f"ok1{suffix}", mixed / f"ok1{suffix}")
        run_command(patch, emit_directives, [mixed, "--layer", LAYER, "--output", tmp_path / "out"])


def test_probe_residual_reads_a_residual_shard_at_the_original_layer(pool):
    rollout = probe_residual.load_shard(pool / "residual/I_turn-s0.json", "driving_queries", LAYER)
    assert rollout.failed and rollout.activations.shape == (len(STEPS), HIDDEN)


def scored_inputs(pool):
    manifest, failed = scoring_run.load_pool([pool / "manifest.json"], [pool / "routes.jsonl"])
    base_of = {str(entry["id"]): str(entry["base_id"]) for entry in manifest}
    return seal.gaps_from_key(key_document()["gaps"], manifest, failed), base_of


def emitted_of(pool):
    return scoring_run.load_emitted([pool / "directives/non_residualized", pool / "directives/action_residual"])


def test_a_baseline_recovering_the_control_does_not_validate_the_harness(pool):
    """The same axes count for validity under an activation label and not under a baseline label."""
    raw = [item for item in emitted_of(pool) if item.family == "M1_raw" and item.directive.preprocessing == NON_RESIDUALIZED]
    gaps, _ = scored_inputs(pool)
    reports = {item.label: scoring_run.score(item.directive, gaps) for item in raw}
    as_baselines = [replace(item, kind=scoring_run.BASELINE) for item in raw]
    first = scoring_run.condition_1(as_baselines, reports, gaps)
    assert first["by_rule"]["prd_9_1"]["valid"] is False and "T0" in first["by_rule"]["prd_9_1"]["reason"]
    assert first["t0_recovered_by"] == {item.label: [CONTROL] for item in raw}


def test_a_dictionary_name_matching_nothing_stops_condition_two(pool):
    gaps, base_of = scored_inputs(pool)
    with pytest.raises(ValueError, match="L1_mistyped"):
        scoring_run.condition_2(emitted_of(pool), gaps, base_of, "L1_mistyped", 5)


def test_a_primary_dictionary_matching_nothing_stops_the_random_draw():
    with pytest.raises(ValueError, match="L1_mistyped"):
        emit_directives.random_run([], ["a", "b"], "L1_mistyped")
    assert emit_directives.random_run([], ["a", "b"], None).family == "B1_random"


def test_a_dictionary_with_counts_false_stays_out_of_condition_two(pool):
    gaps, base_of = scored_inputs(pool)
    emitted = emitted_of(pool)
    label = f"M1_raw@{DICTIONARY}@action_residual"
    assert label in scoring_run.condition_2(emitted, gaps, base_of, DICTIONARY, 5)["activation"]
    uncounted = [replace(item, counts=False) if item.label == label else item for item in emitted]
    assert label not in scoring_run.condition_2(uncounted, gaps, base_of, DICTIONARY, 5)["activation"]


def test_spread_reports_an_uncounted_dictionary_under_its_own_key(pool):
    gaps, _ = scored_inputs(pool)
    real = [gap for gap in gaps if not gap.is_decoy]
    emitted = emitted_of(pool)
    methods = {item.label: scoring_run.method_row(item, scoring_run.score(item.directive, gaps), real) for item in emitted}
    label = f"M1_raw@{DICTIONARY}@action_residual"
    found = scoring_run.spread([replace(item, counts=False) if item.label == label else item for item in emitted],
                               methods, real)
    assert "M1_raw@action_residual" not in found
    row = found["uncounted"]["M1_raw@action_residual"][TURN]
    assert row["dictionaries"] == 1 and row["best"] == methods[label]["best_jaccard"][TURN]


def test_the_report_carries_c34s_sentence_beside_spread(pool):
    assert report_of(pool)["spread_reading"] == "the best axis is chosen using the key"


def test_an_axis_keeps_its_variant_through_a_file():
    axis = AxisCard.from_dict({"axis_id": "a", "name": "n", "description": "d", "rank": 1, "score": 1.0,
                               "provenance": {"method": "sae", "preprocessing": [ACTION_RESIDUAL]}})
    written = Directive("sae", [axis], preprocessing=ACTION_RESIDUAL).to_dict()
    assert Directive.from_dict(written).axes[0].preprocessing == [ACTION_RESIDUAL]
    with pytest.raises(SchemaError, match="another preprocessing variant"):
        Directive.from_dict({**written, "preprocessing": NON_RESIDUALIZED})


def dry_run_pool(pool, root):
    root.mkdir()
    shutil.copytree(pool / "directives", root / "directives")
    for name in ("manifest.json", "routes.jsonl", "salt"):
        shutil.copy(pool / name, root / name)
    (root / "key.json").write_text(json.dumps({**key_document(), "dry_run": True}))
    seal.write_commitment(root / "key.json", root / "salt", root / "commitment.txt")
    return root


def scoring_arguments_with_label(root, output, label):
    arguments = score_arguments(root, output)
    arguments[arguments.index(LABEL)] = label
    return arguments


def test_a_dry_run_key_refuses_a_label_that_hides_it(pool, tmp_path):
    root = dry_run_pool(pool, tmp_path / "pool")
    with pytest.MonkeyPatch.context() as patch, pytest.raises(SystemExit):
        run_command(patch, scoring_run, scoring_arguments_with_label(root, tmp_path / "out.json", "score-v1"))
    assert not (tmp_path / "out.json").exists()


def test_a_dry_run_key_stamps_the_top_of_the_report_and_a_real_key_does_not(pool, tmp_path):
    root = dry_run_pool(pool, tmp_path / "pool")
    with pytest.MonkeyPatch.context() as patch:
        run_command(patch, scoring_run, score_arguments(root, tmp_path / "out.json"))
    written = json.loads((tmp_path / "out.json").read_text())
    assert next(iter(written)) == "dry_run" and written["dry_run"] is True
    assert report_of(pool)["dry_run"] is False
