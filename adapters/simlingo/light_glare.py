"""Where traffic lights land in the policy camera's image, for the traffic_light_glare camera fault (practice gap P9).

Nothing here imports CARLA: `visible_agent.py` supplies the lights' world-space box corners and the ego transform.
CARLA's camera frame is x forward, y right, z up.
"""
from __future__ import annotations

import numpy as np

NEAREST_VISIBLE_M = 0.5
MIN_PADDING_PX = 4


def camera_to_world(ego_matrix: np.ndarray, mount_xyz: tuple[float, float, float]) -> np.ndarray:
    """The camera's local-to-world matrix: mounted at `mount_xyz` in the ego frame, with no rotation relative to it."""
    mount = np.eye(4)
    mount[:3, 3] = mount_xyz
    return ego_matrix @ mount


def project(corners_in_camera: np.ndarray, width: int, height: int, fov_degrees: float) -> np.ndarray:
    focal = width / (2 * np.tan(np.radians(fov_degrees) / 2))
    x, y, z = corners_in_camera.T
    return np.stack([width / 2 + focal * y / x, height / 2 - focal * z / x], axis=1)


def padded_rect(pixels: np.ndarray, width: int, height: int) -> tuple[int, int, int, int] | None:
    """The corners' bounding rectangle, grown by half its size on each side and clipped to the image."""
    (left, top), (right, bottom) = pixels.min(axis=0), pixels.max(axis=0)
    pad_x = max((right - left) / 2, MIN_PADDING_PX)
    pad_y = max((bottom - top) / 2, MIN_PADDING_PX)
    x0, x1 = max(int(np.floor(left - pad_x)), 0), min(int(np.ceil(right + pad_x)), width)
    y0, y1 = max(int(np.floor(top - pad_y)), 0), min(int(np.ceil(bottom + pad_y)), height)
    return (x0, y0, x1, y1) if x0 < x1 and y0 < y1 else None


def glare_rects(world_to_camera: np.ndarray, boxes: list[np.ndarray], width: int, height: int,
                fov_degrees: float) -> list[tuple[int, int, int, int]]:
    """A padded pixel rectangle (x0, y0, x1, y1, end exclusive) for each box, given as 8 world corners, in front of the lens."""
    rects = []
    for corners in boxes:
        homogeneous = np.c_[corners, np.ones(len(corners))]
        in_camera = (world_to_camera @ homogeneous.T).T[:, :3]
        if (in_camera[:, 0] < NEAREST_VISIBLE_M).any():
            continue
        rect = padded_rect(project(in_camera, width, height, fov_degrees), width, height)
        if rect is not None:
            rects.append(rect)
    return rects
