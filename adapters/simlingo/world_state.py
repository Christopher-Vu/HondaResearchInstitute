"""Read the hero's ground-truth surroundings from the running CARLA world, once per policy step."""
from __future__ import annotations

import math
from typing import Any

import carla
from state_geometry import (EgoFrame, Neighbour, blocked_before_target, find_lead, is_nearby, junction_distance,
                            lead_relative_speed, nearest_pedestrian, occlusion_target, time_to_junction)

BUMPER_CLEARANCE = 0.3


def vector_length(vector: Any) -> float:
    return math.sqrt(vector.x ** 2 + vector.y ** 2 + vector.z ** 2)


def distance_or_none(neighbour: Neighbour | None) -> float | None:
    return None if neighbour is None else neighbour.distance


def neighbour_of(frame: EgoFrame, actor: Any) -> Neighbour | None:
    location = actor.get_transform().location
    forward, right, up = frame.locate(location.x, location.y, location.z)
    if not is_nearby(forward, right, up):
        return None
    velocity = actor.get_velocity()
    extent = actor.bounding_box.extent
    return Neighbour(forward, right, up, frame.forward_component(velocity.x, velocity.y),
                     max(extent.x, extent.y, extent.z), actor)


class WorldStateReader:
    def __init__(self, ego: Any, world: Any, carla_map: Any, camera_height: float) -> None:
        self.ego, self.world, self.carla_map = ego, world, carla_map
        box = ego.bounding_box
        self.bumper_x = box.location.x + box.extent.x + BUMPER_CLEARANCE
        self.camera_height = camera_height

    def read(self) -> dict[str, Any]:
        transform = self.ego.get_transform()
        frame = EgoFrame(transform.location.x, transform.location.y, transform.location.z, transform.rotation.yaw)
        ego_speed = vector_length(self.ego.get_velocity())
        actors = self.world.get_actors()
        vehicles = self._neighbours(frame, actors.filter("vehicle.*"))
        walkers = self._neighbours(frame, actors.filter("walker.pedestrian.*"))
        lead = find_lead(vehicles)
        pedestrian = nearest_pedestrian(walkers)
        junction = junction_distance(self.carla_map.get_waypoint(transform.location))
        return {
            "ego_speed": ego_speed,
            "lead_distance": distance_or_none(lead),
            "lead_relative_speed": lead_relative_speed(ego_speed, lead),
            "pedestrian_distance": distance_or_none(pedestrian),
            "traffic_light": self._traffic_light(),
            "junction_distance": junction,
            "time_to_junction": time_to_junction(junction, ego_speed),
            "occluded": self._occluded(transform, occlusion_target(lead, walkers)),
        }

    def _neighbours(self, frame: EgoFrame, actors: Any) -> list[Neighbour]:
        nearby = (neighbour_of(frame, actor) for actor in actors if actor.id != self.ego.id)
        return [neighbour for neighbour in nearby if neighbour is not None]

    def _traffic_light(self) -> str:
        if not self.ego.is_at_traffic_light():
            return "none"
        return self.ego.get_traffic_light_state().name.lower()

    def _occluded(self, ego_transform: Any, target: Neighbour | None) -> bool | None:
        if target is None:
            return None
        # Transform.transform rewrites its argument in place, so every point is built fresh.
        start = ego_transform.transform(carla.Location(x=self.bumper_x, z=self.camera_height))
        centre = target.actor.bounding_box.location
        goal = target.actor.get_transform().transform(carla.Location(centre.x, centre.y, centre.z))
        # A walker returns unlabelled hits about two metres in front of itself; only labelled hits occlude.
        hits = [hit for hit in self.world.cast_ray(start, goal) if hit.label != carla.CityObjectLabel.NONE]
        return blocked_before_target([start.distance(hit.location) for hit in hits], start.distance(goal), target.extent)
