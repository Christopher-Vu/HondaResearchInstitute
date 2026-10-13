"""B2 human taxonomy baseline tests (PRD 9.3)."""
import ast
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from baselines import taxonomy  # noqa: E402
from baselines.taxonomy import (  # noqa: E402
    TaxonomyConfig, abilities_of, preset_weather_name, taxonomy_directive,
)
from harness.schema import Gap  # noqa: E402
from harness.scoring import score  # noqa: E402

CLEAR_NOON = dict(zip(taxonomy.PRESET_FIELDS, taxonomy.PRESET_VALUES["ClearNoon"]))
FOGGY = CLEAR_NOON | {"fog_density": 55.0}


def make_records(prefix, n, n_failed, *, scenario="Other", town="Town01",
                 weather=CLEAR_NOON):
    return [{"id": "%s%03d" % (prefix, i), "town": town, "scenario": scenario,
             "weather": dict(weather), "failed": i < n_failed} for i in range(n)]


def cfg(**kw):
    return TaxonomyConfig(**({"fields": ("scenario",)} | kw))


def names(directive):
    return [a.name for a in directive.axes]


def test_highest_failure_rate_stratum_with_support_ranks_first():
    records = (make_records("a", 30, 6, scenario="A")
               + make_records("b", 30, 21, scenario="B")
               + make_records("c", 30, 12, scenario="C"))
    d = taxonomy_directive(records, cfg())
    assert names(d) == ["scenario = B", "scenario = C", "scenario = A"]
    assert [a.rank for a in d.axes] == [1, 2, 3]
    assert d.axes[0].score == pytest.approx(0.7)
    assert d.method == "B2_taxonomy"
    assert d.axes[0].causal == {"verdict": "untested"}


def test_small_stratum_with_perfect_rate_is_excluded_by_min_support():
    records = make_records("a", 30, 3, scenario="A") + make_records("s", 5, 5, scenario="S")
    d = taxonomy_directive(records, cfg(min_support=20))
    assert names(d) == ["scenario = A"]


def test_ties_break_by_failures_then_field_order_then_value():
    records = (make_records("a", 20, 10, scenario="Z")
               + make_records("b", 40, 20, scenario="Y")
               + make_records("c", 40, 20, scenario="X"))
    d = taxonomy_directive(records, cfg())
    assert names(d) == ["scenario = X", "scenario = Y", "scenario = Z"]


def test_equal_rate_and_failures_prefer_earlier_field():
    records = make_records("a", 20, 10, scenario="A", town="T1")
    records += make_records("b", 20, 0, scenario="A2", town="T2")
    reversed_fields = taxonomy_directive(records, TaxonomyConfig(fields=("town", "scenario")))
    assert names(reversed_fields)[0] == "town = T1"
    # scenario = A and town = T1 hold the same failing set, so only one is emitted
    assert len(reversed_fields.axes) == 1


def test_weather_maps_stock_presets_by_name_and_everything_else_to_custom():
    assert preset_weather_name(CLEAR_NOON) == "ClearNoon"
    assert preset_weather_name(CLEAR_NOON | {"fog_density": 2.0000004}) == "ClearNoon"
    assert preset_weather_name(CLEAR_NOON | {"sun_azimuth_angle": 33.0}) == "ClearNoon"
    assert preset_weather_name(FOGGY) == "custom"
    assert preset_weather_name({"cloudiness": 5.0}) == "custom"


def test_weather_strata_use_preset_names_and_pool_custom():
    records = (make_records("a", 25, 5, weather=CLEAR_NOON)
               + make_records("b", 12, 12, weather=FOGGY)
               + make_records("c", 12, 12, weather=FOGGY | {"fog_density": 70.0}))
    d = taxonomy_directive(records, TaxonomyConfig(fields=("weather",)))
    assert names(d) == ["weather = custom", "weather = ClearNoon"]
    assert len(d.axes[0].rollouts) == 24


def test_rollout_in_multi_ability_scenario_joins_each_ability_stratum():
    assert abilities_of("BlockedIntersection") == ["Emergency_Brake", "Traffic_Signs"]
    assert abilities_of("NotAScenario") == []
    records = make_records("a", 20, 20, scenario="BlockedIntersection")
    records += make_records("b", 20, 10, scenario="InvadingTurn")
    strata = taxonomy.build_strata(records, TaxonomyConfig(fields=("ability",)))
    assert len(strata[("ability", "Emergency_Brake")]) == 20
    assert len(strata[("ability", "Traffic_Signs")]) == 20
    assert len(strata[("ability", "Give_Way")]) == 20


def test_duplicate_failing_sets_are_not_emitted_twice():
    records = (make_records("a", 25, 10, scenario="A")
               + make_records("b", 25, 0, scenario="B"))
    d = taxonomy_directive(records, TaxonomyConfig(fields=("scenario", "town")))
    # town = Town01 fails on the same 10 rollouts as scenario = A
    assert names(d) == ["scenario = A"]


def test_strata_with_no_failures_are_not_emitted():
    d = taxonomy_directive(make_records("a", 30, 0, scenario="A"), cfg())
    assert d.axes == []
    d.validate()


def test_budget_is_respected():
    records = []
    for i in range(6):
        records += make_records("s%d" % i, 20, 1 + i, scenario="S%d" % i)
    d = taxonomy_directive(records, cfg(budget_m=3))
    assert len(d.axes) == 3
    assert names(d) == ["scenario = S5", "scenario = S4", "scenario = S3"]


def test_axis_card_describes_the_stratum():
    d = taxonomy_directive(make_records("a", 20, 5, scenario="HighwayExit"), cfg())
    axis = d.axes[0]
    assert axis.name == "scenario = HighwayExit"
    assert "5 of 20" in axis.description and "0.250" in axis.description
    assert axis.rollouts == {"a%03d" % i for i in range(5)}


def test_custom_weather_name_callable_is_used():
    records = make_records("a", 20, 10)
    d = taxonomy_directive(records, TaxonomyConfig(fields=("weather",)),
                           weather_name=lambda w: "everything")
    assert names(d) == ["weather = everything"]


def test_config_validation():
    for bad in (TaxonomyConfig(budget_m=0), TaxonomyConfig(min_support=0),
                TaxonomyConfig(fields=()), TaxonomyConfig(fields=("colour",)),
                TaxonomyConfig(fields=("town", "town"))):
        with pytest.raises(ValueError):
            bad.validate()


def test_directive_scores_with_the_real_scorer():
    records = (make_records("a", 40, 30, scenario="A")
               + make_records("b", 40, 4, scenario="B"))
    d = taxonomy_directive(records, TaxonomyConfig())
    gap = Gap(gap_id="g1", tier="T0_control",
              failing_rollouts={"a%03d" % i for i in range(30)},
              slice_rollouts={"a%03d" % i for i in range(40)},
              efficacy={"fail_rate_in": 0.75, "fail_rate_neighbourhood": 0.1,
                        "fisher_p": 1e-9, "n_in": 40})
    report = score(d, [gap])
    assert report.recall_by_tier["T0_control"] == 1.0


def test_weather_table_copy_matches_dev_routes():
    dev_routes = pytest.importorskip("dev_routes")
    assert taxonomy.PRESET_FIELDS == dev_routes.PRESET_FIELDS
    assert taxonomy.PRESET_VALUES == dev_routes.PRESET_VALUES


def test_ability_table_copy_matches_bench2drive_script():
    path = ROOT / ".runtime/simlingo/Bench2Drive/tools/ability_benchmark.py"
    if not path.exists():
        pytest.skip("Bench2Drive checkout not present")
    for node in ast.parse(path.read_text()).body:
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "Ability":
            upstream = ast.literal_eval(node.value)
            break
    else:
        pytest.fail("Ability dict not found")
    assert taxonomy.ABILITY_SCENARIOS == {
        ability: tuple(dict.fromkeys(scenarios)) for ability, scenarios in upstream.items()}
