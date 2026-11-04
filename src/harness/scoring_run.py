"""One scoring run: Step 8's `score-v1` (docs/steps/08-seal-generate-score.md), and the dry runs that test it.

    PYTHONPATH=src python -m harness.scoring_run --directives DIR [...] --key KEY --salt SALT --commitment FILE \
        --manifests M.json [...] --routes R.jsonl [...] --efficacy-rule prd_9_1 --label TEXT --output OUT.json

Reads the files `discovery.emit_directives` wrote and the key, checks the commitment first, refuses a directive off
the fixed budget or claiming a rollout outside the scored pool, then writes one report: per-gap efficacy on this pool,
every directive's score, best and median across dictionaries (C34), PRD 13.1's two conditions. It holds no predicate
and no salt. It refuses to overwrite a report, because a scoring run happens once and any later one is post hoc.

Readings pinned here, pending the preregistration's sign-off:
1. Condition 1's "method" means an activation method, since a baseline has no variant. The report still lists every
   directive that recovered a control gap.
2. Condition 2 is `evaluated` only when every baseline in harness.schema.BASELINES emitted a directive
   (PREREGISTRATION.md open item 8). Its arithmetic is reported either way.
3. `--dictionary` keeps one dictionary per SAE method for condition 2 (open item 3); without it the maxima run over
   all of them, and a name that matches no emitted directive stops the run. A dictionary with `counts` false never
   enters condition 2, as in dev_eval; `spread` reports it under `uncounted`.
4. A key that states `dry_run` stamps the report, and refuses a label without "DEV DRY RUN", so the label cannot depend
   only on the command line.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import median
from typing import Any, Sequence

from .bootstrap import advantage, mean_best_jaccard
from .efficacy import outcomes_by_route
from .schema import BASELINES, EFFICACY_RULES, Directive, Gap, SchemaError
from .scoring import ScoringReport, harness_is_valid, require_budget, score
from .seal import commitment, gaps_from_key, key_is_dry_run, load_key, verify

ACTIVATION, BASELINE = "activation", "baseline"
DRY_RUN_MARK = "DEV DRY RUN"
SPREAD_READING = "the best axis is chosen using the key"


@dataclass
class Emitted:
    label: str
    family: str
    kind: str
    dictionary: str | None
    counts: bool
    directive: Directive


def load_emitted(directories: Sequence[Path]) -> list[Emitted]:
    emitted = []
    for path in sorted(path for directory in directories for path in Path(directory).glob("*.json")):
        raw = json.loads(path.read_text())
        directive = Directive.from_dict(raw["directive"])
        if raw["directive"].get("budget_m") is None:
            raise SchemaError(f"{path.name}: the directive states no budget_m")
        require_budget(directive)
        emitted.append(Emitted(path.stem, raw["family"], raw["kind"], raw["dictionary"], raw["counts"], directive))
    if not emitted:
        raise ValueError(f"no directives in {directories}")
    return emitted


def load_pool(manifests: Sequence[Path], routes: Sequence[Path]) -> tuple[list[dict[str, Any]], dict[str, bool]]:
    manifest = [entry for path in manifests for entry in json.loads(Path(path).read_text())]
    rows = [json.loads(line) for path in routes for line in Path(path).read_text().splitlines() if line.strip()]
    failed = outcomes_by_route(rows)
    listed = {str(entry["id"]) for entry in manifest}
    if len(listed) != len(manifest):
        raise ValueError("a route id appears twice in the manifests")
    if failed.keys() - listed:
        raise ValueError(f"scored routes outside the manifests: {sorted(failed.keys() - listed)[:5]}")
    return manifest, failed


def require_scored_members(emitted: Sequence[Emitted], failed: dict[str, bool]) -> None:
    """A rollout outside the pool would score weight 0 in the bootstrap without any error, so it stops the run here."""
    for item in emitted:
        stray = {member for axis in item.directive.axes for member in axis.rollouts} - failed.keys()
        if stray:
            raise ValueError(f"{item.label} claims rollouts with no outcome in this pool: {sorted(stray)[:5]}")


def gap_row(gap: Gap, failures: int) -> dict[str, Any]:
    """Counts only: a report goes out before the key is revealed, and a list of a gap's route ids would reveal part of it."""
    lost = len(gap.efficacy.get("routes_without_outcome", []))
    return {"tier": gap.tier, "decoy": gap.is_decoy, "key_size": len(gap.failing_rollouts),
            "slice_size": len(gap.slice_rollouts), "catch_all": len(gap.failing_rollouts) / max(1, failures),
            "efficacy": {**gap.efficacy, "routes_without_outcome": lost}}


def method_row(item: Emitted, report: ScoringReport, real: Sequence[Gap]) -> dict[str, Any]:
    return {"family": item.family, "kind": item.kind, "dictionary": item.dictionary, "counts": item.counts,
            "preprocessing": item.directive.preprocessing, "n_axes": report.n_axes,
            "best_jaccard": {gap.gap_id: mean_best_jaccard(item.directive, [gap]) for gap in real},
            "score": asdict(report)}


def spread(emitted: Sequence[Emitted], methods: dict[str, Any], real: Sequence[Gap]) -> dict[str, Any]:
    """C34: an axis score is read as best and median across dictionaries, and the best is chosen using the key.
    Dictionaries with `counts` false are summarised apart, so a variant that never counts still has a best and median."""
    dictionaries = [item for item in emitted if item.dictionary is not None]
    return {**spread_rows([item for item in dictionaries if item.counts], methods, real),
            "uncounted": spread_rows([item for item in dictionaries if not item.counts], methods, real)}


def spread_rows(emitted: Sequence[Emitted], methods: dict[str, Any], real: Sequence[Gap]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for item in emitted:
        name = f"{item.family}@{item.directive.preprocessing}"
        row = out.setdefault(name, {gap.gap_id: [] for gap in real})
        for gap in real:
            row[gap.gap_id].append(methods[item.label]["best_jaccard"][gap.gap_id])
    return {name: {gap_id: {"best": max(values), "median": median(values), "dictionaries": len(values)}
                   for gap_id, values in row.items()} for name, row in out.items()}


def condition_1(emitted: Sequence[Emitted], reports: dict[str, ScoringReport], gaps: Sequence[Gap]) -> dict[str, Any]:
    activation = {item.label: reports[item.label] for item in emitted if item.kind == ACTIVATION}
    by_rule = {}
    for rule in EFFICACY_RULES:
        valid, reason = harness_is_valid(activation, gaps, efficacy_rule=rule)
        by_rule[rule] = {"valid": valid, "reason": reason,
                         "t2_reconfirming": sorted(g.gap_id for g in gaps if not g.is_decoy and g.efficacy
                                                   and g.tier == "T2_interactional" and g.reconfirms(rule))}
    recovered = {item.label: [m.gap_id for m in reports[item.label].matches if m.matched and m.tier == "T0_control"]
                 for item in emitted}
    return {"by_rule": by_rule, "t0_recovered_by": {label: found for label, found in recovered.items() if found}}


def condition_2(emitted: Sequence[Emitted], gaps: Sequence[Gap], base_of: dict[str, str], dictionary: str | None,
                replicates: int) -> dict[str, Any]:
    if dictionary is not None and all(item.dictionary != dictionary for item in emitted):
        raise ValueError(f"--dictionary {dictionary} matches no emitted directive")
    used = [item for item in emitted if item.counts and (dictionary is None or item.dictionary in (None, dictionary))]
    activation = {item.label: item.directive for item in used if item.kind == ACTIVATION}
    baselines = {item.label: item.directive for item in used if item.kind == BASELINE}
    missing = sorted(set(BASELINES) - {directive.method for directive in baselines.values()})
    report = advantage(activation, baselines, gaps, base_of, replicates=replicates)
    return {"evaluated": not missing, "missing_baselines": missing, "dictionary": dictionary,
            "activation": sorted(activation), "baselines": sorted(baselines),
            "arithmetic": {**asdict(report), "holds": report.holds}}


def scoring_report(emitted: Sequence[Emitted], key_gaps: Sequence[dict[str, Any]], manifest: list[dict[str, Any]],
                   failed: dict[str, bool], dictionary: str | None, replicates: int) -> dict[str, Any]:
    require_scored_members(emitted, failed)
    gaps = gaps_from_key(key_gaps, manifest, failed)
    real = [gap for gap in gaps if not gap.is_decoy]
    reports = {item.label: score(item.directive, gaps) for item in emitted}
    methods = {item.label: method_row(item, reports[item.label], real) for item in emitted}
    base_of = {str(entry["id"]): str(entry["base_id"]) for entry in manifest if str(entry["id"]) in failed}
    failures = sum(failed.values())
    return {"pool": {"rollouts": len(failed), "failures": failures, "manifest_entries": len(manifest),
                     "variants": sorted({item.directive.preprocessing for item in emitted})},
            "gaps": {gap.gap_id: gap_row(gap, failures) for gap in gaps},
            "methods": methods, "spread": spread(emitted, methods, real), "spread_reading": SPREAD_READING,
            "condition_1": condition_1(emitted, reports, gaps),
            "condition_2": condition_2(emitted, gaps, base_of, dictionary, replicates)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--directives", type=Path, nargs="+", required=True)
    parser.add_argument("--key", type=Path, required=True)
    parser.add_argument("--salt", type=Path, required=True)
    parser.add_argument("--commitment", type=Path, required=True)
    parser.add_argument("--manifests", type=Path, nargs="+", required=True)
    parser.add_argument("--routes", type=Path, nargs="+", required=True, help="routes.jsonl files from score_routes.py")
    parser.add_argument("--efficacy-rule", choices=EFFICACY_RULES, required=True, help="the rule of record")
    parser.add_argument("--label", required=True, help="what this run is; heads the report and every printed line")
    parser.add_argument("--dictionary", help="the one dictionary per SAE method that enters condition 2")
    parser.add_argument("--replicates", type=int, default=10_000)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error(f"{args.output} exists: a scoring run happens once")
    if not verify(args.key, args.salt, args.commitment):
        raise SystemExit(f"{args.key} does not match {args.commitment}")
    dry_run = key_is_dry_run(args.key)
    if dry_run and DRY_RUN_MARK not in args.label:
        parser.error(f"{args.key} is a dry-run key, so --label must say {DRY_RUN_MARK}")
    manifest, failed = load_pool(args.manifests, args.routes)
    report = scoring_report(load_emitted(args.directives), load_key(args.key), manifest, failed, args.dictionary,
                            args.replicates)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"dry_run": dry_run, "label": args.label, "key_commitment": commitment(args.key, args.salt),
                                       "efficacy_rule_of_record": args.efficacy_rule, **report},
                                      indent=1, default=float) + "\n")
    print(f"{args.label}: {report['pool']['rollouts']} rollouts; "
          f"condition 1 under {args.efficacy_rule}: {report['condition_1']['by_rule'][args.efficacy_rule]['reason']}; "
          f"condition 2 evaluated: {report['condition_2']['evaluated']}")


if __name__ == "__main__":
    main()
