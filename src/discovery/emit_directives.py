"""Each method and baseline writes its directive to a file, so scoring needs only those files and the key (Step 8).

    PYTHONPATH=src python -m discovery.emit_directives SHARD_DIR [...] --layer 10 --sae RUN [...] \
        --manifests 'configs/rollout/x.manifest.json' --primary-dictionary L10_k64_s0 --output DIR

Reads the same representation as dev_eval, and the variant comes from the shards' `preprocessing` field, so a
directive cannot be mislabelled by a flag. A non-residualized pool emits M1 raw and capped and B7-pool per dictionary,
M2, B2, B3 and one draw of B1 sized from `--primary-dictionary`'s M1 axes. A residualized pool emits M1, B7-pool and
M2: B1, B2 and B3 read no activations, so a second copy would only be a duplicate. Sidecars' `practice_gaps` and
`role` are never read here.

Each output is `<family>@<dictionary or none>@<variant>.json`: {family, kind, dictionary, counts, explained_variance,
directive}. `counts` is dev_eval's rule that a dictionary below 0.8 explained variance on these frames is reported
but does not count.

Must never read the answer key. CI-enforced; see scripts/check_sealed_imports.py.
"""
from __future__ import annotations

import argparse
import glob
import json
from pathlib import Path
from typing import Any

import torch

from baselines.random_baseline import RandomBaselineConfig, draw_directive
from discovery import dev_eval
from discovery.dev_eval import BASELINE, MethodRun, Shard
from harness.schema import ACTION_RESIDUAL, NON_RESIDUALIZED, Directive


def variant_of(shards: list[Shard]) -> str:
    variants = {shard.meta.get("preprocessing", NON_RESIDUALIZED) for shard in shards}
    if len(variants) != 1:
        raise ValueError(f"shards mix preprocessing variants {sorted(variants)}: emit each variant from its own pool")
    return variants.pop()


def tag(directive: Directive, variant: str) -> Directive:
    directive.preprocessing = variant
    for axis in directive.axes:
        axis.preprocessing = [variant]
    directive.validate()
    return directive


def random_run(runs: list[MethodRun], failing: list[str], primary: str | None) -> MethodRun:
    """One seeded draw of B1, sized from the primary dictionary's M1 axes or a tenth of the failures if it has none."""
    source = [run for run in runs if run.family == "M1_raw" and run.sae and Path(run.sae.run).name == primary]
    if primary is not None and not source:
        raise ValueError(f"--primary-dictionary {primary} matches no M1 dictionary in this run")
    sizes = [len(axis.rollouts) for run in source for axis in run.directive.axes] or [max(1, len(failing) // 10)]
    return MethodRun("B1_random", BASELINE, draw_directive(failing, RandomBaselineConfig(axis_sizes=sizes)))


def method_runs(shards: list[Shard], layer: int, sae_runs: list[Path], manifests: list[str], device: torch.device,
                primary: str | None) -> list[MethodRun]:
    frames = [dev_eval.read_frames(shard, layer) for shard in shards]
    runs, _infos, _skipped = dev_eval.run_saes(sae_runs, frames, layer, device)
    if variant_of(shards) == ACTION_RESIDUAL:
        return [*runs, dev_eval.probe_run(shards, layer)]
    records = dev_eval.taxonomy_records(manifests, {s.route_id: not s.meta["success"] for s in shards})
    failing = sorted(s.route_id for s in shards if s.meta["success"] is False)
    return [*runs, *dev_eval.non_sae_methods(shards, layer, records), random_run(runs, failing, primary)]


def record(run: MethodRun, variant: str) -> dict[str, Any]:
    return {"family": run.family, "kind": run.kind, "dictionary": Path(run.sae.run).name if run.sae else None,
            "counts": run.counts, "explained_variance": run.sae.explained_variance if run.sae else None,
            "directive": tag(run.directive, variant).to_dict()}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("shards", type=Path, nargs="+")
    parser.add_argument("--layer", type=int, default=10)
    parser.add_argument("--sae", type=Path, nargs="*", default=[])
    parser.add_argument("--manifests", nargs="*", default=[], help="manifests (globs allowed) for B2's metadata")
    parser.add_argument("--primary-dictionary", help="SAE run directory name that sizes B1's draw")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    shards = dev_eval.load_shards(args.shards)
    variant = variant_of(shards)
    manifests = sorted({path for pattern in args.manifests for path in glob.glob(pattern)})
    args.output.mkdir(parents=True, exist_ok=True)
    for run in method_runs(shards, args.layer, args.sae, manifests, device, args.primary_dictionary):
        item = record(run, variant)
        name = f"{item['family']}@{item['dictionary'] or 'none'}@{variant}.json"
        (args.output / name).write_text(json.dumps(item, indent=1) + "\n")
        print(f"{name}: {len(item['directive']['axes'])} axes, counts={item['counts']}")


if __name__ == "__main__":
    main()
