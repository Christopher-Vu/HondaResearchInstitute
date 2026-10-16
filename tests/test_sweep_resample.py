import json

from src.discovery.sweep_resample import merge


def run(index, ranks):
    return {"index": index, "dropped": 1, "pairs": [
        {"site": "driving_queries", "layer": layer, "combined_rank": rank, "family_ranks": {"failure_auroc": rank}}
        for layer, rank in ranks.items()]}


def test_merge_counts_positions_not_raw_ranks(tmp_path):
    path = tmp_path / "r.json"
    path.write_text(json.dumps({"resamples": [run(0, {10: 1.5, 11: 3.0, 12: 9.0}),
                                              run(1, {10: 4.0, 11: 2.0, 12: 9.0})]}))
    rows = {row["layer"]: row for row in merge([path])["pairs"]}
    assert rows[10]["top2_share"] == 1.0 and rows[11]["top2_share"] == 1.0
    assert rows[12]["top2_share"] == 0.0 and rows[12]["top3_share"] == 1.0
    assert rows[10]["median_failure_auroc_rank"] == 2.75
