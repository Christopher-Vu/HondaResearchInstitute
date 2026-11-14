#!/usr/bin/env python3
"""H24's route-level features, one row per rollout with an outcome. Reads shards only, never a key.

    PYTHONPATH=src python docs/research/experiments/h24-error-aware-grouping/export_features.py SHARD_DIR [...] \
        --output features.npz

Every block uses B3's window: the logged steps in the 3 s before the failure step, or before the last step.
- act: the mean of layer-10 driving-query frame means over that window.
- kin: what the car did, and nothing about the scene: speed mean, min and max in the window, and the share of the
  whole route spent stationary.
- full: B3's own feature row (kinematics, penalties, and the simulator's distances to nearby objects).
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from baselines import behavioral
from discovery import dev_eval

LAYER = 10
KIN = ("ego_speed_mean", "ego_speed_min", "ego_speed_max", "stationary_frac")


def window_mean(frames: dev_eval.Frames) -> np.ndarray:
    span = int(behavioral.BehavioralConfig().window_s * behavioral.STEPS_PER_SECOND)
    end = frames.failure_step if frames.failure_step is not None else int(frames.steps[-1]) + 1
    rows = np.flatnonzero((frames.steps >= end - span) & (frames.steps < end))
    rows = rows if len(rows) else np.array([len(frames.steps) - 1])
    return frames.means[rows].mean(axis=0)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("shards", type=Path, nargs="+")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    shards = dev_eval.load_shards(args.shards)
    config = behavioral.BehavioralConfig()
    kin_columns = [behavioral.FEATURES.index(name) for name in KIN]
    ids, failed, act, full = [], [], [], []
    for shard in shards:
        rollout = behavioral.load_shard(shard.sidecar)
        frames = dev_eval.read_frames(shard, LAYER)
        ids.append(shard.route_id)
        failed.append(rollout.failed)
        act.append(window_mean(frames))
        full.append(behavioral.features(rollout, config))
    full_matrix = np.stack(full)
    np.savez(args.output, ids=np.array(ids), failed=np.array(failed), act=np.stack(act).astype(np.float32),
             kin=full_matrix[:, kin_columns], full=full_matrix)
    print(f"{len(ids)} rollouts, {int(np.sum(failed))} failed, act dim {np.stack(act).shape[1]}")


if __name__ == "__main__":
    main()
