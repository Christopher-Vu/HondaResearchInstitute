"""Geometry behind the per-step ground-truth state that probes decode from activations (PRD 9.2).

Nothing here imports CARLA or torch: `world_state.py` turns CARLA actors into `Neighbour`s and
these functions pick the lead vehicle, the occlusion target and the junction distance.
"""
from __future__ import annotations

import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any

NEIGHBOUR_RADIUS = 60.0
# Scenarios park walkers and vehicles 50 to 200 m under the map until they trigger.
MAX_VERTICAL_SEPARATION = 20.0
LANE_HALF_WIDTH = 1.75
LEAD_RANGE = 50.0
PEDESTRIAN_RANGE = 50.0
OCCLUSION_WALKER_RANGE = 40.0
OCCLUSION_MARGIN = 0.5
JUNCTION_RANGE = 50.0
JUNCTION_STEP = 1.0
SLOWEST_DIVISOR_SPEED = 0.5
LONGEST_TIME_TO_JUNCTION = 30.0


@dataclass(frozen=True)
class EgoFrame:
    """The ego's position and heading; CARLA yaw turns x toward y, so right is (-sin, cos)."""
    x: float
    y: float
    z: float
    yaw_degrees: float

    def locate(self, x: float, y: float, z: float) -> tuple[float, float, float]:
        yaw = math.radians(self.yaw_degrees)
        dx, dy = x - self.x, y - self.y
        return dx * math.cos(yaw) + dy * math.sin(yaw), -dx * math.sin(yaw) + dy * math.cos(yaw), z - self.z

    def forward_component(self, velocity_x: float, velocity_y: float) -> float:
        yaw = math.radians(self.yaw_degrees)
        return velocity_x * math.cos(yaw) + velocity_y * math.sin(yaw)


@dataclass(frozen=True)
class Neighbour:
    """Another road user in the ego frame; `extent` is the largest half-size of its bounding box."""
    forward: float
    right: float
    up: float
    forward_speed: float
    extent: float
    actor: Any = None

    @property
    def distance(self) -> float:
        return math.sqrt(self.forward ** 2 + self.right ** 2 + self.up ** 2)


def is_nearby(forward: float, right: float, up: float) -> bool:
    return math.hypot(forward, right) <= NEIGHBOUR_RADIUS and abs(up) <= MAX_VERTICAL_SEPARATION


def find_lead(vehicles: Iterable[Neighbour]) -> Neighbour | None:
    in_lane = (vehicle for vehicle in vehicles
               if 0 < vehicle.forward <= LEAD_RANGE and abs(vehicle.right) <= LANE_HALF_WIDTH)
    return min(in_lane, key=lambda vehicle: vehicle.distance, default=None)


def nearest_pedestrian(walkers: Iterable[Neighbour]) -> Neighbour | None:
    close = (walker for walker in walkers if walker.distance <= PEDESTRIAN_RANGE)
    return min(close, key=lambda walker: walker.distance, default=None)


def occlusion_target(lead: Neighbour | None, walkers: Iterable[Neighbour]) -> Neighbour | None:
    ahead = [walker for walker in walkers if walker.forward > 0 and walker.distance <= OCCLUSION_WALKER_RANGE]
    candidates = ahead if lead is None else [*ahead, lead]
    return min(candidates, key=lambda target: target.distance, default=None)


def lead_relative_speed(ego_speed: float, lead: Neighbour | None) -> float | None:
    return None if lead is None else ego_speed - lead.forward_speed


def blocked_before_target(hit_distances: Sequence[float], target_distance: float, target_extent: float) -> bool:
    """A hit nearer than the target's own surface means something stands in between.

    Distances are all measured from the ray's start; the target's front face lies within one
    extent of its centre, so hits that close are the target itself.
    """
    return any(hit < target_distance - target_extent - OCCLUSION_MARGIN for hit in hit_distances)


def junction_distance(waypoint: Any) -> float | None:
    """Metres along the lane to the first junction waypoint, 0 inside one, None beyond the range."""
    if waypoint.is_junction:
        return 0.0
    travelled = 0.0
    while travelled < JUNCTION_RANGE:
        following = waypoint.next(JUNCTION_STEP)
        if not following:
            return None
        waypoint = following[0]
        travelled += JUNCTION_STEP
        if waypoint.is_junction:
            return travelled
    return None


def time_to_junction(distance: float | None, ego_speed: float) -> float | None:
    if distance is None:
        return None
    return min(distance / max(ego_speed, SLOWEST_DIVISOR_SPEED), LONGEST_TIME_TO_JUNCTION)
