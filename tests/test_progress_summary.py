"""Keep the small public dashboard summary current and renderable."""
from datetime import date
from pathlib import Path

import yaml


PROGRESS = Path(__file__).resolve().parents[1] / "docs/steps/progress.yaml"


def test_current_week_summary_is_compact_and_has_a_valid_compute_total():
    progress = yaml.safe_load(PROGRESS.read_text())

    assert progress["updated"] == date(2026, 11, 19)
    assert progress["week"]["start"] == date(2026, 11, 16)
    assert progress["week"]["end"] == date(2026, 11, 20)
    assert progress["compute"]["spent"][0]["su"] == 17800
    for group in ("done", "next"):
        assert progress["week"][group]
        assert all(len(item["text"].split()) <= 20 for item in progress["week"][group])
    assert "replay completed" in progress["week"]["done"][2]["text"]
