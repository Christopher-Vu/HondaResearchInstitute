"""Practice-gap predicates: how a gap's definition is read against a route's metadata."""
from pathlib import Path

import pytest
import yaml

from harness.predicates import matches

PRACTICE_GAPS = Path(__file__).resolve().parents[1] / "gaps/practice/practice_v1.yaml"

ROUTE = {"scenario": "DynamicObjectCrossing", "param": {"blocker_model": "static.prop.container", "distance": "40"},
         "weather": {"sun_altitude_angle": -90.0, "dust_storm": 0.0}}


def condition(field, op, value):
    return {"field": field, "op": op, "value": value}


def test_every_condition_must_hold():
    assert matches([condition("scenario", "==", "DynamicObjectCrossing"),
                    condition("weather.sun_altitude_angle", "<", 0)], ROUTE)
    assert not matches([condition("scenario", "==", "DynamicObjectCrossing"),
                        condition("weather.sun_altitude_angle", ">", 0)], ROUTE)


def test_equality_and_membership_compare_strings_and_numbers():
    assert matches([condition("param.blocker_model", "==", "static.prop.container")], ROUTE)
    assert not matches([condition("param.blocker_model", "==", "static.prop.advertisement")], ROUTE)
    assert matches([condition("scenario", "in", ["Accident", "DynamicObjectCrossing"])], ROUTE)
    assert not matches([condition("scenario", "in", ["Accident"])], ROUTE)
    assert matches([condition("param.distance", "==", 40)], ROUTE)
    assert matches([condition("param.distance", "in", [30, 40.0])], ROUTE)


@pytest.mark.parametrize("op, value, expected", [
    ("<", 41, True), ("<", 40, False), ("<=", 40, True), (">", 39, True), (">", 40, False), (">=", 40, True),
    (">=", "40", True)])
def test_ordering_reads_strings_as_numbers(op, value, expected):
    assert matches([condition("param.distance", op, value)], ROUTE) is expected


def test_a_missing_field_makes_its_condition_false():
    assert not matches([condition("param.crossing_angle", "==", 0)], ROUTE)
    assert not matches([condition("weather.fog_density", "<", 100)], ROUTE)
    assert not matches([condition("scenario.family", "==", "DynamicObjectCrossing")], ROUTE)
    assert not matches([condition("param.crossing_angle", "in", [0])], ROUTE)


def test_text_is_never_ordered_against_a_number():
    assert not matches([condition("scenario", "<", 5)], ROUTE)
    assert not matches([condition("param.distance", ">", "far")], ROUTE)


def test_unknown_operator_raises_even_when_another_condition_already_failed():
    with pytest.raises(ValueError, match="Unknown predicate operator"):
        matches([condition("scenario", "==", "Accident"), condition("scenario", "contains", "Dyn")], ROUTE)


def test_empty_predicate_is_refused_rather_than_matching_everything():
    with pytest.raises(ValueError, match="at least one condition"):
        matches([], ROUTE)


def practice_predicate(gap_id):
    gaps = yaml.safe_load(PRACTICE_GAPS.read_text())["gaps"]
    return next(gap["predicate"] for gap in gaps if gap["gap_id"] == gap_id)


def test_dust_storm_gap_needs_dust_and_darkness_together():
    predicate = practice_predicate("P1_dust_storm_night")
    assert matches(predicate, {"weather": {"dust_storm": 100.0, "sun_altitude_angle": -90.0}})
    assert not matches(predicate, {"weather": {"dust_storm": 100.0, "sun_altitude_angle": 45.0}})
    assert not matches(predicate, {"weather": {"dust_storm": 0.0, "sun_altitude_angle": -90.0}})


def test_pedestrian_gap_needs_the_container_the_crossing_scenario_and_darkness():
    predicate = practice_predicate("P2_occluded_pedestrian_night")
    assert matches(predicate, ROUTE)
    assert not matches(predicate, ROUTE | {"weather": {"sun_altitude_angle": 45.0}})
    assert not matches(predicate, ROUTE | {"param": {"blocker_model": "static.prop.advertisement"}})
    assert not matches(predicate, ROUTE | {"scenario": "PedestrianCrossing"})
