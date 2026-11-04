"""H16: B7 variant A against our methods over H12's dictionaries, and the evidence the stop rule reads.

    PYTHONPATH=src python docs/research/experiments/h16-b7-rollout-free/score.py SHARD_DIR [...] \\
        --training results/savio/h16/training --sae results/savio/h12/sae/L10_* --gap P19_wide_invading_turn ... \\
        [--reproduce docs/research/data/h12_layer10_plain.json] [--stale-latent] --output OUT.json

Variant A's statistics come from the training frames and variant B's from the pool; both merge and take members on the
pool (docs/steps/b7-gap-signal.md). Every score is best and median across dictionaries (CONFLICTS.md C34). With
--stale-latent the output is post hoc: it holds no stop-rule evidence, and read_rule.py refuses it.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np
import torch

from baselines.activation_stats import ActivationStatsConfig, activation_stats_directive, latent_scores
from baselines.b7_variant_a import GapEvidence, read_route_list, route_key, variant_a_tested
from discovery import dev_eval
from discovery.dev_eval import ACTIVATION, BASELINE, Frames, MethodRun, SaeInfo, ScoringContext
from harness.schema import Gap

LAYER = 10
B7_FAMILIES = {"A": "B7_A", "pool": "B7_pool"}
METHOD_FAMILIES = ("M1_raw", "M1_capped")
POST_HOC_LABEL = "post hoc: H2's frozen-input latent is not in the frozen B7 spec, and the stop rule never reads it"


def read_training_frames(directory: Path) -> tuple[list[Frames], list[str]]:
    """Listed routes that were captured, as frames, and the listed routes that were not."""
    frames, missing = [], []
    for route in read_route_list():
        path = directory / f"{route_key(route)}.npz"
        if not path.exists():
            missing.append(route)
            continue
        with np.load(path) as archive:
            frames.append(Frames(route_key(route), archive["driving_queries"].astype(np.float32),
                                 archive["frame"].astype(np.int64), False, None))
    return frames, missing


def dictionary_runs(run: Path, pool: list[Frames], training: list[Frames], device: torch.device, stale_latent: bool
                    ) -> tuple[list[MethodRun], dict[str, Any]]:
    """M1 raw and capped, B7 variant A and B7-pool, all on one dictionary's latents."""
    model, config = dev_eval.load_sae(run, device)
    if config["layer"] != LAYER:
        raise ValueError(f"{run} is layer {config['layer']}, not {LAYER}")
    pool_rollouts, pool_variance = dev_eval.encode_frames(model, pool, device, stale_latent)
    training_rollouts, training_variance = dev_eval.encode_frames(model, training, device, stale_latent)
    info = SaeInfo(str(run), LAYER, config["k"], config["seed"], pool_variance)
    a_info = SaeInfo(str(run), LAYER, config["k"], config["seed"], min(pool_variance, training_variance))
    raw, capped = dev_eval.contrastive_variants(pool_rollouts, LAYER)
    episodes = {rollout.rollout_id: rollout.latents for rollout in pool_rollouts}
    stats = {rollout.rollout_id: rollout.latents for rollout in training_rollouts}
    failing = {rollout.rollout_id for rollout in pool_rollouts if rollout.failed}
    variant_a = activation_stats_directive(stats, episodes, failing, ActivationStatsConfig(variant="A"))
    variant_b = activation_stats_directive(episodes, episodes, failing, ActivationStatsConfig(variant="B"))
    row = {**asdict(info), "training_explained_variance": training_variance,
           "latents_surviving_on_training": int(latent_scores(stats, ActivationStatsConfig(variant="A")).latent_ids.size)}
    return [MethodRun("M1_raw", ACTIVATION, raw, info), MethodRun("M1_capped", ACTIVATION, capped, info),
            MethodRun("B7_A", BASELINE, variant_a, a_info), MethodRun("B7_pool", BASELINE, variant_b, info)], row


def jaccards(runs: list[MethodRun], results: dict[str, Any], gap_id: str) -> list[float]:
    return [results[run.label]["gaps"][gap_id]["best_jaccard"] for run in runs]


def best_of_each_dictionary(runs: list[MethodRun], results: dict[str, Any], gap_id: str) -> list[float]:
    """For each dictionary, the better of its methods' best axes."""
    by_dictionary: dict[str, float] = {}
    for run, value in zip(runs, jaccards(runs, results, gap_id)):
        assert run.sae is not None
        by_dictionary[run.sae.run] = max(by_dictionary.get(run.sae.run, 0.0), value)
    return list(by_dictionary.values())


def spread(values: list[float]) -> dict[str, float]:
    return {"best": max(values), "median": float(np.median(values)), "lowest": min(values), "dictionaries": len(values)}


def gap_evidence(gap: Gap, b7: list[MethodRun], methods: list[MethodRun], results: dict[str, Any], failures: int,
                 bases: dict[str, str], replicates: int) -> tuple[GapEvidence, dict[str, Any]]:
    """Claim B's test with B7 as the only rival, and what the rule reads about this gap on one variant."""
    gap_id = gap.gap_id
    winner = dev_eval.best_run(methods, results, gap_id)
    rival = dev_eval.best_run(b7, results, gap_id)
    winner_record, rival_record = results[winner.label]["gaps"][gap_id], results[rival.label]["gaps"][gap_id]
    deltas = dev_eval.bootstrap_deltas(methods + b7, [gap], bases, replicates)[gap_id]
    interval = (float(np.percentile(deltas, 2.5)), float(np.percentile(deltas, 97.5)))
    stability = dev_eval.seed_stability(winner, methods, results, gap_id, rival_record["best_jaccard"])
    claim_b = dev_eval.claim_b(winner_record, rival_record["best_jaccard"], len(gap.failing_rollouts) / max(1, failures),
                               interval, stability)
    b7_spread, method_spread = spread(jaccards(b7, results, gap_id)), spread(best_of_each_dictionary(methods, results, gap_id))
    evidence = GapEvidence(any(results[run.label]["gaps"][gap_id]["recovers"] for run in b7), b7_spread["best"],
                           b7_spread["median"], any(results[run.label]["gaps"][gap_id]["recovers"] for run in methods),
                           method_spread["best"], method_spread["median"], claim_b["holds"])
    details = {"best_axis_chosen_using_the_key": True, "b7": b7_spread, "methods": method_spread,
               "best_b7_axis": {"method": rival.label, **rival_record},
               "best_method_axis": {"method": winner.label, **winner_record}, "interval": list(interval), "claim_b": claim_b}
    return evidence, details


def stopwatch_jaccard(gap: Gap, pool: list[Frames], failing: set[str]) -> float:
    """The best N longest failing rollouts against the key: what a clock alone reaches (H3's audit)."""
    longest = sorted((item for item in pool if item.rollout_id in failing), key=lambda item: -len(item.means))
    key, best, hits = gap.failing_rollouts, 0.0, 0
    for size, item in enumerate(longest, start=1):
        hits += item.rollout_id in key
        best = max(best, hits / (size + len(key) - hits))
    return best


def reproduction(stored_path: Path, results: dict[str, Any], gaps: list[Gap]) -> dict[str, Any]:
    """How far this run's M1 and B7-pool sit from the numbers already stored, on the same rollouts and dictionaries."""
    stored = json.loads(stored_path.read_text())["methods"]
    differences = [abs(results[label]["gaps"][gap.gap_id]["best_jaccard"] - stored[label]["gaps"][gap.gap_id]["best_jaccard"])
                   for label in results if label in stored for gap in gaps]
    return {"compared": len(differences), "worst_difference": max(differences, default=None)}


def method_results(runs: list[MethodRun], gaps: list[Gap], context: ScoringContext) -> dict[str, Any]:
    return {run.label: {"family": run.family, "counts": run.counts, "sae": run.sae.run if run.sae else None,
                        "gaps": {gap.gap_id: dev_eval.gap_record(run.directive, gap, context) for gap in gaps}}
            for run in runs}


def read_variant(variant: str, runs: list[MethodRun], gaps: list[Gap], results: dict[str, Any], failures: int,
                 bases: dict[str, str], replicates: int) -> tuple[dict[str, dict], dict[str, Any]]:
    b7 = [run for run in runs if run.family == B7_FAMILIES[variant] and run.counts]
    methods = [run for run in runs if run.family in METHOD_FAMILIES and run.counts]
    if not b7 or not methods:
        return {}, {}
    pairs = {gap.gap_id: gap_evidence(gap, b7, methods, results, failures, bases, replicates) for gap in gaps}
    return ({gap_id: asdict(pair[0]) for gap_id, pair in pairs.items()},
            {gap_id: pair[1] for gap_id, pair in pairs.items()})


def evaluate(shard_dirs: list[Path], training_dir: Path, sae_runs: list[Path], gap_ids: list[str], device: torch.device,
             stale_latent: bool, reproduce: Path | None, replicates: int = dev_eval.BOOTSTRAP_REPLICATES) -> dict[str, Any]:
    shards = dev_eval.load_shards(shard_dirs)
    pool = [dev_eval.read_frames(shard, LAYER) for shard in shards]
    training, missing = read_training_frames(training_dir)
    gaps = dev_eval.gap_keys(shards, gap_ids)
    context = ScoringContext({s.route_id for s in shards if s.meta["success"] is False},
                             {s.route_id: s.meta.get("role") for s in shards})
    bases = {s.route_id: str(s.meta["base_id"]) for s in shards}
    runs, rows = [], []
    for run in sae_runs:
        methods, row = dictionary_runs(run, pool, training, device, stale_latent)
        runs += methods
        rows.append(row)
    results = method_results(runs, gaps, context)
    tested_a = variant_a_tested(len(training), sum(run.family == "B7_A" and run.counts for run in runs))
    evidence, details = {}, {}
    for variant in B7_FAMILIES:
        evidence[variant], details[variant] = read_variant(variant, runs, gaps, results, len(context.failing), bases, replicates)
    report = {"layer": LAYER, "stale_latent": stale_latent, "pool_rollouts": len(pool), "pool_failures": len(context.failing),
              "training_routes": len(training), "training_frames": sum(len(item.means) for item in training),
              "training_routes_missing": missing, "dictionaries": rows, "tested": {"A": tested_a, "pool": True},
              "details": details, "methods": results,
              "stopwatch": {gap.gap_id: stopwatch_jaccard(gap, pool, context.failing) for gap in gaps}}
    if reproduce is not None:
        report["reproduces_stored"] = reproduction(reproduce, results, gaps)
    return {**report, "label": POST_HOC_LABEL} if stale_latent else {**report, "evidence": evidence}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("shards", type=Path, nargs="+")
    parser.add_argument("--training", type=Path, required=True)
    parser.add_argument("--sae", type=Path, nargs="+", required=True)
    parser.add_argument("--gap", nargs="+", required=True)
    parser.add_argument("--stale-latent", action="store_true")
    parser.add_argument("--reproduce", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    report = evaluate(args.shards, args.training, args.sae, args.gap, device, args.stale_latent, args.reproduce)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, default=str) + "\n")


if __name__ == "__main__":
    main()
