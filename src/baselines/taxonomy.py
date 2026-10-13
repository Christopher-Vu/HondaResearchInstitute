"""B2: the human taxonomy baseline. PRD 9.3.

PRD 9.3 defines B2 in one line: top single-factor strata of benchmark metadata
(scenario family, weather, town, ability), ranked by failure rate. This is the
standard practice a benchmark user would follow with no tooling: slice the
results by one metadata column at a time and read off the worst slices.

Each stratum is one (field, value) pair, such as scenario = HighwayExit. Its
axis claims the stratum's failing rollouts.

Interpretations, pending sign-off (the PRD does not make these choices):
1. min_support = 20: a stratum needs at least 20 rollouts to be ranked. This
   reuses the contrastive method's support floor in PRD 9.2. Without a floor a
   one-rollout stratum that failed has a 100% failure rate and tops the list.
2. Weather is the name of the stock CARLA preset whose parameters equal the
   record's on every field in PRESET_FIELDS (tolerance 1e-6). Any other weather
   is pooled into the single value "custom".
3. Ability follows Bench2Drive's scenario-to-ability table. A scenario can be
   listed under several abilities, so a rollout joins every ability stratum that
   lists its scenario. Duplicate scenario names inside one ability are dropped.
   A scenario listed under no ability joins no ability stratum.
4. Identical-set deduplication: walking down the ranking, a stratum is skipped
   if its failing-rollout set is empty or equals the set of an axis already
   emitted. Two strata with the same failing rollouts are one claim to the
   scorer, and emitting both would spend budget on a repeat.
5. Ranking is failure rate descending. Ties go to the stratum with more
   failures, then to the field's position in the config, then to the value
   string.

Must never read the answer key. CI-enforced; see scripts/check_sealed_imports.py.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, Mapping, Sequence

from harness.schema import AxisCard, Directive, SupportingEpisode

METHOD = "B2_taxonomy"
KNOWN_FIELDS = ("scenario", "weather", "town", "ability")
CUSTOM_WEATHER = "custom"
WEATHER_TOLERANCE = 1e-6

# Copy of adapters/simlingo/dev_routes.PRESET_FIELDS and PRESET_VALUES.
# src/ does not import from adapters/; tests/test_taxonomy.py asserts the copy
# is equal.
PRESET_FIELDS = ("cloudiness", "precipitation", "precipitation_deposits",
                 "wind_intensity", "sun_altitude_angle", "fog_density",
                 "fog_distance", "fog_falloff", "wetness", "dust_storm")
PRESET_VALUES = {
    "ClearNight": (5, 0, 0, 10, -90, 60, 75, 1, 0, 0),
    "ClearNoon": (5, 0, 0, 10, 45, 2, 0.75, 0.1, 0, 0),
    "ClearSunset": (5, 0, 0, 10, 15, 2, 0.75, 0.1, 0, 0),
    "CloudyNight": (60, 0, 0, 10, -90, 60, 0.75, 0.1, 0, 0),
    "CloudyNoon": (60, 0, 0, 10, 45, 3, 0.75, 0.1, 0, 0),
    "CloudySunset": (60, 0, 0, 10, 15, 3, 0.75, 0.1, 0, 0),
    "DustStorm": (100, 0, 0, 100, 45, 2, 0.75, 0.1, 0, 100),
    "HardRainNight": (100, 100, 90, 100, -90, 100, 0.75, 0.1, 100, 0),
    "HardRainNoon": (100, 100, 90, 100, 45, 7, 0.75, 0.1, 0, 0),
    "HardRainSunset": (100, 100, 90, 100, 15, 7, 0.75, 0.1, 0, 0),
    "MidRainSunset": (60, 60, 60, 60, 15, 3, 0.75, 0.1, 0, 0),
    "MidRainyNight": (80, 60, 60, 60, -90, 60, 0.75, 0.1, 80, 0),
    "MidRainyNoon": (60, 60, 60, 60, 45, 3, 0.75, 0.1, 0, 0),
    "SoftRainNight": (60, 30, 50, 30, -90, 60, 0.75, 0.1, 60, 0),
    "SoftRainNoon": (20, 30, 50, 30, 45, 3, 0.75, 0.1, 0, 0),
    "SoftRainSunset": (20, 30, 50, 30, 15, 2, 0.75, 0.1, 0, 0),
    "WetCloudyNight": (60, 0, 50, 10, -90, 60, 0.75, 0.1, 60, 0),
    "WetCloudyNoon": (60, 0, 50, 10, 45, 3, 0.75, 0.1, 0, 0),
    "WetCloudySunset": (60, 0, 50, 10, 15, 2, 0.75, 0.1, 0, 0),
    "WetNight": (5, 0, 50, 10, -90, 60, 75, 1, 60, 0),
    "WetNoon": (5, 0, 50, 10, 45, 3, 0.75, 0.1, 0, 0),
}

# Copy of the Ability dict in Bench2Drive/tools/ability_benchmark.py, with the
# duplicate scenario names inside each list removed. tests/test_taxonomy.py
# compares it with that file when the file exists.
ABILITY_SCENARIOS = {
    "Overtaking": (
        "Accident", "AccidentTwoWays", "ConstructionObstacle",
        "ConstructionObstacleTwoWays", "HazardAtSideLaneTwoWays", "HazardAtSideLane",
        "ParkedObstacleTwoWays", "ParkedObstacle", "VehicleOpensDoorTwoWays",
    ),
    "Merging": (
        "CrossingBicycleFlow", "EnterActorFlow", "HighwayExit", "InterurbanActorFlow",
        "HighwayCutIn", "InterurbanAdvancedActorFlow", "MergerIntoSlowTrafficV2",
        "MergerIntoSlowTraffic", "NonSignalizedJunctionLeftTurn",
        "NonSignalizedJunctionRightTurn", "NonSignalizedJunctionLeftTurnEnterFlow",
        "ParkingExit", "SequentialLaneChange", "SignalizedJunctionLeftTurn",
        "SignalizedJunctionRightTurn", "SignalizedJunctionLeftTurnEnterFlow",
    ),
    "Emergency_Brake": (
        "BlockedIntersection", "DynamicObjectCrossing", "HardBreakRoute",
        "OppositeVehicleTakingPriority", "OppositeVehicleRunningRedLight",
        "ParkingCutIn", "PedestrianCrossing", "ParkingCrossingPedestrian",
        "StaticCutIn", "VehicleTurningRoute", "VehicleTurningRoutePedestrian",
        "ControlLoss",
    ),
    "Give_Way": (
        "InvadingTurn", "YieldToEmergencyVehicle",
    ),
    "Traffic_Signs": (
        "BlockedIntersection", "OppositeVehicleTakingPriority",
        "OppositeVehicleRunningRedLight", "PedestrianCrossing", "VehicleTurningRoute",
        "VehicleTurningRoutePedestrian", "EnterActorFlow", "CrossingBicycleFlow",
        "NonSignalizedJunctionLeftTurn", "NonSignalizedJunctionRightTurn",
        "NonSignalizedJunctionLeftTurnEnterFlow", "SignalizedJunctionLeftTurn",
        "SignalizedJunctionRightTurn", "SignalizedJunctionLeftTurnEnterFlow",
        "T_Junction", "VanillaNonSignalizedTurn",
        "VanillaSignalizedTurnEncounterGreenLight",
        "VanillaSignalizedTurnEncounterRedLight",
        "VanillaNonSignalizedTurnEncounterStopsign",
    ),
}

Record = Mapping[str, object]
Stratum = tuple[str, str]


@dataclass
class TaxonomyConfig:
    """Committed and hashed before the gaps are finalised (PRD 9.3 fairness rule)."""

    budget_m: int = 10
    min_support: int = 20
    fields: tuple[str, ...] = KNOWN_FIELDS

    def validate(self) -> None:
        if self.budget_m <= 0:
            raise ValueError("budget_m must be positive")
        if self.min_support < 1:
            raise ValueError("min_support must be at least 1")
        if not self.fields:
            raise ValueError("fields is empty")
        unknown = [f for f in self.fields if f not in KNOWN_FIELDS]
        if unknown:
            raise ValueError("unknown fields %s; known: %s" % (unknown, KNOWN_FIELDS))
        if len(set(self.fields)) != len(self.fields):
            raise ValueError("fields contains duplicates: %s" % (self.fields,))


def preset_weather_name(weather: Mapping[str, float]) -> str:
    """Name of the stock preset matching `weather` on every preset field, else "custom"."""
    try:
        observed = [float(weather[f]) for f in PRESET_FIELDS]
    except (KeyError, TypeError, ValueError):
        return CUSTOM_WEATHER
    for name, values in PRESET_VALUES.items():
        if all(math.isclose(o, v, rel_tol=0.0, abs_tol=WEATHER_TOLERANCE)
               for o, v in zip(observed, values)):
            return name
    return CUSTOM_WEATHER


def abilities_of(scenario: str) -> list[str]:
    return [a for a, scenarios in ABILITY_SCENARIOS.items() if scenario in scenarios]


def _values_for(record: Record, field: str,
                weather_name: Callable[[dict], str]) -> list[str]:
    if field == "ability":
        return abilities_of(str(record["scenario"]))
    if field == "weather":
        return [weather_name(dict(record["weather"]))]
    return [str(record[field])]


def build_strata(records: Sequence[Record], cfg: TaxonomyConfig,
                 weather_name: Callable[[dict], str] = preset_weather_name
                 ) -> dict[Stratum, list[Record]]:
    """Every (field, value) stratum with the records that belong to it."""
    strata: dict[Stratum, list[Record]] = {}
    for record in records:
        for field in cfg.fields:
            for value in _values_for(record, field, weather_name):
                strata.setdefault((field, value), []).append(record)
    return strata


def _failing_ids(members: Sequence[Record]) -> list[str]:
    return [str(r["id"]) for r in members if r["failed"]]


def rank_strata(strata: Mapping[Stratum, Sequence[Record]], cfg: TaxonomyConfig
                ) -> list[tuple[Stratum, int, int]]:
    """Strata with enough support as (stratum, failures, size), best first."""
    field_order = {f: i for i, f in enumerate(cfg.fields)}
    kept = [(key, len(_failing_ids(members)), len(members))
            for key, members in strata.items() if len(members) >= cfg.min_support]
    kept.sort(key=lambda t: (-t[1] / t[2], -t[1], field_order[t[0][0]], t[0][1]))
    return kept


def _axis_card(stratum: Stratum, failing: Sequence[str], size: int, rank: int
               ) -> AxisCard:
    field, value = stratum
    rate = len(failing) / size
    return AxisCard(
        axis_id="B2-a%d" % rank,
        name="%s = %s" % (field, value),
        description="%d of %d rollouts with %s = %s failed (failure rate %.3f)"
                    % (len(failing), size, field, value, rate),
        rank=rank,
        score=rate,
        method=METHOD,
        supporting_episodes=[SupportingEpisode(r, 0.0, (0, 0)) for r in failing],
        preprocessing=[],
        causal={"verdict": "untested"},
    )


def taxonomy_directive(records: Sequence[Record], cfg: TaxonomyConfig, *,
                       weather_name: Callable[[dict], str] = preset_weather_name
                       ) -> Directive:
    """B2: the top single-factor strata by failure rate, as a validated Directive."""
    cfg.validate()
    strata = build_strata(records, cfg, weather_name)
    emitted_sets: set[frozenset[str]] = set()
    axes: list[AxisCard] = []
    for stratum, _, size in rank_strata(strata, cfg):
        if len(axes) == cfg.budget_m:
            break
        failing = _failing_ids(strata[stratum])
        if not failing or frozenset(failing) in emitted_sets:
            continue
        emitted_sets.add(frozenset(failing))
        axes.append(_axis_card(stratum, failing, size, len(axes) + 1))
    directive = Directive(method=METHOD, axes=axes, budget_m=cfg.budget_m)
    directive.validate()
    return directive
