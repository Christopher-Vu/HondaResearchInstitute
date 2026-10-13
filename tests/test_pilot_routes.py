"""The Step 5 pilot generator: pairs on distinct base routes that differ only in the planted weather."""
import json
from collections import Counter
from pathlib import Path

import pytest
import yaml

import pilot_routes
from harness.predicates import matches

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/rollout/step5-pilot-p3.yaml"


@pytest.fixture(scope="module")
def config():
    loaded = yaml.safe_load(CONFIG.read_text())
    if not (ROOT / loaded["pilot"]["base_routes_file"]).is_file():
        pytest.skip("pinned routes file not installed")
    return loaded


@pytest.fixture(scope="module")
def pilot(config):
    return pilot_routes.generate(config)


def test_each_of_sixty_base_routes_has_one_slice_and_one_neighbourhood_route(pilot):
    _document, entries = pilot
    assert Counter(entry["role"] for entry in entries) == {"pilot_slice": 60, "pilot_neighbourhood": 60}
    assert set(Counter(entry["base_id"] for entry in entries).values()) == {2}


def test_a_pair_differs_only_in_fog(pilot):
    _document, entries = pilot
    by_base = {}
    for entry in entries:
        by_base.setdefault(entry["base_id"], {})[entry["role"]] = entry
    for pair in by_base.values():
        fog, clear = pair["pilot_slice"], pair["pilot_neighbourhood"]
        changed = {name for name in fog["weather"] if fog["weather"][name] != clear["weather"][name]}
        assert changed == {"fog_density"}
        assert (fog["town"], fog["scenario"], fog["param"]) == (clear["town"], clear["scenario"], clear["param"])


def test_the_gap_predicate_matches_the_slice_and_nothing_else(config, pilot):
    _document, entries = pilot
    gaps = yaml.safe_load((ROOT / config["pilot"]["practice_gaps"]).read_text())["gaps"]
    gap = next(gap for gap in gaps if gap["gap_id"] == config["pilot"]["gap_id"])
    assert {entry["id"] for entry in entries if matches(gap["predicate"], entry)} == {
        entry["id"] for entry in entries if entry["role"] == "pilot_slice"}


def test_no_stock_daytime_preset_falls_in_the_gap(config):
    gaps = yaml.safe_load((ROOT / config["pilot"]["practice_gaps"]).read_text())["gaps"]
    gap = next(gap for gap in gaps if gap["gap_id"] == config["pilot"]["gap_id"])
    import dev_routes
    for name in dev_routes.PRESET_VALUES:
        assert not matches(gap["predicate"], {"weather": dev_routes.preset_weather(name)}), name


def test_committed_files_are_what_the_generator_writes(config, pilot):
    document, entries = pilot
    assert (ROOT / config["route"]["routes_file"]).read_text() == document
    assert json.loads((ROOT / config["route"]["manifest"]).read_text()) == entries
