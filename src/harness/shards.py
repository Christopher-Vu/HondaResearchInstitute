"""The shard contract: what a policy adapter hands the rest of the system (PRD 8.2).

Every discovery method, baseline and the scoring read rollouts only through shards, so a policy whose adapter
writes conforming shards gets all of them without touching their code. One rollout is two files with the same
stem in one directory:

`<id>.json`, the sidecar:
- `route_id` (str): the rollout's id, unique in the pool. `base_id` (str): the base route it was generated
  from; bootstrap and held-out splits resample by it.
- `success` (bool or null): the outcome. null means no valid outcome (a crash), and every reader skips it.
- `infractions` ({name: count}): what went wrong, for failure timing and B3.
- `first_collision_step` (int or null): the step of the first collision.
- Optional: `infraction_locations` ({name: [[x, y], ...]}), and the generation metadata gap predicates and
  baselines read (`scenario`, `town`, `practice_gaps`, `role`, `neighbourhood_of`).

`<id>.npz`, per logged step:
- `step` (T,) int: the policy step of each row, increasing.
- At least one activation site: a (T, layers, hidden) float array, with its `<site>_episode_mean` (layers,
  hidden) over every step, not only the logged ones. Site names are the adapter's own (SimLingo's are
  `driving_queries`, `all_tokens`, `vision_bridge`); methods name the site they read in their config.
- Optional per-token capture for the SAE: `driving_query_tokens` (T, token layers, tokens, hidden) with
  `driving_query_token_layers` naming the layers.
- Optional state arrays (T,) float with NaN for "no value" (`ego_speed`, `red_light`, `ego_x`, ...), which
  probe-residual, B3 and failure timing read when present.

Methods still assume 20 policy steps per simulated second (Bench2Drive's rate).

    python -m harness.shards <shard dir> [...]     # lists every non-conforming shard; exit 1 if any
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

TOKEN_ARRAYS = ("driving_query_tokens", "driving_query_token_layers")


def meta_problems(meta: dict) -> list[str]:
    problems = [f"sidecar lacks {key}" for key in ("route_id", "base_id", "success", "infractions",
                                                     "first_collision_step") if key not in meta]
    if "success" in meta and meta["success"] not in (True, False, None):
        problems.append("success is not true, false or null")
    if not isinstance(meta.get("infractions", {}), dict):
        problems.append("infractions is not a mapping")
    step = meta.get("first_collision_step")
    if step is not None and not isinstance(step, int):
        problems.append("first_collision_step is not an integer or null")
    return problems


def array_problems(arrays: dict[str, np.ndarray]) -> list[str]:
    if "step" not in arrays:
        return ["npz lacks step"]
    steps = arrays["step"]
    if steps.ndim != 1 or not np.issubdtype(steps.dtype, np.integer) or np.any(np.diff(steps) <= 0):
        return ["step is not a 1-d increasing integer array"]
    rows = len(steps)
    sites = [name for name, values in arrays.items() if values.ndim == 3 and name not in TOKEN_ARRAYS]
    problems = [] if sites else ["npz has no (T, layers, hidden) activation site"]
    for site in sites:
        mean = arrays.get(f"{site}_episode_mean")
        if len(arrays[site]) != rows:
            problems.append(f"{site} has {len(arrays[site])} rows for {rows} steps")
        if mean is None or mean.shape != arrays[site].shape[1:]:
            problems.append(f"{site} lacks a matching {site}_episode_mean")
    for name, values in arrays.items():
        if values.ndim == 1 and name != "step" and name not in TOKEN_ARRAYS and len(values) != rows:
            problems.append(f"state {name} has {len(values)} rows for {rows} steps")
    if ("driving_query_tokens" in arrays) != ("driving_query_token_layers" in arrays):
        problems.append("driving_query_tokens and driving_query_token_layers come together")
    elif "driving_query_tokens" in arrays:
        tokens, layers = arrays["driving_query_tokens"], arrays["driving_query_token_layers"]
        if tokens.ndim != 4 or len(tokens) != rows or tokens.shape[1] != len(layers):
            problems.append("driving_query_tokens is not (T, token layers, tokens, hidden)")
    return problems


def shard_problems(sidecar: Path) -> list[str]:
    """What keeps one shard from conforming; empty when it conforms."""
    npz = sidecar.with_suffix(".npz")
    if not npz.is_file():
        return [f"no {npz.name} beside the sidecar"]
    meta = json.loads(sidecar.read_text())
    with np.load(npz) as archive:
        arrays = {name: archive[name] for name in archive.files}
    return meta_problems(meta) + array_problems(arrays)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("dirs", type=Path, nargs="+", help="shard directories")
    found = {sidecar: shard_problems(sidecar) for directory in parser.parse_args().dirs
             for sidecar in sorted(directory.glob("*.json"))}
    bad = {sidecar: problems for sidecar, problems in found.items() if problems}
    for sidecar, problems in bad.items():
        print(f"{sidecar}: {'; '.join(problems)}")
    print(f"{len(found) - len(bad)} of {len(found)} shards conform")
    raise SystemExit(1 if bad or not found else 0)


if __name__ == "__main__":
    main()
