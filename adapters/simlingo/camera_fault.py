"""Camera faults applied to the policy's frame before the model sees it (practice gap P4, Step 5)."""
from __future__ import annotations

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
