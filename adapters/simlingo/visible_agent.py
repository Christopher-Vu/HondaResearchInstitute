"""Show the policy's existing camera feed and record its returned controls."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, TextIO

import numpy as np
from PIL import Image
from agent_simlingo import LingoAgent
from camera_fault import CameraFault
from light_glare import LightBoxCache, camera_to_world, glare_rects


GLARE_RANGE_M = 80.0


def get_entry_point() -> str:
    return "VisibleAgent"


class VisibleAgent(LingoAgent):
    def setup(self, path_to_conf_file: str, route_index: Any = None) -> None:
        self.view: subprocess.Popen[bytes] | None = None
        self.trace: TextIO | None = None
        super().setup(path_to_conf_file, route_index)
        self.evidence = Path(os.environ["SIMLINGO_EVIDENCE"])
        fault = json.loads(os.environ.get("SIMLINGO_CAMERA_FAULT", "null"))
        self.lights: Any = None
        self.light_boxes: LightBoxCache | None = None
        self.camera_fault = CameraFault(fault, self._light_rects if (fault or {}).get("kind") == "traffic_light_glare"
                                        else None)
        (self.evidence / "frames").mkdir(parents=True, exist_ok=True)
        self.trace = (self.evidence / "controls.jsonl").open("w")
        if os.environ.get("SIMLINGO_VISIBLE", "1") == "1":
            root = Path(__file__).resolve().parents[2]
            viewer_environment = os.environ.copy()
            viewer_environment["__PYVENV_LAUNCHER__"] = sys.executable
            viewer_environment["SDL_NO_SIGNAL_HANDLERS"] = "1"
            self.view = subprocess.Popen([
                str(root / ".runtime/CARLA Camera.app/Contents/MacOS/Python"),
                str(Path(__file__).with_name("camera_view.py")), str(self.evidence), str(self.device),
            ], env=viewer_environment)

    def _light_rects(self) -> list[tuple[int, int, int, int]]:
        """Pixel rectangles of the traffic lights within GLARE_RANGE_M of the ego, as the policy camera sees them."""
        import carla
        from srunner.scenariomanager.carla_data_provider import CarlaDataProvider
        ego = CarlaDataProvider.get_hero_actor()
        if self.lights is None:
            self.lights = CarlaDataProvider.get_world().get_actors().filter("traffic.traffic_light")
            self.light_boxes = LightBoxCache(lambda light: [
                np.array([[v.x, v.y, v.z] for v in box.get_world_vertices(carla.Transform())])
                for box in light.get_light_boxes()])
        location = ego.get_location()
        here = np.array([location.x, location.y])
        nearby = [corners for corners in self.light_boxes.boxes(self.lights)
                  if np.linalg.norm(corners.mean(axis=0)[:2] - here) < GLARE_RANGE_M]
        camera = camera_to_world(np.array(ego.get_transform().get_matrix()), tuple(self.config.camera_pos_0))
        return glare_rects(np.linalg.inv(camera), nearby, self.config.camera_width_0, self.config.camera_height_0,
                           self.config.camera_fov_0)

    def run_step(self, input_data: Any, timestamp: float, sensors: Any = None) -> Any:
        frame, bgra = input_data["rgb_0"]
        bgra = self.camera_fault(bgra)
        input_data["rgb_0"] = (frame, bgra)
        rgb = np.ascontiguousarray(bgra[:, :, :3][:, :, ::-1])
        # A failed render is flat. Night routes can average under 1/255 yet still vary (std above 5).
        if rgb.std() < 1:
            raise RuntimeError("CARLA supplied a uniform policy camera frame")
        if self.view is not None and self.view.poll() is not None:
            if self.view.returncode == 0:
                raise KeyboardInterrupt
            raise RuntimeError("The camera viewer failed; inspect evaluator.log")
        started = time.monotonic()
        control = super().run_step(input_data, timestamp, sensors)
        record = {
            "step": self.step, "frame": frame, "simulation_seconds": timestamp,
            "wall_step_seconds": time.monotonic() - started,
            "speed_metres_per_second": float(input_data["speed"][1]["speed"]),
            "throttle": float(control.throttle), "steer": float(control.steer),
            "brake": float(control.brake), "model_inference": self.step > 0,
            "camera_mean": float(rgb.mean()), "camera_std": float(rgb.std()),
            "camera_frame_age_steps": self.camera_fault.age_steps,
        }
        if self.camera_fault.light_rects is not None:
            record["glare_boxes"] = self.camera_fault.glare_boxes
        if not all(np.isfinite(record[key]) for key in ("throttle", "steer", "brake")):
            raise RuntimeError("SimLingo returned non-finite vehicle controls")
        assert self.trace is not None
        self.trace.write(json.dumps(record) + "\n")
        self.trace.flush()
        if self.step % 20 == 0:
            Image.fromarray(rgb).save(self.evidence / "frames" / f"{self.step:06d}.png")
        pending = self.evidence / "last-camera.tmp.png"
        Image.fromarray(rgb).save(pending)
        pending.replace(self.evidence / "last-camera.png")
        print(f"SimLingo step {self.step}: speed={record['speed_metres_per_second']:.2f} "
              f"throttle={control.throttle:.3f} steer={control.steer:.3f} brake={control.brake:.3f}", flush=True)
        return control

    def destroy(self, results: Any = None) -> None:
        if self.view is not None and self.view.poll() is None:
            self.view.terminate()
            try:
                self.view.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.view.kill()
                self.view.wait()
        if self.trace is not None:
            self.trace.close()
        super().destroy(results)
