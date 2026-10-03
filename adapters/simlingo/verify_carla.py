"""Verify a real CARLA camera, synchronous ticks, and vehicle control."""
from __future__ import annotations

import argparse
import json
import queue
import time
from pathlib import Path
from typing import Any

import carla
import numpy as np
from PIL import Image


def camera_frame(images: queue.Queue[Any], expected: int) -> Any:
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        image = images.get(timeout=max(0.01, deadline - time.monotonic()))
        if image.frame == expected:
            return image
        if image.frame > expected:
            raise RuntimeError(f"Camera skipped simulation frame {expected}")
    raise TimeoutError("No matching camera frame")


def save_image(image: Any, path: Path) -> dict[str, float]:
    rgba = np.frombuffer(image.raw_data, dtype=np.uint8).reshape(image.height, image.width, 4)
    rgb = rgba[:, :, :3][:, :, ::-1].copy()
    statistics = {"mean": float(rgb.mean()), "std": float(rgb.std())}
    if statistics["mean"] < 1 or statistics["std"] < 1:
        raise RuntimeError(f"Camera image is black or uniform: {statistics}")
    Image.fromarray(rgb).save(path)
    return statistics


def spawn_vehicle(world: Any) -> Any:
    blueprint = world.get_blueprint_library().find("vehicle.lincoln.mkz_2020")
    blueprint.set_attribute("role_name", "hero")
    for transform in world.get_map().get_spawn_points():
        vehicle = world.try_spawn_actor(blueprint, transform)
        if vehicle is not None:
            return vehicle
    raise RuntimeError("No free vehicle spawn point")


def follow_vehicle(world: Any, vehicle: Any) -> None:
    transform = vehicle.get_transform()
    offset = transform.get_forward_vector() * -6
    location = transform.location + offset + carla.Location(z=3)
    world.get_spectator().set_transform(carla.Transform(
        location, carla.Rotation(pitch=-15, yaw=transform.rotation.yaw),
    ))


def simulate(world: Any, vehicle: Any, images: queue.Queue[Any], output: Path, ticks: int) -> dict[str, Any]:
    first = vehicle.get_location()
    start = time.monotonic()
    statistics = {}
    vehicle.apply_control(carla.VehicleControl(throttle=0.35))
    for index in range(ticks):
        follow_vehicle(world, vehicle)
        frame = world.tick(30)
        image = camera_frame(images, frame)
        print(f"Tick {index + 1}/{ticks}: camera frame {frame}", flush=True)
        if index in (0, ticks - 1):
            statistics[str(index)] = save_image(image, output / f"camera-{index:04d}.png")
    distance = first.distance(vehicle.get_location())
    if distance < 1:
        raise RuntimeError(f"Vehicle did not move: {distance:.3f} metres")
    wall_seconds = time.monotonic() - start
    return {
        "ticks": ticks, "simulated_seconds": ticks * 0.05,
        "wall_seconds": wall_seconds, "real_time_factor": ticks * 0.05 / wall_seconds,
        "distance_metres": distance, "camera_pixels": statistics,
        "camera_verified": True, "control_verified": True,
        "scope": "camera_and_control_smoke", "simlingo_route_verified": False,
    }


def verify(client: Any, output: Path, ticks: int) -> dict[str, Any]:
    versions = {"client": client.get_client_version(), "server": client.get_server_version()}
    print(f"CARLA versions: {versions}", flush=True)
    if versions["server"] != "0.9.15" or versions["client"] not in {"0.9.15", "0.9.15-macclient"}:
        raise RuntimeError(f"CARLA version mismatch: {versions}")
    world = client.get_world()
    print(f"Connected to {world.get_map().name}", flush=True)
    settings, weather = world.get_settings(), world.get_weather()
    spectator = world.get_spectator().get_transform()
    actors = []
    try:
        world.set_weather(carla.WeatherParameters.ClearNoon)
        vehicle = spawn_vehicle(world)
        actors.append(vehicle)
        blueprint = world.get_blueprint_library().find("sensor.camera.rgb")
        for key, value in {"image_size_x": "1280", "image_size_y": "720", "fov": "110"}.items():
            blueprint.set_attribute(key, value)
        camera = world.spawn_actor(blueprint, carla.Transform(carla.Location(x=-1.5, z=2)), attach_to=vehicle)
        actors.append(camera)
        images: queue.Queue[Any] = queue.Queue()
        camera.listen(images.put)
        first_image = images.get(timeout=30)
        print(f"Camera started at frame {first_image.frame}", flush=True)
        save_image(first_image, output / "camera-start.png")
        synchronous = world.get_settings()
        synchronous.synchronous_mode = True
        synchronous.fixed_delta_seconds = 0.05
        synchronous.no_rendering_mode = False
        world.apply_settings(synchronous)
        print("Synchronous settings applied", flush=True)
        for _ in range(10):
            print(f"Warmup frame {world.tick(30)}", flush=True)
            time.sleep(0.1)
        report = simulate(world, vehicle, images, output, ticks)
        report.update({"versions": versions, "map": world.get_map().name})
        return report
    finally:
        for actor in reversed(actors):
            if isinstance(actor, carla.Sensor):
                actor.stop()
            actor.destroy()
        world.set_weather(weather)
        world.get_spectator().set_transform(spectator)
        world.apply_settings(settings)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=2000)
    parser.add_argument("--ticks", type=int, default=100)
    parser.add_argument("--output", type=Path, default=Path("results/setup/carla-smoke"))
    args = parser.parse_args()
    if args.ticks < 2:
        parser.error("--ticks must be at least 2")
    args.output.mkdir(parents=True, exist_ok=True)
    client = carla.Client(args.host, args.port)
    client.set_timeout(30)
    report = verify(client, args.output, args.ticks)
    (args.output / "result.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
