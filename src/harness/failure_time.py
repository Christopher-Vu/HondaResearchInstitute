"""When a failing rollout failed: the step its first infraction of any kind happened, from a shard.

Contrastive, probe-residual and B3 end a failing rollout's window here; None means "use its last 3 s", which is
right only for a pure timeout. Bench2Drive logs collisions with a time (the capture's collision steps) but most
other infractions with a location only, so:

- Shards that log ego x/y (captures from 2026-10-19 on) time each located infraction at the earliest step within
  LOCATED_TOLERANCE_M of the ego's nearest approach to it, so a blocked ego is timed where it stopped.
- Older shards use proxies: a red light at the first step the ego leaves a red light while moving, and a blocked
  ego at the start of its final stationary stretch.

Infractions with neither a location nor a proxy (outside_route_lanes, timeouts) are not timed. A failing rollout
whose infractions are all untimed gets None.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import numpy as np

LOCATED_TOLERANCE_M = 0.5
# A logged location further than this from every ego position is a parse or map mismatch, not a time.
LOCATED_MAX_M = 10.0
MOVING_SPEED = 1.0
STATIONARY_SPEED = 0.1


def located_step(steps: np.ndarray, x: np.ndarray, y: np.ndarray, point: list[float]) -> int | None:
    distance = np.hypot(x - point[0], y - point[1])
    if not np.isfinite(distance).any() or np.nanmin(distance) > LOCATED_MAX_M:
        return None
    return int(steps[np.flatnonzero(distance <= np.nanmin(distance) + LOCATED_TOLERANCE_M)[0]])


def red_light_step(steps: np.ndarray, red: np.ndarray, speed: np.ndarray) -> int | None:
    """The step after the ego last sat at a red light while moving, i.e. when it drove through."""
    at_red = red == 1
    for row in np.flatnonzero(at_red[:-1] & ~at_red[1:]):
        if speed[row] > MOVING_SPEED:
            return int(steps[row + 1])
    return None


def blocked_step(steps: np.ndarray, speed: np.ndarray) -> int | None:
    moving = np.flatnonzero(~(speed < STATIONARY_SPEED))
    if len(moving) and moving[-1] == len(speed) - 1:
        return None
    return int(steps[moving[-1] + 1]) if len(moving) else int(steps[0])


def failure_step(meta: Mapping[str, Any], arrays: Mapping[str, np.ndarray]) -> int | None:
    """`meta` is a shard's json sidecar, `arrays` its npz (step, and whichever state arrays it has)."""
    if meta.get("success") is not False:
        return None
    steps = np.asarray(arrays["step"], dtype=np.int64)
    times = [] if meta.get("first_collision_step") is None else [int(meta["first_collision_step"])]
    x, y = arrays.get("ego_x"), arrays.get("ego_y")
    if x is not None and y is not None and np.isfinite(x).any():
        times += [located_step(steps, np.asarray(x, np.float64), np.asarray(y, np.float64), point)
                  for name, points in (meta.get("infraction_locations") or {}).items()
                  if not name.startswith("collisions_") for point in points]
    else:
        infractions = meta.get("infractions") or {}
        speed = arrays.get("ego_speed")
        if speed is not None and "red_light" in infractions and arrays.get("red_light") is not None:
            times.append(red_light_step(steps, np.asarray(arrays["red_light"]), np.asarray(speed)))
        if speed is not None and "vehicle_blocked" in infractions:
            times.append(blocked_step(steps, np.asarray(speed)))
    return min((time for time in times if time is not None), default=None)
