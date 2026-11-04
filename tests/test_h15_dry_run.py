"""H15's throwaway key and bug check: the key is public and verbatim, and the check catches a tampered number."""
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "docs/research/experiments/h15-scoring-dry-run"
sys.path.insert(0, str(ROOT / "src"))

from discovery.residualize import ActionResidual, fit, write_shard  # noqa: E402
from harness import scoring_run, seal  # noqa: E402
from test_residualize import HIDDEN, LAYER, write_rollout  # noqa: E402


def load(name):
    spec = importlib.util.spec_from_file_location(f"h15_{name}", EXPERIMENT / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


build_key, check = load("build_key"), load("check")
POOL = ("step5-background-wave3", "step5-confirm-p4", "step5-confirm-p7", "step5-pilot-p19-main")


@pytest.fixture(scope="module")
def real_gaps(tmp_path_factory):
    """The key path on the repo's real manifests and outcomes, which needs no shard and no simulator."""
    directory = tmp_path_factory.mktemp("key")
    build_key.write_key("as-labelled", directory)
    manifest, failed = scoring_run.load_pool([ROOT / f"configs/rollout/{name}.manifest.json" for name in POOL],
                                             [ROOT / f"results/savio/{name}/routes.jsonl" for name in POOL])
    gaps = seal.gaps_from_key(seal.load_key(directory / "key.json"), manifest, failed)
    report = {"pool": {"rollouts": len(failed), "failures": sum(failed.values())},
              "gaps": {gap.gap_id: scoring_run.gap_row(gap, sum(failed.values())) for gap in gaps}}
    return json.loads(json.dumps(report))


def stored_efficacy():
    return {gap_id: json.loads((ROOT / path).read_text()) for gap_id, path in check.STORED_EFFICACY.items()}


def h12():
    return json.loads((ROOT / check.H12_PLAIN).read_text())


def test_every_predicate_is_copied_verbatim_from_the_practice_files():
    known = {gap["gap_id"]: gap for name in build_key.PRACTICE_FILES
             for gap in yaml.safe_load((ROOT / name).read_text())["gaps"]}
    for name in build_key.KEYS:
        document = build_key.key_document(name)
        assert document["dry_run"] is True and "NOT A VERDICT" in document["label"]
        for gap in document["gaps"]:
            assert gap["predicate"] == known[gap["gap_id"]]["predicate"] and gap["tier"] == known[gap["gap_id"]]["tier"]
            assert gap["neighbourhood_predicate"] == [{"field": "neighbourhood_of", "op": "==", "value": [gap["gap_id"]]}]


def test_a_throwaway_key_is_refused_under_gaps_or_src():
    for place in ("gaps/sealed/x", "gaps/x", "src/harness/x"):
        with pytest.raises(ValueError, match="throwaway"):
            build_key.refuse_real_locations(ROOT / place)


def test_the_commitment_stays_beside_the_key(tmp_path):
    before = (ROOT / "src/harness/KEY_COMMITMENT.txt").exists()
    build_key.write_key("branch", tmp_path)
    assert seal.verify(tmp_path / "key.json", tmp_path / "salt", tmp_path / "commitment.txt")
    assert (ROOT / "src/harness/KEY_COMMITMENT.txt").exists() == before


def test_on_real_outcomes_the_key_path_reproduces_h12s_pool_and_the_stored_pilots(real_gaps):
    assert check.pool_counts(real_gaps, h12()) == []
    assert check.efficacy_matches_stored(real_gaps, stored_efficacy()) == []


def test_the_check_catches_a_changed_efficacy_number(real_gaps):
    changed = json.loads(json.dumps(real_gaps))
    changed["gaps"]["P19_wide_invading_turn"]["efficacy"]["c23_paired"]["pairs"] = 60
    assert any("pairs" in problem for problem in check.efficacy_matches_stored(changed, stored_efficacy()))


def test_the_check_catches_a_changed_key_size(real_gaps):
    changed = json.loads(json.dumps(real_gaps))
    changed["gaps"]["P4_camera_occlusion"]["key_size"] = 45
    assert check.pool_counts(changed, h12())


def method_row(family, dictionary, jaccard, kind="activation", variant="non_residualized"):
    return {"family": family, "dictionary": dictionary, "kind": kind, "preprocessing": variant,
            "best_jaccard": {"P19_wide_invading_turn": jaccard},
            "score": {"matches": [{"gap_id": "P19_wide_invading_turn"}]}}


def test_the_check_compares_jaccards_exactly_without_a_dictionary_and_loosely_with_one():
    stored = h12()
    plain = stored["methods"]["B2_taxonomy"]["gaps"]["P19_wide_invading_turn"]["best_jaccard"]
    assert check.jaccards_match_h12({"methods": {"b2": method_row("B2_taxonomy", None, plain)}}, stored) == []
    assert check.jaccards_match_h12({"methods": {"b2": method_row("B2_taxonomy", None, plain + 1e-6)}}, stored)
    sae = stored["methods"]["M1_raw@results/savio/h12/sae/L10_k32_s0"]["gaps"]["P19_wide_invading_turn"]["best_jaccard"]
    row = method_row("M1_raw", "L10_k32_s0", sae + 0.005)
    assert check.jaccards_match_h12({"methods": {"m": row}}, stored) == []
    row = method_row("M1_raw", "L10_k32_s0", sae + 0.05)
    assert check.jaccards_match_h12({"methods": {"m": row}}, stored)
    residual = method_row("M1_raw", "L10_k32_s0", 0.0, variant="action_residual")
    assert check.jaccards_match_h12({"methods": {"m": residual}}, stored) == []


def test_the_check_notices_an_h12_row_nobody_scored():
    stored = h12()
    assert check.h12_rows_reached({"methods": {}}, stored)
    everything = {label: method_row(row["family"], Path(row["sae"]).name if row["sae"] else None, 0.0)
                  for label, row in stored["methods"].items()}
    assert check.h12_rows_reached({"methods": everything}, stored) == []


def delta_report(delta):
    return {"gaps": {"P19_wide_invading_turn": {"tier": "T2_interactional", "decoy": False}},
            "methods": {"a": method_row("M1_raw", None, 0.7), "b": method_row("B2", None, 0.8)},
            "condition_2": {"activation": ["a"], "baselines": ["b"], "arithmetic": {"delta": delta}}}


def test_the_check_recomputes_delta_from_the_table():
    assert check.delta_agrees(delta_report(0.7 - 0.8)) == []
    assert check.delta_agrees(delta_report(0.1))


def test_the_check_refuses_validity_resting_on_a_residualized_method():
    report = {"methods": {"r": method_row("M1_raw", None, 0.9, variant="action_residual")},
              "condition_1": {"t0_recovered_by": {"r": ["P4"]}, "by_rule": {"prd_9_1": {"valid": True}}}}
    assert check.only_non_residualized_validates(report)
    report["methods"]["r"]["preprocessing"] = "non_residualized"
    assert check.only_non_residualized_validates(report) == []


def test_the_check_wants_the_label_and_no_key_words():
    assert check.report_is_labelled_and_clean('{"label": "DEV DRY RUN, NOT A VERDICT"}') == []
    assert check.report_is_labelled_and_clean('{"label": "score-v1"}')
    assert check.report_is_labelled_and_clean('DEV DRY RUN predicate')


def test_the_decoy_path_needs_a_decoy_a_verdict_and_no_match():
    decoy = "P7_camera_freeze"
    good = {"gaps": {decoy: {"decoy": True, "efficacy": {"c31_decoy": {"passes": False}}}},
            "methods": {"m": {"score": {"matches": [{"gap_id": "P19"}]}}}}
    assert check.decoy_path_ran(good) == []
    good["methods"]["m"]["score"]["matches"].append({"gap_id": decoy})
    assert check.decoy_path_ran(good)
    assert check.decoy_path_ran({"gaps": {}, "methods": {}})


def test_write_key_refuses_a_real_location_before_writing(tmp_path):
    output = tmp_path / "gaps/x"
    with pytest.raises(ValueError, match="throwaway"):
        build_key.write_key("branch", output, repo=tmp_path)
    assert not output.exists()


@pytest.mark.parametrize("name, value", [("rollouts", 535), ("failures", 228)])
def test_the_check_catches_a_changed_pool_count(name, value):
    stored = {"corpus": {"rollouts": 536, "failures": 229, "key": {}}}
    same = {"pool": {"rollouts": 536, "failures": 229}, "gaps": {}}
    assert check.pool_counts(same, stored) == []
    problems = check.pool_counts({**same, "pool": {**same["pool"], name: value}}, stored)
    assert len(problems) == 1 and name in problems[0]


def test_the_check_catches_a_changed_fisher_number():
    stored = {"G": {"prd_9_1": {"n_in": 53}, "c23_paired": {"pairs": 46}}}
    same = {"gaps": {"G": {"efficacy": {"n_in": 53, "c23_paired": {"pairs": 46}}}}}
    assert check.efficacy_matches_stored(same, stored) == []
    changed = {"gaps": {"G": {"efficacy": {"n_in": 52, "c23_paired": {"pairs": 46}}}}}
    assert any("prd_9_1 n_in" in problem for problem in check.efficacy_matches_stored(changed, stored))


@pytest.fixture
def residual_pool(tmp_path):
    """Sources, a fit on them, and their residual shards; `check.residual_shards_sound` finds nothing wrong yet.
    The noise is not tiny, because ridge's shrinkage alone left R2 0.33 when the residual was almost nothing but noise
    at scale 0.01."""
    source, output = tmp_path / "shards", tmp_path / "residual"
    source.mkdir()
    output.mkdir()
    rng = np.random.default_rng(5)
    for i in range(12):
        write_rollout(source, f"ok{i}", rng, noise=0.5)
    write_rollout(source, "bad", rng, success=False, decision=5.0, noise=0.5)
    write_rollout(source, "crash", rng, success=None, noise=0.5)
    model = fit([source], LAYER)
    for sidecar in source.glob("*.json"):
        write_shard(sidecar, model, output)
    return source, output, model


def rewrite_stored(output, change):
    with np.load(output / "ok0.npz") as archive:
        arrays = {name: archive[name] for name in archive.files}
    change(arrays["driving_queries"])
    np.savez(output / "ok0.npz", **arrays)


def findings(residual_pool):
    source, output, model = residual_pool
    return " ".join(check.residual_shards_sound(output, [source], model))


def test_the_residual_check_passes_sound_shards(residual_pool):
    assert findings(residual_pool) == ""


def test_the_residual_check_catches_a_changed_residual(residual_pool):
    def shift(stored):
        stored[:, LAYER] += 1.0
    rewrite_stored(residual_pool[1], shift)
    assert "stored residual differs" in findings(residual_pool)


def test_the_residual_check_catches_values_at_another_layer(residual_pool):
    def fill(stored):
        stored[:, 0] = 0.0
    rewrite_stored(residual_pool[1], fill)
    assert "a layer other than" in findings(residual_pool)


def test_the_residual_check_catches_a_missing_shard(residual_pool):
    (residual_pool[1] / "ok0.json").unlink()
    assert "ok0 has an outcome and no residual shard" in findings(residual_pool)


@pytest.mark.parametrize("change", [{"success": False}, {"preprocessing": "non_residualized"}])
def test_the_residual_check_catches_a_changed_sidecar(residual_pool, change):
    path = residual_pool[1] / "ok0.json"
    path.write_text(json.dumps({**json.loads(path.read_text()), **change}))
    assert "untagged or its outcome differs" in findings(residual_pool)


def test_the_residual_check_catches_vision_left_in_the_residual(residual_pool):
    """A fit that removes nothing still matches its own arithmetic, so only the refit can notice."""
    source, _, _ = residual_pool
    idle = ActionResidual(LAYER, np.zeros(HIDDEN), np.ones(HIDDEN), np.zeros((HIDDEN, HIDDEN)), np.zeros(HIDDEN), 1.0, 0, 0.0)
    output = source.parent / "idle"
    output.mkdir()
    for sidecar in source.glob("*.json"):
        write_shard(sidecar, idle, output)
    assert "vision still predicts" in findings((source, output, idle))


def outcome_files(tmp_path, scored, listed):
    routes = tmp_path / "routes.jsonl"
    routes.write_text("".join(json.dumps({"id": route, "success": success}) + "\n" for route, success in scored.items()))
    shards = tmp_path / "shards"
    shards.mkdir()
    for route, success in listed.items():
        (shards / f"{route}.json").write_text(json.dumps({"route_id": route, "success": success}))
    return [routes], [shards]


def test_the_outcome_check_skips_rollouts_with_no_outcome_on_either_side(tmp_path):
    routes, shards = outcome_files(tmp_path, {"a": True, "b": False, "c": None}, {"a": True, "b": False, "d": None})
    assert check.outcomes_agree(routes, shards) == []


@pytest.mark.parametrize("scored, listed", [({"a": True}, {"a": False}), ({"a": True, "b": True}, {"a": True}),
                                            ({"a": True}, {"a": True, "b": True})])
def test_the_outcome_check_catches_a_disagreement_or_a_missing_route(tmp_path, scored, listed):
    routes, shards = outcome_files(tmp_path, scored, listed)
    assert check.outcomes_agree(routes, shards)
