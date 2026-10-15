"""Practice-gap efficacy: PRD 9.1's unpaired Fisher rule and CONFLICTS.md C23's paired McNemar rule."""
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


def test_the_report_serializes_to_json_when_every_threshold_but_size_is_met():
    import json
    manifest, rows = pilot([(True, False)] * 9 + [(False, False)])
    json.dumps(efficacy.efficacy(manifest, rows, GAP))



def test_a_screen_passes_on_an_excess_of_slice_only_failures():
    manifest, rows = pilot([(True, False)] * 4 + [(False, True)] + [(False, False)] * 5)
    report = efficacy.efficacy(manifest, rows, GAP)
    assert efficacy.screen_passes(report, {"min_excess_slice_only_failures": 3})
    assert not efficacy.screen_passes(report, {"min_excess_slice_only_failures": 4})
