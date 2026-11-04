"""Practice-gap efficacy: PRD 9.1's unpaired Fisher rule and CONFLICTS.md C23's paired McNemar rule."""
import json
from pathlib import Path

import pytest

from src.harness import efficacy

GAP = "G"


def pilot(outcomes):
    """outcomes: list of (slice failed, neighbourhood failed) per base route; None leaves a route unscored."""
    manifest, rows = [], []
    for index, pair in enumerate(outcomes):
        for role, failed in zip(("slice", "nbhd"), pair):
            route_id = f"{index}{role}"
            manifest.append({"id": route_id, "base_id": str(index), "practice_gaps": [GAP] if role == "slice" else [],
                             "neighbourhood_of": [GAP] if role == "nbhd" else []})
            rows.append({"id": route_id, "success": None if failed is None else not failed})
    return manifest, rows


def test_a_strong_paired_gap_passes_both_rules():
    manifest, rows = pilot([(True, False)] * 30 + [(False, False)] * 30)
    report = efficacy.efficacy(manifest, rows, GAP)
    assert report["c23_paired"]["passes"] and report["prd_9_1"]["passes"]
    assert report["c23_paired"]["slice_only_failed"] == 30


def test_pairing_counts_only_discordant_routes():
    concordant = [(True, True)] * 20 + [(False, False)] * 28
    manifest, rows = pilot(concordant + [(True, False)] * 10 + [(False, True)] * 2)
    report = efficacy.efficacy(manifest, rows, GAP)["c23_paired"]
    assert (report["slice_only_failed"], report["neighbourhood_only_failed"]) == (10, 2)
    assert report["mcnemar_p"] > 0.01 and not report["passes"]


def test_fewer_than_sixty_pairs_fail_c23_even_with_a_large_effect():
    manifest, rows = pilot([(True, False)] * 40)
    assert not efficacy.efficacy(manifest, rows, GAP)["c23_paired"]["passes"]


def test_a_base_route_missing_either_outcome_is_not_a_pair():
    manifest, rows = pilot([(True, None), (None, False), (True, False)])
    report = efficacy.efficacy(manifest, rows, GAP)
    assert report["c23_paired"]["pairs"] == 1
    assert report["routes_without_outcome"] == ["0nbhd", "1slice"]
    assert report["prd_9_1"]["n_in"] == 2 and report["prd_9_1"]["n_neighbourhood"] == 2


def several_pairs_per_base(bases, pairs_per_base, failed_slice=True):
    """Each base carries several slice and neighbourhood routes; the slice fails and its twin does not."""
    manifest, rows = [], []
    for base in range(bases):
        for n in range(pairs_per_base):
            manifest += [{"id": f"{base}-{n}s", "base_id": str(base), "practice_gaps": [GAP], "neighbourhood_of": []},
                         {"id": f"{base}-{n}n", "base_id": str(base), "practice_gaps": [], "neighbourhood_of": [GAP]}]
            rows += [{"id": f"{base}-{n}s", "success": not failed_slice}, {"id": f"{base}-{n}n", "success": True}]
    return manifest, rows


def test_sixty_pairs_on_thirty_bases_score_as_sixty_pairs_and_pass():
    """PREREGISTRATION.md code gap 4: a second pair on a base used to overwrite the first, so this scored 30 and failed."""
    report = efficacy.efficacy(*several_pairs_per_base(30, 2), GAP)["c23_paired"]
    assert (report["pairs"], report["base_routes"]) == (60, 30)
    assert report["passes"]


def test_sixty_pairs_on_too_few_bases_still_fail_the_base_route_floor():
    report = efficacy.efficacy(*several_pairs_per_base(20, 3), GAP)["c23_paired"]
    assert (report["pairs"], report["base_routes"]) == (60, 20)
    assert not report["passes"]


def test_a_lost_route_leaves_its_own_twin_unpaired_and_does_not_shift_the_next_pair():
    manifest, rows = several_pairs_per_base(1, 2)
    rows = [row for row in rows if row["id"] != "0-0s"]
    rows = [{**row, "success": False} if row["id"] == "0-0n" else row for row in rows]
    report = efficacy.efficacy(manifest, rows, GAP)["c23_paired"]
    assert report["pairs"] == 1 and report["neighbourhood_only_failed"] == 0 and report["slice_only_failed"] == 1


@pytest.mark.parametrize("folder", ["step5-confirm-p4", "step5-confirm-p7", "step5-pilot-p4-main", "step5-pilot-p7-main",
                                    "step5-pilot-p8-main", "step5-pilot-p14-main", "step5-pilot-p19-main"])
def test_stored_pilots_recompute_to_the_same_report(folder):
    root = Path(__file__).resolve().parents[1]
    stored = json.loads((root / "results/savio" / folder / "efficacy.json").read_text())
    rows = [json.loads(line) for line in (root / "results/savio" / folder / "routes.jsonl").read_text().splitlines()
            if line.strip()]
    manifest = json.loads((root / "configs/rollout" / f"{folder}.manifest.json").read_text())
    assert efficacy.efficacy(manifest, rows, stored["gap_id"]) == stored


def decoy_pilot(slice_only, nbhd_only, concordant_fail=10, concordant_ok=None, total=60):
    """A decoy's paired report with the given discordant counts."""
    concordant_ok = total - slice_only - nbhd_only - concordant_fail if concordant_ok is None else concordant_ok
    outcomes = ([(True, False)] * slice_only + [(False, True)] * nbhd_only + [(True, True)] * concordant_fail
                + [(False, False)] * concordant_ok)
    manifest, rows = pilot(outcomes)
    return efficacy.efficacy(manifest, rows, GAP)["c23_paired"]


def test_a_harmless_decoy_passes_c31_and_can_fail_the_old_band():
    verdict = efficacy.decoy_verdict(decoy_pilot(7, 3))
    assert verdict == {"passes": True, "within_old_band": False}


def test_a_decoy_with_a_large_uplift_fails_c31():
    assert not efficacy.decoy_verdict(decoy_pilot(12, 2))["passes"]


@pytest.mark.parametrize("slice_only, nbhd_only", [(15, 8), (8, 15)])
def test_an_uplift_past_ten_points_fails_c31_in_either_direction_with_a_high_p(slice_only, nbhd_only):
    report = decoy_pilot(slice_only, nbhd_only)
    assert abs(report["uplift_pp"]) == pytest.approx(7 / 60 * 100) and report["mcnemar_p"] > 0.2
    assert not efficacy.decoy_verdict(report)["passes"]


def test_a_small_uplift_with_a_low_p_fails_c31():
    report = decoy_pilot(6, 0, concordant_fail=0, concordant_ok=54)
    assert report["uplift_pp"] == pytest.approx(10.0) and report["mcnemar_p"] < 0.2
    assert not efficacy.decoy_verdict(report)["passes"]


def test_a_small_pilot_cannot_pass_c31_by_having_no_power():
    assert not efficacy.decoy_verdict(decoy_pilot(1, 1, concordant_fail=2, total=20))["passes"]
    assert efficacy.decoy_verdict(efficacy.paired({})) == {"passes": False, "within_old_band": False}


def test_the_report_serializes_to_json_when_every_threshold_but_size_is_met():
    import json
    manifest, rows = pilot([(True, False)] * 9 + [(False, False)])
    json.dumps(efficacy.efficacy(manifest, rows, GAP))



def test_a_screen_passes_on_an_excess_of_slice_only_failures():
    manifest, rows = pilot([(True, False)] * 4 + [(False, True)] + [(False, False)] * 5)
    report = efficacy.efficacy(manifest, rows, GAP)
    assert efficacy.screen_passes(report, {"min_excess_slice_only_failures": 3})
    assert not efficacy.screen_passes(report, {"min_excess_slice_only_failures": 4})


def test_a_screen_report_with_no_pairs_is_not_a_failed_screen(tmp_path, capsys):
    manifest, _ = pilot([(True, False)])
    report = tmp_path / "efficacy.json"
    report.write_text(json.dumps(efficacy.efficacy(manifest, [], GAP)))
    gaps = tmp_path / "gaps.yaml"
    gaps.write_text(f"gaps:\n- gap_id: {GAP}\n  screen_rule:\n    min_excess_slice_only_failures: 3\n")
    assert efficacy.screen_verdict(report, gaps) == efficacy.NO_RESULT_EXIT
    assert "on 0 pairs, 2 routes without an outcome; no result" in capsys.readouterr().out


def test_a_screen_under_its_pair_floor_is_no_result_even_with_an_excess(tmp_path, capsys):
    manifest, rows = pilot([(True, False)] * 7)
    report = tmp_path / "efficacy.json"
    report.write_text(json.dumps(efficacy.efficacy(manifest, rows, GAP)))
    gaps = tmp_path / "gaps.yaml"
    gaps.write_text(f"gaps:\n- gap_id: {GAP}\n  screen_rule:\n    min_excess_slice_only_failures: 3\n    min_pairs: 8\n")
    assert efficacy.screen_verdict(report, gaps) == efficacy.NO_RESULT_EXIT
    assert "on 7 pairs" in capsys.readouterr().out
    manifest, rows = pilot([(True, False)] * 8)
    report.write_text(json.dumps(efficacy.efficacy(manifest, rows, GAP)))
    assert efficacy.screen_verdict(report, gaps) == 0
