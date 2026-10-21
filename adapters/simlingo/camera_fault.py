"""Camera faults applied to the policy's frame before the model sees it (practice gap P4, Step 5)."""
from __future__ import annotations

from collections import deque
from collections.abc import Callable
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


Rect = tuple[int, int, int, int]
KINDS = (None, "occlusion", "freeze", "latency", "traffic_light_glare")


class CameraFault:
    """Applies one fault per policy step, keeping the frames the time-based faults need.

    occlusion            stateless, as apply_camera_fault.
    freeze               every `period_steps` steps, for `duration_steps` steps, the policy keeps seeing the frame
                         from the step before the freeze began (a stalled camera); `offset_steps` delays the first
                         freeze.
    latency              the policy sees the frame from `delay_steps` steps earlier (the first frames repeat the
                         oldest held).
    traffic_light_glare  every rectangle from `light_rects()` (pixels x0, y0, x1, y1, end exclusive; the traffic
                         lights in view, padded) is painted saturated white, alpha untouched. `glare_boxes` is how
                         many were painted on the last step.

    `age_steps` is how many policy steps old the frame last returned is: 0 unless freeze or latency holds one back.
    """

    def __init__(self, fault: dict[str, Any] | None, light_rects: Callable[[], list[Rect]] | None = None) -> None:
        spec: dict[str, Any] = fault or {}
        self.fault = spec or None
        self.step = 0
        self.age_steps = 0
        self.glare_boxes = 0
        self.light_rects = light_rects
        kind = spec.get("kind")
        if kind not in KINDS:
            raise ValueError(f"Unknown camera fault {fault!r}")
        if kind == "freeze" and not 0 < spec["duration_steps"] < spec["period_steps"]:
            raise ValueError("freeze needs 0 < duration_steps < period_steps")
        if kind == "latency" and spec["delay_steps"] < 1:
            raise ValueError("latency needs delay_steps >= 1")
        if kind == "traffic_light_glare" and light_rects is None:
            raise ValueError("traffic_light_glare needs a light_rects provider")
        self.held: np.ndarray | None = None
        self.held_step = 0
        self.history: deque[np.ndarray] = deque(maxlen=spec.get("delay_steps", 0) + 1)

    def __call__(self, bgra: np.ndarray) -> np.ndarray:
        step, self.step = self.step, self.step + 1
        if not self.fault:
            return bgra
        kind = self.fault["kind"]
        if kind == "occlusion":
            return apply_camera_fault(bgra, self.fault)
        if kind == "latency":
            return self._delayed(bgra, step)
        if kind == "traffic_light_glare":
            return self._glared(bgra)
        return self._frozen(bgra, step)

    def _delayed(self, bgra: np.ndarray, step: int) -> np.ndarray:
        self.history.append(bgra.copy())
        self.age_steps = min(step, self.fault["delay_steps"])
        return self.history[0]

    def _frozen(self, bgra: np.ndarray, step: int) -> np.ndarray:
        phase = step - self.fault.get("offset_steps", 0)
        frozen = phase >= 0 and phase % self.fault["period_steps"] < self.fault["duration_steps"]
        if not frozen or self.held is None:
            self.held, self.held_step = bgra.copy(), step
        self.age_steps = step - self.held_step
        return self.held if self.age_steps else bgra

    def _glared(self, bgra: np.ndarray) -> np.ndarray:
        assert self.light_rects is not None
        rects = self.light_rects()
        self.glare_boxes = len(rects)
        glared = bgra.copy()
        for x0, y0, x1, y1 in rects:
            glared[y0:y1, x0:x1, :3] = 255
        return glared
