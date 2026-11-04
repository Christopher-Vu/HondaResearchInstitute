"""H17: a dev rehearsal of PRD 9.2's projection removal in offline replay, on one axis. Not Step 9's verdict.

    PYTHONPATH=src .runtime/policy-venv/bin/python adapters/simlingo/causal_replay.py select POOL_SHARDS... \
        --frames-from P4_SHARDS --sae SAE_RUN --stored H12_JSON --gap P4_camera_occlusion --output OUT
    PYTHONPATH=src .runtime/policy-venv/bin/python adapters/simlingo/causal_replay.py replay OUT --device cuda
    PYTHONPATH=src .runtime/policy-venv/bin/python adapters/simlingo/causal_replay.py report OUT

The protocol and its rule are in docs/research/experiments/h17-causal-rehearsal/protocol.md.

`select` rebuilds the stored axis from the same shards and dictionary, refuses if it does not reproduce, and pairs each
failing slice rollout with its non-failing same-base twin. It writes OUT/selection.json and OUT/directions.pt.
`replay` edits the 30 driving-query tokens at decoder layer 10's output on each saved model input, once per condition,
and writes OUT/effects.npz every 25 frames. `report` applies the rule to whole pairs and writes OUT/result.json, so it
can run again on a replay cut short by its time limit. `select` and `report` each record the commit and the hashes of
this file and the protocol, so a rule changed after replay leaves a trace.

The axis is the span of its latents' decoder columns. Its edit is y' = y - QQ'y. A control moves each token by the same
length along one fixed unit vector, because plain removal along a random direction removes almost nothing in 896
dimensions and any real direction would beat it. A control therefore matches the axis per token, not on the frame mean:
the axis's edit differs by token and partly cancels in the mean, a control's does not. `report` gives both lengths.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import statistics
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import torch

from discovery.contrastive import ContrastiveConfig, Rollout, latent_effects, merge, window_rows, windows
from harness.failure_time import failure_step

LAYER = 10
RANDOM_DIRECTIONS = 100
NON_FAILURE_LATENTS = 20
DIRECTION_SEED = 17
PAIR_ORDER_SEED = 17
BOOTSTRAP_SEED = 17
BOOTSTRAP_REPLICATES = 5000
MATCH_RADIUS_M = 5.0
MIN_PAIRS = 20
RERUN_LIMIT_M = 1e-3
ZERO_EFFECT_M = 0.1
SITE_ERROR_LIMIT = 0.02
EDIT_RATIO_TOLERANCE = 0.1
CONTROL_PERCENTILE = 95
# Two outcomes are read, so each interval is at 97.5% (Bonferroni).
INTERVAL_PERCENTILES = (1.25, 98.75)
SAVE_EVERY = 25

SLICE_ROLE, NEIGHBOURHOOD_ROLE = "pilot_slice", "pilot_neighbourhood"
FAILING_ARM, CONTROL_ARM = "failing", "control"
NONE, ZERO, AXIS, FOUNDER, RANDOM, LATENT = "none", "zero", "axis", "founder", "random", "latent"
ROUTE_COLUMN, SPEED_COLUMN, EDIT_COLUMN, FRAME_MEAN_EDIT_COLUMN = 0, 1, 2, 3
EFFECT_COLUMNS = 4
OUTCOMES = {"route_m": ROUTE_COLUMN, "speed_m": SPEED_COLUMN}
# The median replay-to-log offset on CUDA bfloat16 (measured, docs/WHAT_BROKE.md 2026-10-09), so a shift inside it cannot clear.
SHIFT_FLOORS_M = {"route_m": 0.03, "speed_m": 0.06}
LABEL = "Dev rehearsal in offline replay. Not Step 9's verdict."
UNTESTED, NOT_SHOWN, ABOVE_NOT_SHOWN_LARGER, ABOVE_LARGER = (
    "untested", "not_shown_above_random", "above_random_failing_not_shown_larger", "above_random_larger_on_failing")
READINGS = {
    UNTESTED: "H17 is untested: a check failed, so no shift is read.",
    NOT_SHOWN: "In replay, H17 could not show that removing the axis moves the plan more than random edits of equal size.",
    ABOVE_NOT_SHOWN_LARGER: "In replay, removing the axis moves the plan more than random edits of equal size. H17 could "
                            "not show that it moves the plan more on failing frames than on their clean twins.",
    ABOVE_LARGER: "In replay, removing the axis moves the plan more than random edits of equal size, "
                  "and more on failing frames than on their clean twins.",
}
NOT_ABOVE_LATENTS = "Its mean shift does not exceed the 95th percentile of other latents of the same dictionary at that size."
FRAME_MEAN_NOTE = ("Each control moves the frame mean at least as far as the axis does, because the axis's per-token edits "
                   "partly cancel in the mean and a control's do not. If the plan reads the frame mean, this makes the "
                   "axis harder to show above random, not easier.")
HERE = Path(__file__).resolve()
PROTOCOL = HERE.parents[2] / "docs/research/experiments/h17-causal-rehearsal/protocol.md"


def file_sha256(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def provenance() -> dict[str, str | None]:
    """What ties a file written here to the locked rule. The commit alone would miss an uncommitted edit."""
    done = subprocess.run(["git", "rev-parse", "HEAD"], cwd=HERE.parent, capture_output=True, text=True, check=False)
    return {"commit": done.stdout.strip() if done.returncode == 0 else None,
            "code_sha256": file_sha256(HERE), "protocol_sha256": file_sha256(PROTOCOL)}


def rule_constants() -> dict[str, Any]:
    return {"shift_floors_m": SHIFT_FLOORS_M, "control_percentile": CONTROL_PERCENTILE,
            "interval_percentiles": list(INTERVAL_PERCENTILES), "bootstrap_replicates": BOOTSTRAP_REPLICATES,
            "bootstrap_seed": BOOTSTRAP_SEED, "direction_seed": DIRECTION_SEED, "pair_order_seed": PAIR_ORDER_SEED,
            "min_pairs": MIN_PAIRS, "rerun_limit_m": RERUN_LIMIT_M, "zero_effect_m": ZERO_EFFECT_M,
            "site_error_limit": SITE_ERROR_LIMIT, "edit_ratio_tolerance": EDIT_RATIO_TOLERANCE}


def unit_rows(rows: torch.Tensor) -> torch.Tensor:
    """Centred like the SAE's own inputs (sae.normalise), which cannot read a constant shift, then unit length."""
    centred = rows - rows.mean(dim=-1, keepdim=True)
    return centred / centred.norm(dim=-1, keepdim=True).clamp_min(1e-8)


def orthonormal_basis(columns: torch.Tensor) -> torch.Tensor:
    """(q, hidden) orthonormal rows spanning the given (q, hidden) rows, after centring."""
    return torch.linalg.qr(unit_rows(columns).T).Q.T


def random_directions(count: int, hidden: int, seed: int) -> torch.Tensor:
    return unit_rows(torch.randn(count, hidden, generator=torch.Generator().manual_seed(seed)))


def removed_part(tokens: torch.Tensor, basis: torch.Tensor) -> torch.Tensor:
    return (tokens @ basis.T) @ basis


@dataclass(frozen=True)
class Condition:
    name: str
    family: str
    directions: torch.Tensor | None = None


def edited_tokens(tokens: torch.Tensor, condition: Condition, axis_basis: torch.Tensor) -> torch.Tensor | None:
    """The tokens after this condition's edit; None leaves the layer's output untouched."""
    if condition.family == NONE:
        return None
    if condition.family == ZERO:
        return torch.zeros_like(tokens)
    assert condition.directions is not None
    if condition.family in (AXIS, FOUNDER):
        return tokens - removed_part(tokens, condition.directions)
    return tokens - removed_part(tokens, axis_basis).norm(dim=1, keepdim=True) * condition.directions


def conditions_from(directions: dict[str, Any], device: torch.device) -> list[Condition]:
    def moved(key: str) -> torch.Tensor:
        return directions[key].float().to(device)

    fixed = [Condition(NONE, NONE), Condition(ZERO, ZERO), Condition(AXIS, AXIS, moved("axis_basis")),
             Condition(FOUNDER, FOUNDER, moved("founder"))]
    random_rows = [Condition(f"{RANDOM}:{i}", RANDOM, row) for i, row in enumerate(moved("random"))]
    latent_rows = [Condition(f"{LATENT}:{int(latent)}", LATENT, row)
                   for latent, row in zip(directions["latent_ids"], moved("latents"))]
    return fixed + random_rows + latent_rows


class DirectionEdit:
    """A forward hook on one decoder layer: applies `condition` to the last n positions, the driving queries."""

    def __init__(self, layer: torch.nn.Module, n_queries: int, axis_basis: torch.Tensor) -> None:
        self.n = n_queries
        self.axis_basis = axis_basis
        self.condition = Condition(NONE, NONE)
        self.live_mean: torch.Tensor | None = None
        self.realised_edit = 0.0
        self.realised_frame_mean_edit = 0.0
        layer.register_forward_hook(self._hook)

    def _hook(self, _module: Any, _inputs: Any, output: Any) -> Any:
        out = output[0] if isinstance(output, tuple) else output
        tokens = out[0, -self.n:].float()
        self.live_mean = tokens.mean(dim=0)
        self.realised_edit = 0.0
        self.realised_frame_mean_edit = 0.0
        edited = edited_tokens(tokens, self.condition, self.axis_basis)
        if edited is None:
            return None
        new = out.clone()
        # The stored value is rounded to the model's dtype, so the edit that took effect is measured after that.
        new[0, -self.n:] = edited.to(out.dtype)
        moved = new[0, -self.n:].float() - tokens
        self.realised_edit = moved.norm(dim=1).mean().item()
        self.realised_frame_mean_edit = moved.mean(dim=0).norm().item()
        return (new, *output[1:]) if isinstance(output, tuple) else new


@dataclass
class Track:
    """One rollout's logged frames from its shard, and which of them have a saved model input."""
    meta: dict[str, Any]
    steps: np.ndarray
    xy: np.ndarray
    means: np.ndarray
    failure_step: int | None
    inputs: dict[int, Path]


def read_track(sidecar: Path, meta: dict[str, Any]) -> Track:
    with np.load(sidecar.with_suffix(".npz")) as archive:
        steps = archive["step"].astype(np.int64)
        xy = np.column_stack([archive["ego_x"], archive["ego_y"]]).astype(np.float64)
        means = archive["driving_queries"][:, LAYER].astype(np.float32)
        failed_at = failure_step(meta, archive)
    inputs = {int(path.stem): path for path in (Path(meta["source"]) / "capture/inputs").glob("*.pt")}
    return Track(meta, steps, xy, means, failed_at, inputs)


def slice_only_pairs(metas: list[dict[str, Any]], gap_id: str) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    """Failing slice rollouts whose same-base neighbourhood rollout did not fail: C23's slice-only failures."""
    twins = {meta["base_id"]: meta for meta in metas
             if meta.get("role") == NEIGHBOURHOOD_ROLE and meta["success"] is True}
    return [(meta, twins[meta["base_id"]]) for meta in sorted(metas, key=lambda m: str(m["route_id"]))
            if meta.get("role") == SLICE_ROLE and meta["success"] is False
            and gap_id in meta.get("practice_gaps", []) and meta["base_id"] in twins]


def failing_rows(track: Track) -> np.ndarray:
    """The rows of contrastive's own failure window that have a saved input."""
    rollout = Rollout(str(track.meta["route_id"]), np.empty((len(track.steps), 0)), track.steps, True,
                      track.failure_step)
    rows = window_rows(rollout, ContrastiveConfig(), random.Random(0))
    return np.array([row for row in rows if int(track.steps[row]) in track.inputs], dtype=np.int64)


def matched_rows(targets: np.ndarray, twin: Track) -> dict[int, float]:
    """For each target position, the twin's nearest frame with a saved input, within the radius, with its distance."""
    usable = np.array([row for row, step in enumerate(twin.steps)
                       if int(step) in twin.inputs and np.isfinite(twin.xy[row]).all()], dtype=np.int64)
    picked: dict[int, float] = {}
    if not len(usable):
        return picked
    for target in targets[np.isfinite(targets).all(axis=1)]:
        distances = np.hypot(*(twin.xy[usable] - target).T)
        nearest = float(distances.min())
        if nearest <= MATCH_RADIUS_M:
            row = int(usable[distances.argmin()])
            picked[row] = min(nearest, picked.get(row, nearest))
    return picked


def select_frames(pairs: list[tuple[Track, Track]], members: set[str], seed: int
                  ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], np.ndarray]:
    """Pairs in a seeded order, so a replay cut short still holds whole pairs drawn without regard to outcome."""
    order = np.random.default_rng(seed).permutation(len(pairs))
    rows: list[dict[str, Any]] = []
    frames: list[dict[str, Any]] = []
    means: list[np.ndarray] = []

    def add(index: int, arm: str, track: Track, row: int, match_m: float | None) -> None:
        step = int(track.steps[row])
        frames.append({"pair": index, "arm": arm, "route": str(track.meta["route_id"]), "step": step,
                       "path": str(track.inputs[step]), "match_m": match_m})
        means.append(track.means[row])

    for position in order:
        failing, twin = pairs[int(position)]
        window = failing_rows(failing)
        matched = matched_rows(failing.xy[window], twin)
        if not len(window) or not matched:
            continue
        index = len(rows)
        rows.append({"pair": index, "base_id": str(failing.meta["base_id"]), "failing": str(failing.meta["route_id"]),
                     "control": str(twin.meta["route_id"]), "axis_member": str(failing.meta["route_id"]) in members})
        for row in window:
            add(index, FAILING_ARM, failing, int(row), None)
        for row, distance in sorted(matched.items()):
            add(index, CONTROL_ARM, twin, row, distance)
    return rows, frames, np.stack(means) if means else np.empty((0, 0))


def axis_from_rollouts(rollouts: list[Rollout], axis_id: str) -> tuple[Any, dict[str, np.ndarray]]:
    """The named axis, walking the same steps as contrastive_directive, which keeps latent ids only in prose."""
    config = ContrastiveConfig()
    found = windows(rollouts, config)
    effects = latent_effects(found, config)
    return merge(found, effects, config)[int(axis_id.rsplit("a", 1)[1]) - 1], effects


def reproduction_errors(stored: dict[str, Any], members: set[str], key: set[str]) -> list[str]:
    measured = {"axis_size": len(members), "in_key": len(members & key)}
    return [f"{name}: stored {stored[name]}, rebuilt {value}" for name, value in measured.items()
            if stored[name] != value]


def non_failure_latents(effects: dict[str, np.ndarray], count: int, seed: int) -> np.ndarray:
    """Latents as active on failures as an axis must be, which contrastive's own test does not tie to failure."""
    config = ContrastiveConfig()
    tied = (effects["q"] < config.max_q) & (effects["smd"] > 0)
    eligible = np.flatnonzero(~tied & (effects["support"] >= config.min_support))
    chosen = np.random.default_rng(seed).choice(eligible, size=min(count, len(eligible)), replace=False)
    return np.sort(chosen)


def stored_axis(stored_path: Path, sae_run: str, gap_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    methods = json.loads(stored_path.read_text())["methods"]
    best = [method["gaps"][gap_id]["best_jaccard"] for method in methods.values() if method["family"] == "M1_raw"]
    spread = {"dictionaries": len(best), "best_jaccard": max(best), "median_jaccard": statistics.median(best),
              "note": "The best axis is chosen using the key."}
    return methods[f"M1_raw@{sae_run}"]["gaps"][gap_id], spread


def rebuild_axis(args: argparse.Namespace, record: dict[str, Any]) -> tuple[Any, Any, dict[str, np.ndarray]]:
    from discovery.dev_eval import encode_frames, gap_keys, load_sae, load_shards, read_frames

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    shards = load_shards(args.pool)
    model, config = load_sae(args.sae, device)
    if config["layer"] != LAYER:
        raise SystemExit(f"{args.sae} is at layer {config['layer']}, not {LAYER}")
    rollouts, _explained = encode_frames(model, [read_frames(shard, LAYER) for shard in shards], device)
    axis, effects = axis_from_rollouts(rollouts, record["axis_id"])
    errors = reproduction_errors(record, axis.members, gap_keys(shards, [args.gap])[0].failing_rollouts)
    if errors:
        raise SystemExit(f"axis {record['axis_id']} did not reproduce: {errors}")
    return model, axis, effects


def paired_tracks(frames_from: Path, gap_id: str) -> tuple[list[tuple[Track, Track]], int]:
    from discovery.dev_eval import load_shards

    shards = load_shards([frames_from])
    sidecars = {shard.route_id: shard.sidecar for shard in shards}
    meta_pairs = slice_only_pairs([shard.meta for shard in shards], gap_id)
    expected = json.loads((frames_from.parent / "efficacy.json").read_text())["c23_paired"]["slice_only_failed"]
    if len(meta_pairs) != expected:
        raise SystemExit(f"{len(meta_pairs)} slice-only pairs, but efficacy.json has {expected}")
    return [(read_track(sidecars[str(failing["route_id"])], failing), read_track(sidecars[str(twin["route_id"])], twin))
            for failing, twin in meta_pairs], expected


def run_select(args: argparse.Namespace) -> None:
    record, spread = stored_axis(args.stored, str(args.sae), args.gap)
    model, axis, effects = rebuild_axis(args, record)
    tracks, expected = paired_tracks(args.frames_from, args.gap)
    pairs, frames, means = select_frames(tracks, axis.members, PAIR_ORDER_SEED)
    if len(pairs) < MIN_PAIRS:
        raise SystemExit(f"only {len(pairs)} of {expected} pairs have saved inputs and a match; {MIN_PAIRS} needed")
    decoder = model.decoder.data.T.cpu()
    latent_ids = non_failure_latents(effects, NON_FAILURE_LATENTS, DIRECTION_SEED)
    directions = {"axis_basis": orthonormal_basis(decoder[sorted(axis.latents)]),
                  "founder": unit_rows(decoder[[axis.founder]]),
                  "random": random_directions(RANDOM_DIRECTIONS, decoder.shape[1], DIRECTION_SEED),
                  "latents": unit_rows(decoder[latent_ids]), "latent_ids": latent_ids.tolist(),
                  "logged_means": torch.from_numpy(means)}
    args.output.mkdir(parents=True, exist_ok=True)
    torch.save(directions, args.output / "directions.pt")
    selection = {"label": LABEL, "provenance": provenance(), "gap": args.gap, "sae": str(args.sae), "layer": LAYER,
                 "axis": {**record, **spread, "founder": axis.founder, "latents": sorted(axis.latents),
                          "members": sorted(axis.members)},
                 "pairs_expected": expected, "pairs": pairs, "frames": frames}
    (args.output / "selection.json").write_text(json.dumps(selection, indent=1) + "\n")
    forwards = len(frames) * (1 + len(conditions_from(directions, torch.device("cpu"))))
    print(f"axis {record['axis_id']}: {len(axis.members)} rollouts, {len(axis.latents)} latents")
    print(f"{len(pairs)} of {expected} pairs, {len(frames)} frames, {forwards} forward passes")


def shift(edited: torch.Tensor, intact: torch.Tensor) -> float:
    return (edited - intact).norm(dim=1).mean().item()


def run_replay(args: argparse.Namespace) -> None:
    # Imported here because these need the policy's own dependencies, which select and report do not.
    from ablate_replay import load_frame, plan
    from replay_capture import decoder, driving_query_count, load_in_dtype
    from verify_checkpoint import ROOT

    sys.path.insert(0, str(ROOT / ".runtime/simlingo"))
    selection = json.loads((args.output / "selection.json").read_text())
    directions = torch.load(args.output / "directions.pt", weights_only=False)
    frames = selection["frames"][: args.limit or None]
    device, dtype = torch.device(args.device), torch.bfloat16
    model = load_in_dtype(dtype).to(device).eval()
    edit = DirectionEdit(decoder(model).layers[LAYER], driving_query_count(model),
                         directions["axis_basis"].float().to(device))
    conditions = conditions_from(directions, device)
    effects: np.ndarray = np.zeros((len(frames), len(conditions), EFFECT_COLUMNS), dtype=np.float32)
    site_errors: np.ndarray = np.zeros(len(frames), dtype=np.float32)
    names = np.array([condition.name for condition in conditions])
    started = time.monotonic()
    for i, record in enumerate(frames):
        frame = load_frame(Path(record["path"]), dtype, device)
        edit.condition = conditions[0]
        speed0, route0 = plan(model, frame)
        logged = directions["logged_means"][i].float().to(device)
        site_errors[i] = ((edit.live_mean - logged).norm() / logged.norm().clamp_min(1e-8)).item()
        for j, condition in enumerate(conditions):
            edit.condition = condition
            speed, route = plan(model, frame)
            effects[i, j] = [shift(route, route0), shift(speed, speed0), edit.realised_edit,
                             edit.realised_frame_mean_edit]
        if (i + 1) % SAVE_EVERY == 0 or i + 1 == len(frames):
            np.savez_compressed(args.output / "effects.npz", effects=effects[: i + 1], conditions=names,
                                site_errors=site_errors[: i + 1], seconds=time.monotonic() - started)
            print(f"{i + 1}/{len(frames)} frames, {time.monotonic() - started:.0f} s", flush=True)
        if i + 1 == SAVE_EVERY and (failed := failed_early(effects[: i + 1], site_errors[: i + 1], names.tolist())):
            raise SystemExit(f"stopped after {i + 1} frames, so H17 is untested. Failed checks: {failed}")


def families_of(names: list[str]) -> list[str]:
    return [name.split(":")[0] for name in names]


def whole_pairs(frames: list[dict[str, Any]], done: int) -> list[int]:
    """Pairs with every frame replayed, in the seeded order that select_frames fixed."""
    total: dict[int, int] = {}
    finished: dict[int, int] = {}
    for index, frame in enumerate(frames):
        total[frame["pair"]] = total.get(frame["pair"], 0) + 1
        finished[frame["pair"]] = finished.get(frame["pair"], 0) + (index < done)
    return [pair for pair in sorted(total) if finished[pair] == total[pair]]


def pair_means(effects: np.ndarray, frames: list[dict[str, Any]], pairs: list[int], arm: str) -> np.ndarray:
    """(pairs, conditions, columns): one value per route, so a route's frames do not count as separate evidence."""
    return np.stack([effects[[i for i, frame in enumerate(frames[: len(effects)])
                              if frame["pair"] == pair and frame["arm"] == arm]].mean(axis=0) for pair in pairs])


def excess(route_values: np.ndarray, axis: int, controls: np.ndarray) -> float:
    means = route_values.mean(axis=0)
    return float(means[axis] - np.percentile(means[controls], CONTROL_PERCENTILE))


def interval(draws: np.ndarray) -> list[float]:
    low, high = np.percentile(draws, INTERVAL_PERCENTILES)
    return [float(low), float(high)]


def stopped_by(axis_mean: float, floor_m: float, excess_low: float) -> list[str]:
    """Which gates kept an outcome from clearing: its shift is inside rounding, or its interval reaches zero."""
    return [gate for gate, stopped in (("floor", axis_mean < floor_m), ("interval", excess_low <= 0)) if stopped]


def read_outcome(failing: np.ndarray, control: np.ndarray, families: list[str], floor_m: float) -> dict[str, Any]:
    """The rule for one outcome, on (pairs, conditions) arrays; each bootstrap draw resamples base routes."""
    axis = families.index(AXIS)
    randoms = np.array([i for i, family in enumerate(families) if family == RANDOM])
    latents = np.array([i for i, family in enumerate(families) if family == LATENT])
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    draws = np.empty((BOOTSTRAP_REPLICATES, 3))
    for replicate in range(BOOTSTRAP_REPLICATES):
        picked = rng.integers(0, len(failing), len(failing))
        over_failing = excess(failing[picked], axis, randoms)
        over_control = excess(control[picked], axis, randoms)
        draws[replicate] = over_failing, over_control, over_failing - over_control
    axis_mean = float(failing[:, axis].mean())
    excess_interval, difference_interval = interval(draws[:, 0]), interval(draws[:, 2])
    stopped = stopped_by(axis_mean, floor_m, excess_interval[0])
    clears = not stopped
    return {"axis_mean_m": axis_mean, "axis_control_frames_mean_m": float(control[:, axis].mean()),
            "founder_mean_m": float(failing[:, families.index(FOUNDER)].mean()),
            "random_p95_m": float(np.percentile(failing[:, randoms].mean(axis=0), CONTROL_PERCENTILE)),
            "excess_m": excess(failing, axis, randoms), "excess_interval": excess_interval,
            "control_frames_excess_m": excess(control, axis, randoms), "control_frames_interval": interval(draws[:, 1]),
            "failing_minus_control_m": excess(failing, axis, randoms) - excess(control, axis, randoms),
            "difference_interval": difference_interval,
            "non_failure_latent_p95_m": float(np.percentile(failing[:, latents].mean(axis=0), CONTROL_PERCENTILE))
            if len(latents) else None,
            "above_non_failure_latents": bool(len(latents) and excess(failing, axis, latents) > 0),
            "floor_m": floor_m, "stopped_by": stopped, "clears": clears,
            "specific": clears and difference_interval[0] > 0}


def run_checks(effects: np.ndarray, site_errors: np.ndarray, families: list[str], pairs: int) -> dict[str, Any]:
    rerun = float(np.percentile(effects[:, families.index(NONE), :EDIT_COLUMN], 90))
    zero = float(np.median(effects[:, families.index(ZERO), :EDIT_COLUMN], axis=0).max())
    site = float(np.median(site_errors))
    axis_edit = float(effects[:, families.index(AXIS), EDIT_COLUMN].mean())
    randoms = [i for i, family in enumerate(families) if family == RANDOM]
    ratios = effects[:, randoms, EDIT_COLUMN].mean(axis=0) / max(axis_edit, 1e-12)
    worst = float(np.abs(ratios - 1).max())
    return {"pairs": {"value": pairs, "limit": MIN_PAIRS, "passes": pairs >= MIN_PAIRS},
            "rerun_p90_m": {"value": rerun, "limit": RERUN_LIMIT_M, "passes": rerun <= RERUN_LIMIT_M},
            "zeroed_tokens_median_m": {"value": zero, "limit": ZERO_EFFECT_M, "passes": zero >= ZERO_EFFECT_M},
            "site_error_median": {"value": site, "limit": SITE_ERROR_LIMIT, "passes": site <= SITE_ERROR_LIMIT},
            "edit_ratio_worst": {"value": worst, "limit": EDIT_RATIO_TOLERANCE,
                                 "passes": worst <= EDIT_RATIO_TOLERANCE}}


def failed_early(effects: np.ndarray, site_errors: np.ndarray, names: list[str]) -> list[str]:
    """Checks that any few frames can already fail, so a broken run stops before it spends its time limit."""
    checks = run_checks(effects, site_errors, families_of(names), MIN_PAIRS)
    return [name for name, check in checks.items() if not check["passes"]]


def overall(checks: dict[str, Any], outcomes: dict[str, dict[str, Any]]) -> str:
    if not all(check["passes"] for check in checks.values()):
        return UNTESTED
    if any(row["specific"] for row in outcomes.values()):
        return ABOVE_LARGER
    if any(row["clears"] for row in outcomes.values()):
        return ABOVE_NOT_SHOWN_LARGER
    return NOT_SHOWN


def member_split(failing: np.ndarray, members: np.ndarray, axis: int, column: int) -> dict[str, float | None]:
    def mean(rows: np.ndarray) -> float | None:
        return float(rows[:, axis, column].mean()) if len(rows) else None

    return {"axis_members": mean(failing[members]), "not_axis_members": mean(failing[~members])}


def frame_mean_edit(failing: np.ndarray, control: np.ndarray, families: list[str]) -> dict[str, Any]:
    """Per arm, the axis's frame-mean edit length against the random controls', with the bias stated beside them."""
    axis = families.index(AXIS)
    randoms = [i for i, family in enumerate(families) if family == RANDOM]

    def lengths(rows: np.ndarray) -> dict[str, float]:
        return {"axis": float(rows[:, axis, FRAME_MEAN_EDIT_COLUMN].mean()),
                "random_mean": float(rows[:, randoms, FRAME_MEAN_EDIT_COLUMN].mean())}

    return {FAILING_ARM: lengths(failing), CONTROL_ARM: lengths(control), "note": FRAME_MEAN_NOTE}


def gate_details(outcomes: dict[str, dict[str, Any]]) -> str:
    """Why a not-shown result was not shown, in numbers, so it cannot be read as a measured absence."""
    return " ".join(
        f"{name}: stopped by {' and '.join(row['stopped_by'])}, A {row['axis_mean_m']:.3f} m, floor {row['floor_m']:.3f} m, "
        f"T {row['random_p95_m']:.3f} m, excess interval {row['excess_interval'][0]:.3f} to "
        f"{row['excess_interval'][1]:.3f} m." for name, row in outcomes.items())


def reading_for(outcome: str, outcomes: dict[str, dict[str, Any]]) -> str:
    if outcome == NOT_SHOWN:
        return f"{READINGS[outcome]} {gate_details(outcomes)}"
    if outcome == UNTESTED or any(row["clears"] and row["above_non_failure_latents"] for row in outcomes.values()):
        return READINGS[outcome]
    return f"{READINGS[outcome]} {NOT_ABOVE_LATENTS}"


def build_result(selection: dict[str, Any], effects: np.ndarray, site_errors: np.ndarray, names: list[str]
                 ) -> dict[str, Any]:
    families = families_of(names)
    frames = selection["frames"]
    pairs = whole_pairs(frames, len(effects))
    checks = run_checks(effects, site_errors, families, len(pairs))
    result: dict[str, Any] = {"label": LABEL, "dev_rehearsal": True, "step9_verdict": False,
                              "rule": rule_constants(), "axis": selection["axis"], "gap": selection["gap"], "sae": selection["sae"],
                              "pairs_expected": selection["pairs_expected"], "pairs_read": len(pairs),
                              "frames_replayed": len(effects), "checks": checks, "outcomes": {}}
    if pairs:
        failing = pair_means(effects, frames, pairs, FAILING_ARM)
        control = pair_means(effects, frames, pairs, CONTROL_ARM)
        members = np.array([selection["pairs"][pair]["axis_member"] for pair in pairs])
        axis = families.index(AXIS)
        result["outcomes"] = {name: {**read_outcome(failing[:, :, column], control[:, :, column], families,
                                                    SHIFT_FLOORS_M[name]),
                                     "by_membership": member_split(failing, members, axis, column)}
                              for name, column in OUTCOMES.items()}
        result["axis_edit_norm"] = {FAILING_ARM: float(failing[:, axis, EDIT_COLUMN].mean()),
                                    CONTROL_ARM: float(control[:, axis, EDIT_COLUMN].mean())}
        result["frame_mean_edit"] = frame_mean_edit(failing, control, families)
    result["outcome"] = overall(checks, result["outcomes"])
    result["reading"] = reading_for(result["outcome"], result["outcomes"])
    return result


def run_report(args: argparse.Namespace) -> None:
    selection = json.loads((args.output / "selection.json").read_text())
    with np.load(args.output / "effects.npz") as saved:
        result = build_result(selection, saved["effects"], saved["site_errors"], saved["conditions"].tolist())
    current = provenance()
    result["provenance"] = {"at_report": current, "at_select": selection.get("provenance"),
                            "changed_since_select": current != selection.get("provenance")}
    (args.output / "result.json").write_text(json.dumps(result, indent=1) + "\n")
    print(result["label"], result["reading"], sep="\n")
    print(json.dumps({"checks": result["checks"], "outcomes": result["outcomes"]}, indent=1))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    select = commands.add_parser("select")
    select.add_argument("pool", type=Path, nargs="+", help="the shard folders the axis was read from")
    select.add_argument("--frames-from", type=Path, required=True, help="a pilot's shards, beside its efficacy.json")
    select.add_argument("--sae", type=Path, required=True)
    select.add_argument("--stored", type=Path, required=True, help="dev_eval output naming the axis")
    select.add_argument("--gap", required=True)
    select.add_argument("--output", type=Path, required=True)
    replay = commands.add_parser("replay")
    replay.add_argument("output", type=Path)
    replay.add_argument("--device", default="cuda")
    replay.add_argument("--limit", type=int, default=0, help="replay only the first N frames (smoke test)")
    report = commands.add_parser("report")
    report.add_argument("output", type=Path)
    args = parser.parse_args()
    {"select": run_select, "replay": run_replay, "report": run_report}[args.command](args)


if __name__ == "__main__":
    main()
