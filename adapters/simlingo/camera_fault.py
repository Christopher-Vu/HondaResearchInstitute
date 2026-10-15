"""Camera faults applied to the policy's frame before the model sees it (practice gap P4, Step 5)."""
from __future__ import annotations

from collections import deque
from typing import Any

import numpy as np


def apply_camera_fault(bgra: np.ndarray, fault: dict[str, Any] | None) -> np.ndarray:
    """A copy of the frame with the fault applied: `occlusion` blacks out `box`, [x0, y0, x1, y1] as fractions."""
    if not fault:
        return bgra
    if fault.get("kind") != "occlusion":
        raise ValueError(f"Unknown camera fault {fault!r}")
    height, width = bgra.shape[:2]
    x0, y0, x1, y1 = fault["box"]
    faulty = bgra.copy()
    faulty[round(y0 * height):round(y1 * height), round(x0 * width):round(x1 * width), :3] = 0
    return faulty


class CameraFault:
    """Applies one fault per policy step, keeping the frames the time-based faults need.

    occlusion  stateless, as apply_camera_fault.
    freeze     every `period_steps` steps, for `duration_steps` steps, the policy keeps seeing the frame from the
               step before the freeze began (a stalled camera); `offset_steps` delays the first freeze.
    latency    the policy sees the frame from `delay_steps` steps earlier (the first frames repeat the oldest held).
    """

    def __init__(self, fault: dict[str, Any] | None) -> None:
        spec: dict[str, Any] = fault or {}
        self.fault = spec or None
        self.step = 0
        kind = spec.get("kind")
        if kind not in (None, "occlusion", "freeze", "latency"):
            raise ValueError(f"Unknown camera fault {fault!r}")
        if kind == "freeze" and not 0 < spec["duration_steps"] < spec["period_steps"]:
            raise ValueError("freeze needs 0 < duration_steps < period_steps")
        if kind == "latency" and spec["delay_steps"] < 1:
            raise ValueError("latency needs delay_steps >= 1")
        self.held: np.ndarray | None = None
        self.history: deque[np.ndarray] = deque(maxlen=spec.get("delay_steps", 0) + 1)

    def __call__(self, bgra: np.ndarray) -> np.ndarray:
        step, self.step = self.step, self.step + 1
        if not self.fault:
            return bgra
        kind = self.fault["kind"]
        if kind == "occlusion":
            return apply_camera_fault(bgra, self.fault)
        if kind == "latency":
            self.history.append(bgra.copy())
            return self.history[0]
        phase = step - self.fault.get("offset_steps", 0)
        frozen = phase >= 0 and phase % self.fault["period_steps"] < self.fault["duration_steps"]
        if not frozen or self.held is None:
            self.held = bgra.copy()
            return bgra
        return self.held
