"""Turn each rollout's capture/steps.pt into one compact shard for the Step 4 layer sweep.

    .runtime/policy-venv/bin/python adapters/simlingo/export_activations.py \\
        results/savio/<job> [<route dir or parent> ...] --output results/step4/shards \\
        [--manifest configs/rollout/step4-dev-pool.manifest.json] [--stride 5]

Each argument is a route directory (holding capture/steps.pt) or a parent of `route-<id>` directories.
A route writes `<route id>.npz` and `<route id>.json` to the output directory.

The npz holds every `--stride`-th policy step (steps divisible by the stride) in float16: `all_tokens` and
`driving_queries` as (T, layers, hidden), `vision_bridge` as (T, hidden) when the capture has it, `step` as
(T,), and the state list as (T,) float32 arrays with NaN where a record has no value. The three
`*_episode_mean` arrays are float32 means over all steps, not only the strided ones.

The json sidecar carries the outcome (`success` is null when the route has no valid driving outcome, and
the sweep then leaves it out), the manifest's base route, role and practice gaps, and where the shard came from.
Success is `route_outcome`'s rule from sweep_local.py, the same one that fills routes.jsonl.
"""
from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any

import numpy as np
import torch
from artifacts import ROOT
from route_run import route_from_xml
from sweep_local import route_outcome

CONTINUOUS_STATES = ("ego_speed", "lead_distance", "lead_relative_speed", "pedestrian_distance",
                     "junction_distance", "time_to_junction")
ACTIVATION_DTYPE = np.float16
FLOAT16_LIMIT = float(np.finfo(ACTIVATION_DTYPE).max)
RESULT_ROUTE_ID = re.compile(r"^RouteScenario_(.+?)(?:_rep\d+)?$")


def route_dirs_under(paths: list[Path]) -> list[Path]:
    found: dict[Path, None] = {}
    for path in paths:
        directly = [path] if (path / "capture/steps.pt").is_file() else []
        for route_dir in directly or sorted(path.glob("route-*")):
            if (route_dir / "capture/steps.pt").is_file():
                found[route_dir.resolve()] = None
    return list(found)


def route_id_of(route_dir: Path) -> str:
    if route_dir.name.startswith("route-"):
        return route_dir.name.removeprefix("route-")
    records = json.loads((route_dir / "result.json").read_text())["_checkpoint"]["records"]
    return RESULT_ROUTE_ID.match(records[0]["route_id"]).group(1)  # type: ignore[union-attr]


def load_manifest(path: Path | None) -> dict[str, dict[str, Any]]:
    if path is None:
        return {}
    data = json.loads(path.read_text())
    entries = data["rollouts"] if isinstance(data, dict) else data
    return {str(entry["id"]): entry for entry in entries}


def xml_identity(route_id: str) -> dict[str, str]:
    try:
        return route_from_xml(route_id)
    except (ValueError, OSError):
        return {}


def number(state: dict[str, Any] | None, key: str) -> float:
    value = state.get(key) if state else None
    return math.nan if value is None else float(value)


def red_light(state: dict[str, Any] | None) -> float:
    light = state.get("traffic_light") if state else None
    return math.nan if light is None else float(light == "red")


def usable(state: Any) -> dict[str, Any] | None:
    return state if isinstance(state, dict) and "error" not in state else None


def state_arrays(records: list[dict[str, Any]]) -> dict[str, np.ndarray]:
    states = [usable(record.get("state")) for record in records]
    columns = {name: [number(state, name) for state in states] for name in CONTINUOUS_STATES}
    columns["red_light"] = [red_light(state) for state in states]
    columns["occluded"] = [number(state, "occluded") for state in states]
    return {name: np.asarray(values, dtype=np.float32) for name, values in columns.items()}


def float16_checked(values: np.ndarray, name: str) -> np.ndarray:
    if np.abs(values).max(initial=0.0) > FLOAT16_LIMIT:
        raise ValueError(f"{name} has values beyond float16 range; store this site in float32 instead")
    return values.astype(ACTIVATION_DTYPE)


def stacked(records: list[dict[str, Any]], key: str) -> np.ndarray:
    return np.stack([record[key].float().numpy() for record in records])


def episode_mean(values: np.ndarray) -> np.ndarray:
    return values.mean(axis=0, dtype=np.float64).astype(np.float32)


def activation_arrays(records: list[dict[str, Any]], strided: np.ndarray) -> dict[str, np.ndarray]:
    sites = {"all_tokens": "layer_mean", "driving_queries": "layer_driving_mean"}
    if all(record.get("vision_bridge_mean") is not None for record in records):
        sites["vision_bridge"] = "vision_bridge_mean"
    arrays: dict[str, np.ndarray] = {}
    for site, key in sites.items():
        values = stacked(records, key)
        arrays[site] = float16_checked(values[strided], site)
        arrays[f"{site}_episode_mean"] = episode_mean(values)
    return arrays


def first_collision_step(collisions: list[dict[str, Any]] | None) -> int | None:
    return min((int(collision["step"]) for collision in collisions or []), default=None)


def source_label(route_dir: Path) -> str:
    return str(route_dir.relative_to(ROOT) if route_dir.is_relative_to(ROOT) else route_dir)


def sidecar(route_dir: Path, route_id: str, capture: dict[str, Any], entry: dict[str, Any],
            stride: int) -> dict[str, Any]:
    identity = {**xml_identity(entry.get("base_id", route_id)), **entry}
    outcome = route_outcome(route_dir)
    return {
        "route_id": route_id, "base_id": identity.get("base_id", route_id),
        "scenario": identity.get("scenario"), "town": identity.get("town"),
        "status": outcome.get("status"), "success": outcome.get("success"),
        "infractions": outcome.get("infractions", {}),
        "practice_gaps": identity.get("practice_gaps", []), "role": identity.get("role"),
        "neighbourhood_of": identity.get("neighbourhood_of", []),
        "first_collision_step": first_collision_step(capture.get("collisions")),
        "n_steps": len(capture["records"]), "stride": stride, "capture_every": capture["capture_every"],
        "dtype": capture["dtype"], "source": source_label(route_dir),
    }


def export_route(route_dir: Path, output: Path, manifest: dict[str, dict[str, Any]], stride: int) -> dict[str, Any]:
    route_id = route_id_of(route_dir)
    capture = torch.load(route_dir / "capture/steps.pt", map_location="cpu", weights_only=False)
    records = capture["records"]
    steps = np.asarray([record["step"] for record in records], dtype=np.int64)
    strided = steps % stride == 0
    # Typed loosely so numpy's stubs accept the ** spread beside savez's own allow_pickle flag.
    arrays: dict[str, Any] = activation_arrays(records, strided)
    arrays["step"] = steps[strided].astype(np.int32)
    arrays |= {name: values[strided] for name, values in state_arrays(records).items()}
    np.savez(output / f"{route_id}.npz", **arrays)
    meta = sidecar(route_dir, route_id, capture, manifest.get(route_id, {}), stride)
    (output / f"{route_id}.json").write_text(json.dumps(meta, indent=2) + "\n")
    return meta


def export_all(paths: list[Path], output: Path, manifest_path: Path | None = None,
               stride: int = 5) -> list[dict[str, Any]]:
    output.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest(manifest_path)
    exported = []
    for route_dir in route_dirs_under(paths):
        meta = export_route(route_dir, output, manifest, stride)
        size_mb = (output / f"{meta['route_id']}.npz").stat().st_size / 1e6
        print(f"{meta['route_id']}: {meta['n_steps']} steps, success={meta['success']}, {size_mb:.1f} MB")
        exported.append(meta)
    return exported


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("routes", type=Path, nargs="+", help="route directories or their parents")
    parser.add_argument("--output", type=Path, required=True, help="shard directory")
    parser.add_argument("--manifest", type=Path, help="dev-pool manifest: base route, role and practice gaps")
    parser.add_argument("--stride", type=int, default=5, help="keep steps divisible by this (default 5)")
    args = parser.parse_args()
    exported = export_all(args.routes, args.output, args.manifest, args.stride)
    print(f"{len(exported)} shards in {args.output}")


if __name__ == "__main__":
    main()
