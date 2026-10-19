"""A deliberately minimal adapter (PRD 8.2): a policy nobody would mistake for SimLingo, meeting the shard contract.

    python adapters/stub/stub_adapter.py --output <shard dir> [--episodes 240] [--seed 0]

The environment is a straight 120 m road at 20 steps per second. A lead car may drive ahead; a pedestrian may
step into the lane in front of the ego; fog may be on. The policy is a two-layer numpy network over what the ego
*perceives*, with a linear read-out fitted by ridge regression to an expert's acceleration on clear-weather
episodes. Fog makes a pedestrian look 15 m further away than it is, so the policy brakes late for pedestrians
in fog and nowhere else (fog is in the fitting data too, so fog alone is familiar): a planted gap whose
failing rollouts are known exactly. Its hidden layers are the
activation site (`mlp`, two layers of 32 units).

Each episode writes `<id>.json` and `<id>.npz` as `src/harness/shards.py` specifies, plus the episode's
generation metadata (`fog`, `pedestrian`, `lead_car`) in the sidecar, which a gap predicate would read.
Nothing here imports from the rest of the repository: the contract is the files.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

STEPS_PER_SECOND = 20
DT = 1.0 / STEPS_PER_SECOND
ROAD_M, MAX_SECONDS, CRUISE = 120.0, 25.0, 10.0
SENSOR_RANGE, FOG_ERROR_M = 50.0, 15.0
HIDDEN, LAYERS = 32, 2


def expert_acceleration(perceived: np.ndarray) -> float:
    """Brake for whatever is closer than the stopping distance plus margin; otherwise cruise."""
    pedestrian, lead, _relative, speed = perceived[:4]
    stopping = speed ** 2 / (2 * 6.0) + 6.0
    if min(pedestrian, lead) < stopping:
        return -8.0
    return float(np.clip(CRUISE - speed, -2.0, 2.0))


class Policy:
    def __init__(self, seed: int) -> None:
        rng = np.random.default_rng(seed)
        self.weights = [rng.normal(scale=1 / np.sqrt(5), size=(5, HIDDEN)),
                        rng.normal(scale=1 / np.sqrt(HIDDEN), size=(HIDDEN, HIDDEN))]
        self.biases = [rng.normal(scale=0.1, size=HIDDEN) for _ in range(LAYERS)]
        self.readout = np.zeros(HIDDEN + 1)

    def hidden(self, perceived: np.ndarray, visibility: float) -> np.ndarray:
        x = np.append(perceived / [SENSOR_RANGE, SENSOR_RANGE, 10.0, CRUISE], visibility)
        layers = []
        for weights, bias in zip(self.weights, self.biases):
            x = np.maximum(x @ weights + bias, 0.0)
            layers.append(x)
        return np.stack(layers)

    def act(self, layers: np.ndarray) -> float:
        return float(np.clip(np.append(layers[-1], 1.0) @ self.readout, -8.0, 2.0))

    def fit(self, observations: list[tuple[np.ndarray, float]], ridge: float = 1e-2) -> None:
        features = np.stack([np.append(self.hidden(p, v)[-1], 1.0) for p, v in observations])
        targets = np.array([expert_acceleration(p) for p, _ in observations])
        self.readout = np.linalg.solve(features.T @ features + ridge * np.eye(features.shape[1]),
                                       features.T @ targets)


def episode_setup(rng: np.random.Generator, index: int) -> dict:
    return {"id": f"stub{index:04d}", "base_id": f"road{index // 2:04d}", "fog": bool(rng.random() < 0.4),
            "pedestrian": bool(rng.random() < 0.5), "lead_car": bool(rng.random() < 0.5),
            "pedestrian_at": float(rng.uniform(45, 75)), "lead_gap": float(rng.uniform(20, 40)),
            "lead_speed": float(rng.uniform(5, 8)), "lead_brakes_at": float(rng.uniform(3, 10)),
            "crossing_seconds": float(rng.uniform(2.5, 4.0))}


def perceive(setup: dict, x: float, speed: float, lead_x: float, lead_speed: float, crossing: bool) -> np.ndarray:
    pedestrian = setup["pedestrian_at"] - x if crossing and setup["pedestrian_at"] > x else SENSOR_RANGE
    if setup["fog"] and pedestrian < SENSOR_RANGE:
        pedestrian += FOG_ERROR_M
    lead = lead_x - x if setup["lead_car"] else SENSOR_RANGE
    relative = speed - lead_speed if setup["lead_car"] else 0.0
    return np.array([min(pedestrian, SENSOR_RANGE), min(lead, SENSOR_RANGE), relative, speed])


def drive(setup: dict, policy: Policy | None, observations: list | None = None) -> dict:
    """One episode; with no policy the expert drives (to collect fitting data)."""
    x, speed = 0.0, 0.0
    lead_x, lead_speed = setup["lead_gap"], setup["lead_speed"]
    visibility = 0.5 if setup["fog"] else 1.0
    rows, collision, crossing_since = [], None, None
    for step in range(int(MAX_SECONDS * STEPS_PER_SECOND)):
        t = step * DT
        if setup["pedestrian"] and crossing_since is None and setup["pedestrian_at"] - x < 30.0:
            crossing_since = t
        crossing = crossing_since is not None and t - crossing_since < setup["crossing_seconds"]
        perceived = perceive(setup, x, speed, lead_x, lead_speed, crossing)
        if observations is not None:
            observations.append((perceived, visibility))
        layers = policy.hidden(perceived, visibility) if policy else np.zeros((LAYERS, HIDDEN))
        acceleration = policy.act(layers) if policy else expert_acceleration(perceived)
        truth = perceived.copy()
        truth[0] = setup["pedestrian_at"] - x if crossing and setup["pedestrian_at"] > x else np.nan
        rows.append((step, layers, truth, x))
        speed = max(0.0, speed + acceleration * DT)
        x += speed * DT
        if setup["lead_car"]:
            braking = setup["lead_brakes_at"] < t < setup["lead_brakes_at"] + 1.0
            lead_speed = float(np.clip(lead_speed + (-6.0 if braking else 1.0) * DT, 0.0, setup["lead_speed"]))
            lead_x += lead_speed * DT
        if crossing and abs(setup["pedestrian_at"] - x) < 1.0 and speed > 1.0:
            collision = ("collisions_pedestrian", step)
        elif setup["lead_car"] and lead_x - x < 1.0:
            collision = ("collisions_vehicle", step)
        if collision or x >= ROAD_M:
            break
    timed_out = collision is None and x < ROAD_M
    infractions = {collision[0]: 1} if collision else {"route_timeout": 1} if timed_out else {}
    return {"rows": rows, "success": not infractions, "infractions": infractions,
            "first_collision_step": collision[1] if collision else None}


def write_shard(output: Path, setup: dict, result: dict) -> None:
    steps, layers, truth, xs = zip(*result["rows"])
    activations = np.stack(layers).astype(np.float32)
    truth = np.stack(truth)
    np.savez(output / f"{setup['id']}.npz", step=np.asarray(steps, dtype=np.int32), mlp=activations,
             mlp_episode_mean=activations.mean(axis=0),
             pedestrian_distance=truth[:, 0].astype(np.float32),
             lead_distance=np.where(truth[:, 1] < SENSOR_RANGE, truth[:, 1], np.nan).astype(np.float32),
             lead_relative_speed=truth[:, 2].astype(np.float32), ego_speed=truth[:, 3].astype(np.float32),
             ego_x=np.asarray(xs, dtype=np.float32), ego_y=np.zeros(len(xs), dtype=np.float32))
    meta = {"route_id": setup["id"], "base_id": setup["base_id"], "success": result["success"],
            "infractions": result["infractions"], "first_collision_step": result["first_collision_step"],
            "fog": setup["fog"], "pedestrian": setup["pedestrian"], "lead_car": setup["lead_car"]}
    (output / f"{setup['id']}.json").write_text(json.dumps(meta, indent=2) + "\n")


def generate(output: Path, episodes: int = 240, seed: int = 0) -> list[dict]:
    """Fit the policy on the expert's driving, then roll it out; returns each episode's sidecar."""
    rng = np.random.default_rng(seed)
    policy = Policy(seed)
    observations: list = []
    for index in range(100):
        drive(episode_setup(rng, index), None, observations)
    policy.fit(observations)
    output.mkdir(parents=True, exist_ok=True)
    for index in range(episodes):
        setup = episode_setup(rng, index)
        write_shard(output, setup, drive(setup, policy))
    return [json.loads(path.read_text()) for path in sorted(output.glob("*.json"))]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--episodes", type=int, default=240)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    metas = generate(args.output, args.episodes, args.seed)
    print(f"{len(metas)} episodes, {sum(not m['success'] for m in metas)} failed, in {args.output}")


if __name__ == "__main__":
    main()
