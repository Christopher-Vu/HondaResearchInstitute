"""Data contracts from PRD 8.3 (axis card) and 9.1 (gap spec).

Validation only. No policy, no simulator, no GPU, no cluster. Importable
anywhere, which is the point: a directive that does not validate here cannot
enter scoring, so a malformed baseline fails loudly instead of silently
scoring zero and looking like a real negative result.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

TIERS = ("T0_control", "T1_enumerable", "T2_interactional")
METHODS = ("contrastive", "sae", "probe_residual")
BASELINES = (
    "B1_random", "B2_taxonomy", "B3_behavioral", "B4_enumerated",
    "B4p_enumerated_pairs", "B5_domino", "B6_detector", "B7_actstats",
)
CAUSAL_VERDICTS = ("causal", "correlational_only", "untested")
# PRD 9.2's preprocessing variants. Only the first can satisfy harness validity (PRD 13.1).
NON_RESIDUALIZED, ACTION_RESIDUAL = "non_residualized", "action_residual"
PREPROCESSING = (NON_RESIDUALIZED, ACTION_RESIDUAL)
# How a gap re-confirms efficacy on the test pool: PRD 9.1's Fisher rule, or CONFLICTS.md C23's paired rule if accepted.
FISHER_RULE, PAIRED_RULE = "prd_9_1", "c23"
EFFICACY_RULES = (FISHER_RULE, PAIRED_RULE)


class SchemaError(ValueError):
    """A contract violation. Loud by design (PRD 8.3)."""


def _req(d: dict, key: str, typ, where: str):
    if key not in d:
        raise SchemaError("%s: missing required field %r" % (where, key))
    v = d[key]
    if not isinstance(v, typ):
        raise SchemaError("%s: %r must be %s, got %s"
                          % (where, key, typ, type(v).__name__))
    return v


@dataclass(frozen=True)
class SupportingEpisode:
    episode_id: str
    activation: float
    timesteps: tuple[int, int]

    def __post_init__(self):
        a, b = self.timesteps
        if a > b:
            raise SchemaError("%s: timesteps %s not ordered"
                              % (self.episode_id, self.timesteps))


@dataclass
class AxisCard:
    """One discovered axis. PRD 8.3.

    name and description are not optional: an axis without them is a cluster,
    not a discovery. Enforced in validate().
    """

    axis_id: str
    name: str
    description: str
    rank: int
    score: float
    method: str
    config_hash: str = ""
    supporting_episodes: list[SupportingEpisode] = field(default_factory=list)
    layer: str | None = None
    aggregation: str | None = None
    preprocessing: list[str] = field(default_factory=list)
    generality: dict[str, Any] = field(default_factory=dict)
    causal: dict[str, Any] = field(default_factory=dict)
    gate: dict[str, Any] = field(default_factory=dict)
    parameterization: dict[str, Any] = field(default_factory=dict)

    @property
    def rollouts(self) -> set[str]:
        """R(a_j): the rollout set this axis claims. The unit of scoring."""
        return {e.episode_id for e in self.supporting_episodes}

    def to_dict(self) -> dict[str, Any]:
        """What from_dict reads back: a directive crosses from the methods to scoring only as a file."""
        return {
            "axis_id": self.axis_id, "name": self.name, "description": self.description,
            "rank": int(self.rank), "score": float(self.score),
            "provenance": {"method": self.method, "config_hash": self.config_hash, "layer": self.layer,
                           "aggregation": self.aggregation, "preprocessing": list(self.preprocessing)},
            "supporting_episodes": [{"episode_id": e.episode_id, "activation": float(e.activation),
                                     "timesteps": [int(e.timesteps[0]), int(e.timesteps[1])]}
                                    for e in self.supporting_episodes],
            "generality": self.generality, "causal": self.causal, "gate": self.gate,
            "parameterization": self.parameterization,
        }

    def validate(self) -> None:
        if not self.name.strip():
            raise SchemaError(
                "%s: empty name. An axis without a human-readable name is a "
                "cluster, not a discovery (PRD 8.3)" % self.axis_id)
        if not self.description.strip():
            raise SchemaError("%s: empty description (PRD 8.3)" % self.axis_id)
        if self.method not in METHODS + BASELINES:
            raise SchemaError("%s: unknown method %r" % (self.axis_id, self.method))
        if self.rank < 1:
            raise SchemaError("%s: rank must be >= 1" % self.axis_id)
        verdict = self.causal.get("verdict", "untested")
        if verdict not in CAUSAL_VERDICTS:
            raise SchemaError("%s: causal.verdict %r not in %s"
                              % (self.axis_id, verdict, CAUSAL_VERDICTS))
        ids = [e.episode_id for e in self.supporting_episodes]
        if len(ids) != len(set(ids)):
            raise SchemaError("%s: duplicate episode ids" % self.axis_id)

    @classmethod
    def from_dict(cls, d: dict) -> "AxisCard":
        where = "axis %s" % d.get("axis_id", "<no id>")
        eps = []
        for e in d.get("supporting_episodes", []):
            ts = _req(e, "timesteps", (list, tuple), where)
            if len(ts) != 2:
                raise SchemaError("%s: timesteps must have 2 entries" % where)
            eps.append(SupportingEpisode(
                episode_id=_req(e, "episode_id", str, where),
                activation=float(_req(e, "activation", (int, float), where)),
                timesteps=(int(ts[0]), int(ts[1])),
            ))
        prov = d.get("provenance", {})
        card = cls(
            axis_id=_req(d, "axis_id", str, where),
            name=_req(d, "name", str, where),
            description=_req(d, "description", str, where),
            rank=int(_req(d, "rank", int, where)),
            score=float(_req(d, "score", (int, float), where)),
            method=prov.get("method", d.get("method", "")),
            config_hash=prov.get("config_hash", d.get("config_hash", "")),
            supporting_episodes=eps,
            layer=prov.get("layer"),
            aggregation=prov.get("aggregation"),
            preprocessing=list(prov.get("preprocessing", [])),
            generality=d.get("generality", {}),
            causal=d.get("causal", {}),
            gate=d.get("gate", {}),
            parameterization=d.get("parameterization", {}),
        )
        card.validate()
        return card


@dataclass
class Directive:
    """A ranked list of at most M axes, from one method. PRD 10.2.

    Precision always divides by M, so the budget is part of the contract
    rather than just the output length.
    """

    method: str
    axes: list[AxisCard]
    budget_m: int = 10
    preprocessing: str = NON_RESIDUALIZED

    def validate(self) -> None:
        if self.preprocessing not in PREPROCESSING:
            raise SchemaError("%s: preprocessing %r not in %s"
                              % (self.method, self.preprocessing, PREPROCESSING))
        if any(self.preprocessing not in a.preprocessing for a in self.axes if set(a.preprocessing) & set(PREPROCESSING)):
            raise SchemaError("%s: an axis says it came from another preprocessing variant than %s"
                              % (self.method, self.preprocessing))
        if len(self.axes) > self.budget_m:
            raise SchemaError("%s: %d axes exceeds budget M=%d"
                              % (self.method, len(self.axes), self.budget_m))
        if len({a.axis_id for a in self.axes}) != len(self.axes):
            raise SchemaError("%s: duplicate axis_ids" % self.method)
        for a in self.axes:
            a.validate()

    @classmethod
    def from_dict(cls, d: dict) -> "Directive":
        obj = cls(
            method=_req(d, "method", str, "directive"),
            axes=[AxisCard.from_dict(a) for a in d.get("axes", [])],
            budget_m=int(d.get("budget_m", 10)),
            preprocessing=d.get("preprocessing", NON_RESIDUALIZED),
        )
        obj.validate()
        return obj

    def to_dict(self) -> dict[str, Any]:
        return {"method": self.method, "budget_m": self.budget_m, "preprocessing": self.preprocessing,
                "axes": [a.to_dict() for a in self.axes]}


@dataclass
class Gap:
    """A planted gap. PRD 9.1.

    failing_rollouts is F(g) and is what scoring matches against. Only ever
    populated from sealed material, inside scoring code.
    """

    gap_id: str
    tier: str
    failing_rollouts: set[str]
    slice_rollouts: set[str] = field(default_factory=set)
    efficacy: dict[str, Any] = field(default_factory=dict)
    is_decoy: bool = False

    def validate(self) -> None:
        if self.tier not in TIERS:
            raise SchemaError("%s: tier %r not in %s" % (self.gap_id, self.tier, TIERS))
        if self.slice_rollouts and not self.failing_rollouts <= self.slice_rollouts:
            raise SchemaError("%s: failing rollouts are not a subset of the slice"
                              % self.gap_id)

    def passes_efficacy(self, *, min_uplift_pp: float = 20.0,
                        min_ratio: float = 2.0, max_p: float = 0.01,
                        min_n: int = 30) -> bool:
        """PRD 9.1 thresholds, all required together.

        A candidate region is only a gap if the policy demonstrably fails more
        inside it than in its matched neighbourhood. Decoys are expected to
        fail this check, which is what makes them decoys.
        """
        e = self.efficacy
        try:
            p_in = float(e["fail_rate_in"])
            p_nbhd = float(e["fail_rate_neighbourhood"])
            fisher_p = float(e["fisher_p"])
            n_in = int(e["n_in"])
        except (KeyError, TypeError, ValueError) as exc:
            raise SchemaError("%s: incomplete efficacy stats: %s" % (self.gap_id, exc))
        uplift_pp = (p_in - p_nbhd) * 100.0
        ratio = p_in / p_nbhd if p_nbhd > 0 else float("inf")
        return (uplift_pp >= min_uplift_pp and ratio >= min_ratio
                and fisher_p < max_p and n_in >= min_n)

    def reconfirms(self, rule: str = FISHER_RULE) -> bool:
        """Whether this gap's efficacy stats pass `rule`. Fisher reads the flat stats; C23 reads efficacy["c23_paired"],
        harness.efficacy's report of the pairs, whose `passes` holds the rule's thresholds."""
        if rule == FISHER_RULE:
            return self.passes_efficacy()
        if rule != PAIRED_RULE:
            raise SchemaError("%s: unknown efficacy rule %r; use one of %s" % (self.gap_id, rule, EFFICACY_RULES))
        try:
            return bool(self.efficacy["c23_paired"]["passes"])
        except (KeyError, TypeError) as exc:
            raise SchemaError("%s: no paired efficacy report: %s" % (self.gap_id, exc))

    @property
    def attributable_share(self) -> float:
        """1 - p_nbhd/p_in. PRD 10.3."""
        p_in = float(self.efficacy["fail_rate_in"])
        p_nbhd = float(self.efficacy["fail_rate_neighbourhood"])
        return 1.0 - (p_nbhd / p_in) if p_in > 0 else 0.0
