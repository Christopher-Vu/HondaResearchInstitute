"""The dashboard's weekly summary stays compact and renderable."""
from pathlib import Path

import yaml


PROGRESS = Path(__file__).resolve().parents[1] / "docs/steps/progress.yaml"


def test_dashboard_week_summary_has_bounded_attributed_items():
    progress = yaml.safe_load(PROGRESS.read_text())
    week = progress["week"]
    assert str(week["start"]) <= str(week["end"])
    assert week["done"] and week["next"]
    for item in [*week["done"], *week["next"]]:
        assert item["who"]
        assert 1 <= len(item["text"].split()) <= 20
