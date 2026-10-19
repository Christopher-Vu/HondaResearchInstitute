"""Discovery on the dev pool, scored against the practice gaps that passed efficacy (Steps 6 and 7).

    PYTHONPATH=src python -m discovery.dev_eval SHARD_DIR [...] --sae RUN_DIR [...] --gap P4_camera_occlusion
        --manifests configs/rollout/step5-pilot-*.manifest.json --output OUT.json

For each SAE run (a directory holding sae.pt from discovery/sae.py), every rollout's driving-query tokens at the
run's layer are normalised, encoded, and reduced to per-frame latents (maximum over tokens). On those rollouts the
contrastive method, B7's pool variant ("B7-pool"), B1 (random, sized from the contrastive axes) and B2 (human
taxonomy over the manifests' metadata) each emit a directive, scored by harness.scoring against each named gap's
failing rollouts: the shards whose practice_gaps list the gap and whose outcome is a failure. Rollouts without an
outcome are left out. Dev only: the scores guide method development and are not results (PRD 9.2).
"""
from __future__ import annotations

import argparse
import glob
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np
import torch

from baselines.activation_stats import ActivationStatsConfig, activation_stats_directive
from baselines.random_baseline import RandomBaselineConfig, score_averaged
from baselines.taxonomy import TaxonomyConfig, taxonomy_directive
from discovery import sae
from discovery.contrastive import ContrastiveConfig, Rollout, contrastive_directive, frame_latents
from harness.failure_time import failure_step
from harness.schema import Gap
from harness.scoring import jaccard, score


def load_sae(run: Path, device: torch.device) -> tuple[sae.TopKSae, int]:
    saved = torch.load(run / "sae.pt", map_location=device, weights_only=False)
    state = saved["state"]
    model = sae.TopKSae(state["encoder"].shape[1], state["encoder"].shape[0], saved["config"]["k"], state["pre_bias"])
    model.load_state_dict(state)
    return model.to(device).eval(), saved["config"]["layer"]


@torch.no_grad()
def encode_rollouts(shard_dirs: list[Path], model: sae.TopKSae, layer: int, device: torch.device) -> list[Rollout]:
    rollouts = []
    for sidecar in sorted(path for directory in shard_dirs for path in directory.glob("*.json")):
        meta = json.loads(sidecar.read_text())
        with np.load(sidecar.with_suffix(".npz")) as archive:
            if meta["success"] is None or "driving_query_tokens" not in archive.files:
                continue
            position = list(archive["driving_query_token_layers"]).index(layer)
            tokens = torch.from_numpy(archive["driving_query_tokens"][:, position].astype(np.float32)).to(device)
            steps = archive["step"].astype(np.int64)
            failed_at = failure_step(meta, archive)
        _reconstruction, latents, _pre = model(sae.normalise(tokens))
        rollouts.append(Rollout(meta["route_id"], frame_latents(latents.cpu().numpy()), steps,
                                not meta["success"], failed_at))
    return rollouts


def gap_failures(shard_dirs: list[Path], gap_ids: list[str]) -> dict[str, set[str]]:
    failures: dict[str, set[str]] = {gap: set() for gap in gap_ids}
    for sidecar in (path for directory in shard_dirs for path in directory.glob("*.json")):
        meta = json.loads(sidecar.read_text())
        for gap in set(meta.get("practice_gaps", [])) & set(gap_ids):
            if meta["success"] is False:
                failures[gap].add(meta["route_id"])
    return failures


def records(manifest_paths: list[str], rollouts: list[Rollout]) -> list[dict[str, Any]]:
    entries = {entry["id"]: entry for path in manifest_paths for entry in json.loads(Path(path).read_text())}
    return [{**entries[rollout.rollout_id], "failed": rollout.failed} for rollout in rollouts
            if rollout.rollout_id in entries]


def summary(report: Any) -> dict[str, Any]:
    return {"mean_best_jaccard": report.mean_best_jaccard, "precision_at_m": report.precision_at_m,
            "n_axes": report.n_axes, "matches": [asdict(match) for match in report.matches]}


def evaluate_run(run: Path, shard_dirs: list[Path], gaps: list[Gap], manifests: list[str],
                 device: torch.device) -> dict[str, Any]:
    model, layer = load_sae(run, device)
    rollouts = encode_rollouts(shard_dirs, model, layer, device)
    failing = {rollout.rollout_id for rollout in rollouts if rollout.failed}
    contrastive, _effects = contrastive_directive(rollouts, ContrastiveConfig(), layer=f"driving_queries_L{layer}")
    # C27 variant: 0.8 because P4 alone is 70% of this corpus's failures; a realistic pool needs a lower cap.
    projected, _ = contrastive_directive(rollouts, ContrastiveConfig(max_failure_share=0.8),
                                         layer=f"driving_queries_L{layer}")
    episodes = {rollout.rollout_id: rollout.latents for rollout in rollouts}
    b7_pool = activation_stats_directive(episodes, episodes, failing, ActivationStatsConfig(variant="B"))
    sizes = [len(axis.rollouts) for axis in contrastive.axes] or [max(1, len(failing) // 10)]
    random_summary, _draws = score_averaged(sorted(failing), gaps, RandomBaselineConfig(axis_sizes=sizes, n_draws=200))
    taxonomy = taxonomy_directive(records(manifests, rollouts), TaxonomyConfig())
    return {"run": str(run), "layer": layer, "rollouts": len(rollouts), "failing": len(failing),
            "contrastive": summary(score(contrastive, gaps)),
            "contrastive_capped": summary(score(projected, gaps)), "B7_pool": summary(score(b7_pool, gaps)),
            "B2_taxonomy": summary(score(taxonomy, gaps)), "B1_random": random_summary,
            "contrastive_axes": [axis_overlap(axis, gaps, failing) for axis in contrastive.axes],
            "contrastive_capped_axes": [axis_overlap(axis, gaps, failing) for axis in projected.axes]}


def axis_overlap(axis: Any, gaps: list[Gap], failing: set[str]) -> dict[str, Any]:
    """An axis's size, its Jaccard with each gap's failing rollouts, and the share of all failures it holds."""
    return {"axis_id": axis.axis_id, "size": len(axis.rollouts), "description": axis.description,
            "share_of_failures": len(axis.rollouts & failing) / max(1, len(failing)),
            "jaccard": {gap.gap_id: jaccard(axis.rollouts, gap.failing_rollouts) for gap in gaps},
            "precision": {gap.gap_id: len(axis.rollouts & gap.failing_rollouts) / max(1, len(axis.rollouts))
                          for gap in gaps}}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("shards", type=Path, nargs="+")
    parser.add_argument("--sae", type=Path, nargs="+", required=True, help="SAE run directories")
    parser.add_argument("--gap", nargs="+", required=True, help="practice gaps that passed efficacy")
    parser.add_argument("--manifests", nargs="+", required=True, help="manifests (globs allowed) for B2's metadata")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    gaps = [Gap(gap, "T0_control", members) for gap, members in gap_failures(args.shards, args.gap).items()]
    manifests = sorted({path for pattern in args.manifests for path in glob.glob(pattern)})
    reports = [evaluate_run(run, args.shards, gaps, manifests, device) for run in args.sae if (run / "sae.pt").is_file()]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"gaps": {gap.gap_id: len(gap.failing_rollouts) for gap in gaps},
                                       "runs": reports}, indent=2, default=str) + "\n")
    for report in reports:
        print(report["run"], {method: report[method].get("mean_best_jaccard")
                              for method in ("contrastive", "contrastive_capped", "B7_pool", "B2_taxonomy",
                                             "B1_random")})


if __name__ == "__main__":
    main()
