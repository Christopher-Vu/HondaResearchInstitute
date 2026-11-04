"""H1, planted-gap recovery on the pooled dev corpus (docs/research/experiments/h1-planted-gap-recovery/protocol.md).

    PYTHONPATH=src python -m discovery.dev_eval SHARD_DIR [...] --layer 10 --gap P4_camera_occlusion P7_camera_freeze
        P8_camera_latency --manifests 'configs/rollout/step4-dev-pool*.manifest.json' [--sae RUN_DIR ...] --output OUT.json

Every rollout with a driving outcome is read as its `driving_queries` frame means at --layer, so SAE rows, probe
residuals and activation statistics all see the same representation. Activation methods are M1 contrastive (raw and
capped at half of all failures) over each SAE run's latents, and M2 probe-residual; baselines are B2 taxonomy, B3
behavioural, B7's pool variant over the same latents, and B1 random, which is a summary of draws sized from M1's axes.
Without --sae only M2, B2 and B3 run. An SAE run whose layer differs from --layer is skipped with a note, and one
whose explained variance on these frame means is below 0.8 is reported but does not count.

Scoring is the only code that reads the sidecars' practice_gaps and role: the answer key for a gap is the failing
rollouts listing it. Methods receive rollouts built from activations, state, infractions and outcome, and B2 receives
only scenario, weather and town. Per gap and method the output holds the best axis's Jaccard with the key, its size,
its share of all failures and how many of its members are pilot slice versus pilot neighbourhood routes, then Claim A
and Claim B of the protocol with a base-route cluster bootstrap. Dev only: nothing here is a result (PRD 9.2).
"""
from __future__ import annotations

import argparse
import glob
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import torch

from baselines import behavioral
from baselines.activation_stats import ActivationStatsConfig, activation_stats_directive
from baselines.random_baseline import RandomBaselineConfig, score_averaged
from baselines.taxonomy import TaxonomyConfig, taxonomy_directive
from discovery import probe_residual, sae
from discovery.contrastive import ContrastiveConfig, Rollout, contrastive_directive
from harness.bootstrap import MARGIN, mean_best_jaccard
from harness.failure_time import failure_step
from harness.schema import Directive, Gap
from harness.scoring import MATCH_THRESHOLD, jaccard, score

ACTIVATION, BASELINE = "activation", "baseline"
CATCH_ALL_CAP = 0.5
STALE_CHANGE = 1e-3
MIN_EXPLAINED_VARIANCE = 0.8
MIN_STABLE_SEEDS = 4
RANDOM_DRAWS = 200
BOOTSTRAP_REPLICATES = 2000
BOOTSTRAP_SEED = 20261031
MARGIN_TOLERANCE = 1e-9
SLICE_ROLE, NEIGHBOURHOOD_ROLE = "pilot_slice", "pilot_neighbourhood"
TAXONOMY_FIELDS = ("id", "scenario", "weather", "town")


@dataclass
class Shard:
    sidecar: Path
    meta: dict[str, Any]
    source: str

    @property
    def route_id(self) -> str:
        return str(self.meta["route_id"])


@dataclass
class Frames:
    """One rollout's layer-mean activations, (frames, hidden), with what the methods may know about its outcome."""
    rollout_id: str
    means: np.ndarray
    steps: np.ndarray
    failed: bool
    failure_step: int | None


@dataclass
class SaeInfo:
    run: str
    layer: int
    k: int
    seed: int
    explained_variance: float

    @property
    def counts(self) -> bool:
        return self.explained_variance >= MIN_EXPLAINED_VARIANCE


@dataclass
class MethodRun:
    family: str
    kind: str
    directive: Directive
    sae: SaeInfo | None = None

    @property
    def counts(self) -> bool:
        return self.sae is None or self.sae.counts

    @property
    def label(self) -> str:
        return self.family if self.sae is None else f"{self.family}@{self.sae.run}"


@dataclass
class ScoringContext:
    """What only scoring may use: who failed, and which pilot role each rollout had."""
    failing: set[str]
    roles: dict[str, str | None]


def load_shards(shard_dirs: list[Path]) -> list[Shard]:
    shards = [Shard(sidecar, meta, str(directory)) for directory in shard_dirs
              for sidecar in sorted(directory.glob("*.json"))
              if (meta := json.loads(sidecar.read_text()))["success"] is not None]
    shards.sort(key=lambda shard: shard.route_id)
    ids = [shard.route_id for shard in shards]
    repeated = sorted({route_id for route_id in ids if ids.count(route_id) > 1})
    if repeated:
        raise ValueError(f"route ids appear in more than one shard: {repeated[:5]}")
    return shards


def read_frames(shard: Shard, layer: int) -> Frames:
    with np.load(shard.sidecar.with_suffix(".npz")) as archive:
        means = archive["driving_queries"][:, layer].astype(np.float32)
        steps = archive["step"].astype(np.int64)
        failed_at = failure_step(shard.meta, archive)
    return Frames(shard.route_id, means, steps, not shard.meta["success"], failed_at)


def load_sae(run: Path, device: torch.device) -> tuple[sae.TopKSae, dict[str, Any]]:
    saved = torch.load(run / "sae.pt", map_location=device, weights_only=False)
    state = saved["state"]
    model = sae.TopKSae(state["encoder"].shape[1], state["encoder"].shape[0], saved["config"]["k"], state["pre_bias"])
    model.load_state_dict(state)
    return model.to(device).eval(), saved["config"]


@dataclass
class VarianceTally:
    """Explained variance, 1 - SSE/SST, accumulated over rollouts so the frames never sit in memory together."""
    squared_error: float = 0.0
    sum_squares: float = 0.0
    count: int = 0
    total: torch.Tensor | None = None

    def add(self, inputs: torch.Tensor, reconstruction: torch.Tensor) -> None:
        inputs = inputs.double()
        self.squared_error += float(((inputs - reconstruction.double()) ** 2).sum())
        self.sum_squares += float((inputs ** 2).sum())
        self.count += len(inputs)
        self.total = inputs.sum(dim=0) if self.total is None else self.total + inputs.sum(dim=0)

    @property
    def explained(self) -> float:
        spread = self.sum_squares - float((self.total ** 2).sum()) / self.count
        return 1 - self.squared_error / max(spread, 1e-12)


def stale_frames(means: np.ndarray) -> np.ndarray:
    """1 where a frame mean barely differs from the previous logged frame's (H2: a frozen input), else 0."""
    change = np.linalg.norm(np.diff(means, axis=0), axis=1) / np.maximum(np.linalg.norm(means[:-1], axis=1), 1e-12)
    return np.concatenate([[0.0], (change < STALE_CHANGE).astype(np.float64)])


@torch.no_grad()
def encode_frames(model: sae.TopKSae, frames: list[Frames], device: torch.device,
                  stale_latent: bool = False) -> tuple[list[Rollout], float]:
    """Each rollout's per-frame latents, and the SAE's explained variance on these normalised frame means.

    With `stale_latent`, one more latent is appended: stale_frames of the raw frame means."""
    tally, rollouts = VarianceTally(), []
    for item in frames:
        inputs = sae.normalise(torch.from_numpy(item.means).to(device))
        reconstruction, latents, _pre = model(inputs)
        tally.add(inputs, reconstruction)
        values = latents.cpu().numpy()
        if stale_latent:
            values = np.column_stack([values, stale_frames(item.means)]).astype(values.dtype)
        rollouts.append(Rollout(item.rollout_id, values, item.steps, item.failed, item.failure_step))
    return rollouts, tally.explained


def contrastive_variants(rollouts: list[Rollout], layer: int) -> tuple[Directive, Directive]:
    label = f"driving_queries_L{layer}"
    raw, _ = contrastive_directive(rollouts, ContrastiveConfig(), layer=label)
    capped, _ = contrastive_directive(rollouts, ContrastiveConfig(max_failure_share=CATCH_ALL_CAP), layer=label)
    return raw, capped


def sae_methods(rollouts: list[Rollout], info: SaeInfo, layer: int) -> list[MethodRun]:
    raw, capped = contrastive_variants(rollouts, layer)
    episodes = {rollout.rollout_id: rollout.latents for rollout in rollouts}
    failing = {rollout.rollout_id for rollout in rollouts if rollout.failed}
    pool = activation_stats_directive(episodes, episodes, failing, ActivationStatsConfig(variant="B"))
    return [MethodRun("M1_raw", ACTIVATION, raw, info), MethodRun("M1_capped", ACTIVATION, capped, info),
            MethodRun("B7_pool", BASELINE, pool, info)]


def run_saes(runs: list[Path], frames: list[Frames], layer: int, device: torch.device, stale_latent: bool = False
             ) -> tuple[list[MethodRun], list[SaeInfo], list[dict[str, str]]]:
    methods, infos, skipped = [], [], []
    for run in runs:
        if not (run / "sae.pt").is_file():
            skipped.append({"run": str(run), "reason": "no sae.pt"})
            continue
        model, config = load_sae(run, device)
        if config["layer"] != layer:
            skipped.append({"run": str(run), "reason": f"SAE layer {config['layer']} is not --layer {layer}"})
            continue
        rollouts, explained = encode_frames(model, frames, device, stale_latent)
        info = SaeInfo(str(run), config["layer"], config["k"], config["seed"], explained)
        infos.append(info)
        methods += sae_methods(rollouts, info, layer)
    return methods, infos, skipped


def probe_run(shards: list[Shard], layer: int) -> MethodRun:
    rollouts = [rollout for shard in shards
                if (rollout := probe_residual.load_shard(shard.sidecar, "driving_queries", layer))]
    return MethodRun("M2_probe_residual", ACTIVATION,
                     probe_residual.probe_residual_directive(rollouts, probe_residual.ProbeResidualConfig()))


def non_sae_methods(shards: list[Shard], layer: int, records: list[dict[str, Any]]) -> list[MethodRun]:
    behaviour = [rollout for shard in shards if (rollout := behavioral.load_shard(shard.sidecar))]
    return [probe_run(shards, layer),
            MethodRun("B2_taxonomy", BASELINE, taxonomy_directive(records, TaxonomyConfig())),
            MethodRun("B3_behavioral", BASELINE,
                      behavioral.behavioral_directive(behaviour, behavioral.BehavioralConfig()))]


def taxonomy_records(manifest_paths: list[str], failed: dict[str, bool]) -> list[dict[str, Any]]:
    """B2 sees scenario, weather and town only; the manifests also carry the key and the sensor fault."""
    entries = {str(entry["id"]): entry for path in manifest_paths for entry in json.loads(Path(path).read_text())}
    return [{**{name: entries[route_id][name] for name in TAXONOMY_FIELDS}, "id": route_id, "failed": did_fail}
            for route_id, did_fail in sorted(failed.items()) if route_id in entries]


def gap_keys(shards: list[Shard], gap_ids: list[str]) -> list[Gap]:
    return [Gap(gap_id, "T0_control",
                {shard.route_id for shard in shards
                 if shard.meta["success"] is False and gap_id in shard.meta.get("practice_gaps", [])})
            for gap_id in gap_ids]


def axis_record(axis: Any, key: set[str], context: ScoringContext) -> dict[str, Any]:
    members = axis.rollouts
    roles = [context.roles.get(member) for member in members]
    return {"axis_id": axis.axis_id, "best_jaccard": jaccard(members, key), "axis_size": len(members),
            "share_of_failures": len(members & context.failing) / max(1, len(context.failing)),
            "in_key": len(members & key), "pilot_slice": roles.count(SLICE_ROLE),
            "pilot_neighbourhood": roles.count(NEIGHBOURHOOD_ROLE),
            "other": sum(role not in (SLICE_ROLE, NEIGHBOURHOOD_ROLE) for role in roles)}


def gap_record(directive: Directive, gap: Gap, context: ScoringContext) -> dict[str, Any]:
    """The best axis against one gap's key, and whether any axis recovers it (Claim A's test)."""
    axes = [axis_record(axis, gap.failing_rollouts, context) for axis in directive.axes]
    if not axes:
        return {"axis_id": None, "best_jaccard": 0.0, "axis_size": 0, "share_of_failures": 0.0, "in_key": 0,
                "pilot_slice": 0, "pilot_neighbourhood": 0, "other": 0, "recovers": False}
    recovers = any(a["best_jaccard"] >= MATCH_THRESHOLD and a["share_of_failures"] <= CATCH_ALL_CAP for a in axes)
    return {**max(axes, key=lambda a: a["best_jaccard"]), "recovers": recovers}


def summary(report: Any) -> dict[str, Any]:
    return {"mean_best_jaccard": report.mean_best_jaccard, "precision_at_m": report.precision_at_m,
            "n_axes": report.n_axes, "matches": [asdict(match) for match in report.matches]}


def best_run(runs: list[MethodRun], results: dict[str, Any], gap_id: str) -> MethodRun:
    return max(runs, key=lambda run: results[run.label]["gaps"][gap_id]["best_jaccard"])


def best_weighted(runs: list[MethodRun], gap: Gap, weight: dict[str, float] | None) -> float:
    return max(mean_best_jaccard(run.directive, [gap], weight) for run in runs)


def bootstrap_deltas(runs: list[MethodRun], gaps: list[Gap], base_of: dict[str, str], replicates: int
                     ) -> dict[str, np.ndarray]:
    """Per gap, best activation minus best baseline over base-route resamples, both maxima re-taken every time."""
    activation = [run for run in runs if run.kind == ACTIVATION]
    baselines = [run for run in runs if run.kind == BASELINE]
    bases = sorted(set(base_of.values()))
    rollouts_of: dict[str, list[str]] = {}
    for rollout, base in base_of.items():
        rollouts_of.setdefault(base, []).append(rollout)
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    deltas = {gap.gap_id: np.empty(replicates) for gap in gaps}
    for replicate in range(replicates):
        counts = np.bincount(rng.integers(0, len(bases), len(bases)), minlength=len(bases))
        weight = {r: float(c) for base, c in zip(bases, counts) if c for r in rollouts_of[base]}
        for gap in gaps:
            deltas[gap.gap_id][replicate] = best_weighted(activation, gap, weight) - best_weighted(baselines, gap, weight)
    return deltas


def seed_stability(winner: MethodRun, all_runs: list[MethodRun], results: dict[str, Any], gap_id: str,
                   baseline_jaccard: float) -> dict[str, int] | None:
    """Of the seeds at the winner's layer and k, how many counting runs beat the best baseline; None for non-SAE."""
    if winner.sae is None:
        return None
    peers = [run for run in all_runs if run.family == winner.family and run.sae is not None
             and (run.sae.layer, run.sae.k) == (winner.sae.layer, winner.sae.k)]
    beating = sum(run.counts and results[run.label]["gaps"][gap_id]["best_jaccard"] > baseline_jaccard
                  for run in peers)
    return {"seeds_beating": beating, "seeds_total": len(peers)}


def claim_b(winner: dict[str, Any], baseline_jaccard: float, catch_all: float, interval: tuple[float, float],
            stability: dict[str, int] | None) -> dict[str, Any]:
    over_baseline = winner["best_jaccard"] - baseline_jaccard >= MARGIN - MARGIN_TOLERANCE
    over_catch_all = winner["best_jaccard"] - catch_all >= MARGIN - MARGIN_TOLERANCE
    margin = over_baseline and over_catch_all and interval[0] > 0
    not_catch_all = winner["share_of_failures"] <= CATCH_ALL_CAP
    stable = None if stability is None else stability["seeds_beating"] >= MIN_STABLE_SEEDS
    return {"margin": margin, "not_catch_all": not_catch_all, "stable": stable, "seed_counts": stability,
            "holds": margin and not_catch_all and stable is not False}


def family_bests(counting: list[MethodRun], results: dict[str, Any], gap_id: str) -> dict[str, Any]:
    bests = {}
    for family in sorted({run.family for run in counting}):
        run = best_run([other for other in counting if other.family == family], results, gap_id)
        bests[family] = {"method": run.label, **results[run.label]["gaps"][gap_id]}
    return bests


def gap_verdict(gap: Gap, all_runs: list[MethodRun], results: dict[str, Any], deltas: np.ndarray,
                failures: int) -> dict[str, Any]:
    counting = [run for run in all_runs if run.counts]
    activation = [run for run in counting if run.kind == ACTIVATION]
    winner = best_run(activation, results, gap.gap_id)
    rival = best_run([run for run in counting if run.kind == BASELINE], results, gap.gap_id)
    record = results[winner.label]["gaps"][gap.gap_id]
    rival_jaccard = results[rival.label]["gaps"][gap.gap_id]["best_jaccard"]
    catch_all = len(gap.failing_rollouts) / max(1, failures)
    interval = (float(np.percentile(deltas, 2.5)), float(np.percentile(deltas, 97.5)))
    stability = seed_stability(winner, all_runs, results, gap.gap_id, rival_jaccard)
    return {"key_size": len(gap.failing_rollouts), "catch_all": catch_all,
            "best_activation": {"method": winner.label, **record},
            "best_baseline": {"method": rival.label, **results[rival.label]["gaps"][gap.gap_id]},
            "delta": record["best_jaccard"] - rival_jaccard, "interval": list(interval),
            "claim_a": any(results[run.label]["gaps"][gap.gap_id]["recovers"] for run in activation),
            "claim_b": claim_b(record, rival_jaccard, catch_all, interval, stability),
            "best_by_family": family_bests(counting, results, gap.gap_id)}


def random_floors(runs: list[MethodRun], failing: set[str], gaps: list[Gap]) -> list[dict[str, Any]]:
    """B1 per SAE run, sized from that run's M1 axes; one fallback draw set when no run supplies axes."""
    sources = [(run.sae.run, run.directive) for run in runs if run.family == "M1_raw" and run.sae is not None]
    floors = []
    for source, directive in sources or [("fallback", None)]:
        sizes = [len(axis.rollouts) for axis in directive.axes] if directive else []
        sizes = sizes or [max(1, len(failing) // 10)]
        draws, _ = score_averaged(sorted(failing), gaps, RandomBaselineConfig(axis_sizes=sizes, n_draws=RANDOM_DRAWS))
        floors.append({"sizes_from": source, **draws})
    return floors


def corpus_counts(shards: list[Shard], gaps: list[Gap], manifest_records: int) -> dict[str, Any]:
    def counts(subset: list[Shard]) -> dict[str, Any]:
        return {"rollouts": len(subset), "failures": sum(shard.meta["success"] is False for shard in subset),
                "key": {gap.gap_id: len({s.route_id for s in subset} & gap.failing_rollouts) for gap in gaps}}
    sources = sorted({shard.source for shard in shards})
    return {**counts(shards), "manifest_records": manifest_records,
            "sources": {source: counts([s for s in shards if s.source == source]) for source in sources}}


def evaluate(shard_dirs: list[Path], layer: int, sae_runs: list[Path], gap_ids: list[str], manifests: list[str],
             device: torch.device, replicates: int = BOOTSTRAP_REPLICATES, stale_latent: bool = False
             ) -> dict[str, Any]:
    shards = load_shards(shard_dirs)
    frames = [read_frames(shard, layer) for shard in shards]
    records = taxonomy_records(manifests, {s.route_id: not s.meta["success"] for s in shards})
    sae_method_runs, infos, skipped = run_saes(sae_runs, frames, layer, device, stale_latent)
    runs = sae_method_runs + non_sae_methods(shards, layer, records)
    gaps = gap_keys(shards, gap_ids)
    context = ScoringContext({s.route_id for s in shards if s.meta["success"] is False},
                             {s.route_id: s.meta.get("role") for s in shards})
    results = {run.label: {"family": run.family, "kind": run.kind, "counts": run.counts,
                           "sae": run.sae.run if run.sae else None, "score": summary(score(run.directive, gaps)),
                           "gaps": {gap.gap_id: gap_record(run.directive, gap, context) for gap in gaps}}
               for run in runs}
    deltas = bootstrap_deltas([run for run in runs if run.counts], gaps,
                              {s.route_id: str(s.meta["base_id"]) for s in shards}, replicates)
    return {"layer": layer, "stale_latent": stale_latent, "corpus": corpus_counts(shards, gaps, len(records)),
            "saes": [{**asdict(info), "counts": info.counts} for info in infos], "skipped_saes": skipped,
            "methods": results, "B1_random": random_floors(runs, context.failing, gaps),
            "gaps": {gap.gap_id: gap_verdict(gap, runs, results, deltas[gap.gap_id], len(context.failing))
                     for gap in gaps}}


def yes(flag: bool | None) -> str:
    return "n/a" if flag is None else "yes" if flag else "no"


def format_gap(gap_id: str, verdict: dict[str, Any]) -> str:
    lines = [f"{gap_id}: key {verdict['key_size']}, catch-all {verdict['catch_all']:.3f}",
             f"  {'method':<20}{'best J':>8}{'size':>6}{'share':>7}{'slice':>7}{'nbhd':>6}{'other':>7}"]
    for family, row in verdict["best_by_family"].items():
        lines.append(f"  {family:<20}{row['best_jaccard']:>8.3f}{row['axis_size']:>6}{row['share_of_failures']:>7.2f}"
                     f"{row['pilot_slice']:>7}{row['pilot_neighbourhood']:>6}{row['other']:>7}")
    low, high = verdict["interval"]
    rules = verdict["claim_b"]
    lines.append(f"  delta {verdict['delta']:+.3f} [{low:+.3f}, {high:+.3f}]  claim A {yes(verdict['claim_a'])}  "
                 f"claim B {yes(rules['holds'])} (margin {yes(rules['margin'])}, not catch-all "
                 f"{yes(rules['not_catch_all'])}, stable {yes(rules['stable'])})")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("shards", type=Path, nargs="+")
    parser.add_argument("--layer", type=int, default=10)
    parser.add_argument("--sae", type=Path, nargs="*", default=[], help="SAE run directories; none runs M2, B2, B3")
    parser.add_argument("--gap", nargs="+", required=True, help="practice gaps that passed efficacy")
    parser.add_argument("--manifests", nargs="+", required=True, help="manifests (globs allowed) for B2's metadata")
    parser.add_argument("--stale-latent", action="store_true", help="append H2's stale-frame latent to every SAE's")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    manifests = sorted({path for pattern in args.manifests for path in glob.glob(pattern)})
    result = evaluate(args.shards, args.layer, args.sae, args.gap, manifests, device,
                      stale_latent=args.stale_latent)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, default=str) + "\n")
    for skipped in result["skipped_saes"]:
        print(f"skipped {skipped['run']}: {skipped['reason']}")
    for gap_id, verdict in result["gaps"].items():
        print(format_gap(gap_id, verdict))


if __name__ == "__main__":
    main()
