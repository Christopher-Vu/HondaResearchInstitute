"""Keep the policy camera window responsive while model inference runs."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pygame
from PIL import Image


class CameraView:
    def __init__(self, evidence: Path) -> None:
        pygame.display.init()
        self.evidence = evidence
        self.surface: Any = None
        self.paused = False
        self.last_image_time = 0

    def handle_events(self) -> bool:
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                (self.evidence / "user-stop.json").write_text(
                    json.dumps({"reason": "camera_window_closed"}) + "\n")
                print("CARLA camera: stop requested", flush=True)
                return False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                self.paused = not self.paused
                print(f"CARLA camera: {'paused' if self.paused else 'resumed'}", flush=True)
        return True

    def show(self, image_path: Path, caption: str) -> None:
        state = "View paused; Space resumes" if self.paused else "Space pauses view"
        pygame.display.set_caption(f"{caption} | {state} | Esc stops run")
        if self.paused or not image_path.is_file():
            return
        modified = image_path.stat().st_mtime_ns
        if modified == self.last_image_time:
            return
        with Image.open(image_path) as image:
            rgb = np.ascontiguousarray(image.convert("RGB"))
        if self.surface is None:
            self.surface = pygame.display.set_mode((rgb.shape[1], rgb.shape[0]))
            print("CARLA camera: window ready", flush=True)
        self.surface.blit(pygame.surfarray.make_surface(rgb.swapaxes(0, 1)), (0, 0))
        pygame.display.flip()
        self.last_image_time = modified


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path)
    parser.add_argument("device")
    args = parser.parse_args()
    view = CameraView(args.evidence)
    clock = pygame.time.Clock()
    try:
        while view.handle_events():
            view.show(args.evidence / "last-camera.png", f"CARLA 0.9.15 | SimLingo {args.device}")
            clock.tick(20)
    finally:
        pygame.display.quit()


if __name__ == "__main__":
    main()
