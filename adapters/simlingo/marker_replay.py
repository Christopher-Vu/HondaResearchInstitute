"""H14's offline test (docs/research/experiments/h14-route-markers/protocol.md): paint route markers out of saved frames.

    .runtime/policy-venv/bin/python adapters/simlingo/marker_replay.py sheets results/savio/40715498 --output OUT
    (view OUT/mask-check/*.png, fill in OUT/mask-check.json)
    HF_HUB_OFFLINE=1 .runtime/policy-venv/bin/python adapters/simlingo/marker_replay.py replay results/savio/40715498 --output OUT --device cuda
    .runtime/policy-venv/bin/python adapters/simlingo/marker_replay.py summary results/savio/40715498 --output OUT

`sheets` draws 50 seeded frames with the mask ringed. `replay` refuses until OUT/mask-check.json passes, then requires each
saved PNG to rebuild its saved pixel_values exactly (at bfloat16, as the model sees them), and stops if over 5% do not. Each
surviving frame with a marker is replayed intact, painted and with the same shapes painted on road in the same rows (the
placebo). Rows go to OUT/rows.jsonl and every frame's fate to OUT/census.jsonl as they finish, in a seeded order, so a job that
runs out of time leaves a random subset that `summary` can read.

torch loads only inside `replay`: `import torch` took 158 s from slow scratch (measured), and `sheets` does not need it.
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "configs/rollout/step5-background-wave3.manifest.json"
SEED = 14
ROUTES_USED = 40
MASK_CHECK_FRAMES = 50
MASK_CHECK_MIN_CAUGHT = 0.9
MAX_WRONG_WHITE_RING_SHARE = 0.1
MAX_NOT_REPRODUCED = 0.05
BOOTSTRAP_DRAWS = 2000
DECODER_LAYER = 10

# The camera has no pitch, so flat ground starts at row 256 of 512; a little margin allows for gentle rises.
HORIZON_ROW = 250
CAMERA_HEIGHT_M, CAMERA_FOV_DEGREES = 2.0, 110.0
NEAR_MARKER_M = 15.0
MAX_BLOB_PIXELS = 400
CROP_LINE_MAX_ASPECT = 6.0
SURROUND_SATURATED = 70
MAX_SURROUND_SATURATED_SHARE = 0.35
GROW_PIXELS = 2
INPAINT_RADIUS = 3

ROAD_MAX_SATURATION = 45
ROAD_VALUE_RANGE = (15, 235)
ROAD_MAX_LOCAL_VARIANCE = 40.0
ROAD_WINDOW = 9
ROAD_CLOSING = 21
PLACEBO_CLEARANCE = 15
PLACEBO_PADDING = 4
PLACEBO_ROW_BAND = 15
PLACEBO_WIDE_ROW_BAND = 40
ROW_BANDS = (("lowest marker above row 280", 0, 280), ("lowest marker in rows 280 to 319", 280, 320),
             ("lowest marker at row 320 or below", 320, 10_000))

WHITE = "white"
ChannelTest = Callable[[np.ndarray, np.ndarray, np.ndarray], np.ndarray]

# Debug points ignore scene lighting, so each colour renders almost fixed: green near (0, 245, 56), cyan (172, 241, 240),
# yellow (244, 246, 83), red (248, 59, 71) on local frames (measured). No local frame showed orange, dark cyan or blue, so
# those three tests are guesses from the drawn colour. Grey (64, 64, 64) straight points and the (128, 128, 128) route end
# should be the opaque blocks near (243, 243, 243) seen on local frames, though no frame says which draw call made which block.
MARKER_COLOURS: dict[str, ChannelTest] = {
    "green": lambda r, g, b: (g >= 190) & (g - r >= 70) & (g - b >= 70),
    "cyan": lambda r, g, b: (g >= 200) & (b >= 200) & (g - r >= 40) & (np.abs(g - b) <= 20),
    "yellow": lambda r, g, b: (r >= 200) & (g >= 200) & (np.abs(r - g) <= 14) & (r - b >= 80),
    "red": lambda r, g, b: (r >= 200) & (r - g >= 110) & (r - b >= 100) & (np.abs(g - b) <= 40),
    "orange": lambda r, g, b: (r >= 200) & (g - b >= 40) & (r - g >= 50) & (g <= 190),
    "dark cyan": lambda r, g, b: (b >= 200) & (b - r >= 90) & (g - r >= 20) & (b - g >= 50),
    "blue": lambda r, g, b: (b >= 200) & (b - r >= 110) & (b - g >= 110) & (np.abs(g - r) <= 30),
    WHITE: lambda r, g, b: (np.minimum(np.minimum(r, g), b) >= 225) & (np.maximum(np.maximum(r, g), b) - np.minimum(np.minimum(r, g), b) <= 8),
}


REPLAYED, NO_MARKER, NO_PLACEBO_SPOT = "replayed", "no marker", "no placebo spot"


@dataclass(frozen=True)
class BlobRule:
    min_pixels: int
    max_aspect: float
    min_fill: float


# Tail lights, lane paint, shirts and blue cars share the later colours, so those blobs must be larger and squarer.
BLOB_RULES = {"green": BlobRule(5, 2.5, 0.5), "cyan": BlobRule(6, 2.5, 0.5), "yellow": BlobRule(18, 1.6, 0.7),
              "red": BlobRule(30, 1.6, 0.7), "orange": BlobRule(30, 1.6, 0.7), "dark cyan": BlobRule(30, 1.6, 0.7),
              "blue": BlobRule(30, 1.6, 0.7), WHITE: BlobRule(30, 1.7, 0.8)}


@dataclass(frozen=True)
class Blob:
    colour: str
    left: int
    top: int
    shape: np.ndarray

    @property
    def bottom(self) -> int:
        return self.top + self.shape.shape[0]


@dataclass(frozen=True)
class FrameRef:
    route: str
    step: int
    png: Path
    inputs: Path


def policy_rows(height: int) -> int:
    """Rows the agent keeps: it crops the bottom before the model (team_code/agent_simlingo.py:382), so no mask goes lower."""
    return int(height - (height * 4.8) // 16)


def read_rgb(path: Path) -> np.ndarray:
    return np.asarray(Image.open(path).convert("RGB"))


def fits_rule(stats: np.ndarray, rule: BlobRule, rows: int) -> bool:
    left, top, width, height, area = stats
    if not rule.min_pixels <= area <= MAX_BLOB_PIXELS or area / (width * height) < rule.min_fill:
        return False
    # A blob cut by the crop line reads as flat, so its ceiling is looser there, though a long strip is still paint.
    ceiling = CROP_LINE_MAX_ASPECT if top + height >= rows else rule.max_aspect
    return bool(max(width, height) / min(width, height) <= ceiling)


def surround_is_plain(saturation: np.ndarray, labels: np.ndarray, label: int, stats: np.ndarray, rows: int) -> bool:
    left, top, width, height = stats[:4]
    y0, y1, x0 = max(top - 8, 0), min(top + height + 8, rows), max(left - 8, 0)
    x1 = left + width + 8
    blob = (labels[y0:y1, x0:x1] == label).astype(np.uint8)
    ring = (cv2.dilate(blob, np.ones((13, 13), np.uint8)) > 0) & (cv2.dilate(blob, np.ones((5, 5), np.uint8)) == 0)
    return bool(np.mean(saturation[y0:y1, x0:x1][ring] >= SURROUND_SATURATED) < MAX_SURROUND_SATURATED_SHARE)


def find_markers(rgb: np.ndarray) -> list[Blob]:
    """A marker colour, in the policy's crop below the horizon, as a small compact blob on plain surroundings."""
    rows = policy_rows(rgb.shape[0])
    channels = [rgb[..., index].astype(np.int16) for index in range(3)]
    saturation = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)[..., 1]
    blobs = []
    for colour, test in MARKER_COLOURS.items():
        candidates = test(*channels).astype(np.uint8)
        candidates[:HORIZON_ROW] = 0
        candidates[rows:] = 0
        count, labels, stats, _ = cv2.connectedComponentsWithStats(candidates, connectivity=8)
        for label in range(1, count):
            if fits_rule(stats[label], BLOB_RULES[colour], rows) and surround_is_plain(saturation, labels, label, stats[label], rows):
                left, top, width, height = (int(value) for value in stats[label][:4])
                blobs.append(Blob(colour, left, top, labels[top:top + height, left:left + width] == label))
    return blobs


def blob_mask(frame_shape: tuple[int, ...], blobs: list[Blob]) -> np.ndarray:
    mask = np.zeros(frame_shape[:2], dtype=np.uint8)
    for blob in blobs:
        height, width = blob.shape.shape
        mask[blob.top:blob.top + height, blob.left:blob.left + width] |= blob.shape.astype(np.uint8)
    return mask


def paint(rgb: np.ndarray, blobs: list[Blob]) -> np.ndarray:
    size = 2 * GROW_PIXELS + 1
    grown = cv2.dilate(blob_mask(rgb.shape, blobs), np.ones((size, size), np.uint8))
    return cv2.inpaint(rgb, grown, INPAINT_RADIUS, cv2.INPAINT_TELEA)


def empty_road(rgb: np.ndarray, markers: list[Blob]) -> np.ndarray:
    """Plain low-saturation ground joined to the patch just ahead of the car, then closed over gaps thinner than ROAD_CLOSING.

    Closing after the join brings back the lane paint, crosswalk stripes and small marks that markers really sit on, and leaves
    out an object larger than the kernel even when its interior is plain.
    """
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    grey = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32)
    window = (ROAD_WINDOW, ROAD_WINDOW)
    variance = cv2.blur(grey * grey, window) - cv2.blur(grey, window) ** 2
    plain = ((hsv[..., 1] <= ROAD_MAX_SATURATION) & (hsv[..., 2] >= ROAD_VALUE_RANGE[0]) & (hsv[..., 2] <= ROAD_VALUE_RANGE[1])
             & (variance <= ROAD_MAX_LOCAL_VARIANCE))
    rows = policy_rows(rgb.shape[0])
    plain[:HORIZON_ROW] = False
    plain[rows:] = False
    clearance = np.ones((2 * PLACEBO_CLEARANCE + 1, 2 * PLACEBO_CLEARANCE + 1), np.uint8)
    free = cv2.dilate(blob_mask(rgb.shape, markers), clearance) == 0
    plain &= free
    _, labels = cv2.connectedComponents(plain.astype(np.uint8), connectivity=4)
    width = rgb.shape[1]
    ahead = labels[rows - 40:rows, width // 2 - 110:width // 2 + 110]
    found = np.bincount(ahead[ahead > 0])
    if not found.size:
        return np.zeros_like(plain)
    road = (labels == int(found.argmax())).astype(np.uint8)
    closed = cv2.morphologyEx(road, cv2.MORPH_CLOSE, np.ones((ROAD_CLOSING, ROAD_CLOSING), np.uint8)) > 0
    closed[:HORIZON_ROW] = False
    closed[rows:] = False
    return closed & free


def largest_first(blobs: list[Blob]) -> list[Blob]:
    return sorted(blobs, key=lambda item: -item.shape.size)


def placebo_row_gap(markers: list[Blob], placebo: list[Blob]) -> int:
    """How many rows the worst placebo shape sits from its marker. `placebo` is in `placebo_blobs`'s order."""
    return max(abs(spot.top - blob.top) for blob, spot in zip(largest_first(markers), placebo))


def place_on_road(road: np.ndarray, blob: Blob, rng: np.random.Generator) -> Blob | None:
    """A seeded spot where the blob and its padding sit wholly on road, nearest its own rows; the spot then leaves `road`.

    It tries the blob's row band, then a wider one, then any row, so a frame is lost only when the road has no room at all.
    `placebo_row_gap` reports how far each frame had to go.
    """
    height, width = blob.shape.shape
    full_height, full_width = height + 2 * PLACEBO_PADDING, width + 2 * PLACEBO_PADDING
    fits = cv2.erode(road.astype(np.uint8), np.ones((full_height, full_width), np.uint8), anchor=(0, 0))
    fits[road.shape[0] - full_height + 1:] = 0
    fits[:, road.shape[1] - full_width + 1:] = 0
    tops, lefts = np.nonzero(fits)
    if tops.size == 0:
        return None
    row_gaps = np.abs(tops + PLACEBO_PADDING - blob.top)
    band = next(limit for limit in (PLACEBO_ROW_BAND, PLACEBO_WIDE_ROW_BAND, road.shape[0]) if np.any(row_gaps <= limit))
    tops, lefts = tops[row_gaps <= band], lefts[row_gaps <= band]
    pick = int(rng.integers(tops.size))
    top, left = int(tops[pick]), int(lefts[pick])
    road[top:top + full_height, left:left + full_width] = False
    return Blob(blob.colour, left + PLACEBO_PADDING, top + PLACEBO_PADDING, blob.shape)


def placebo_blobs(rgb: np.ndarray, markers: list[Blob], route: str, step: int) -> list[Blob] | None:
    """The same shapes at seeded spots on road in their own rows, or None when the road has no room for all of them."""
    road = empty_road(rgb, markers)
    rng = np.random.default_rng([SEED, zlib.crc32(route.encode()), step])
    placed = []
    for blob in largest_first(markers):
        spot = place_on_road(road, blob, rng)
        if spot is None:
            return None
        placed.append(spot)
    return placed


def nearest_marker_m(blobs: list[Blob], frame_height: int, frame_width: int) -> float:
    """Flat-ground estimate from the lowest blob's image row, so a rough band and not a measured distance."""
    focal_pixels = frame_width / 2 / math.tan(math.radians(CAMERA_FOV_DEGREES / 2))
    rows_below_horizon = max(blob.bottom for blob in blobs) - frame_height / 2
    return focal_pixels * CAMERA_HEIGHT_M / rows_below_horizon if rows_below_horizon > 0 else math.inf


def drawn_routes(manifest: Path = MANIFEST) -> list[str]:
    """Every route id in the seeded order. No outcome enters the draw."""
    route_ids = sorted((entry["id"] for entry in json.loads(manifest.read_text())), key=int)
    random.Random(SEED).shuffle(route_ids)
    return route_ids


def route_frames(route_dir: Path) -> list[FrameRef]:
    """Steps with both a saved PNG (every 20th) and saved model inputs (every 10th). Step 0 has no model call, so no inputs."""
    route = route_dir.name.removeprefix("route-")
    inputs = {path.stem: path for path in (route_dir / "capture/inputs").glob("*.pt")}
    return [FrameRef(route, int(png.stem), png, inputs[png.stem])
            for png in sorted((route_dir / "frames").glob("*.png")) if png.stem in inputs]


def usable_frames(run: Path, draw: list[str], routes_used: int = ROUTES_USED) -> tuple[list[FrameRef], list[str], list[str]]:
    """The first drawn routes that have frames and inputs. A route without either gives way to the next id."""
    frames: list[FrameRef] = []
    used: list[str] = []
    passed_over: list[str] = []
    for route in draw:
        if len(used) == routes_used:
            break
        found = route_frames(run / f"route-{route}")
        if found:
            frames += found
            used.append(route)
        else:
            passed_over.append(route)
    return frames, used, passed_over


def white_rule_holds(report: dict[str, Any]) -> bool:
    """White rings sit on real blocks at least 90% of the time and catch 90% of them. Otherwise white blocks stay unpainted."""
    rings, wrong = report.get("white_rings_drawn"), report.get("white_rings_not_on_a_block")
    visible, caught = report.get("white_blocks_visible"), report.get("white_blocks_caught")
    if None in (rings, wrong, visible, caught):
        return False
    return wrong <= MAX_WRONG_WHITE_RING_SHARE * rings and caught >= MASK_CHECK_MIN_CAUGHT * visible


def mask_check_passes(report: dict[str, Any] | None) -> bool:
    """50 frames viewed by eye, 90% of visible dots caught (white blocks too if their rule holds), no traffic light or vehicle touched."""
    if not report:
        return False
    viewed, visible = report.get("frames_viewed"), report.get("coloured_dots_visible")
    caught, touched = report.get("coloured_dots_caught"), report.get("frames_touching_traffic_light_or_vehicle")
    if None in (viewed, visible, caught, touched) or not visible:
        return False
    if white_rule_holds(report):
        visible, caught = visible + report["white_blocks_visible"], caught + report["white_blocks_caught"]
    return viewed >= MASK_CHECK_FRAMES and caught / visible >= MASK_CHECK_MIN_CAUGHT and touched == 0


def reproduction_passes(dropped: int, total: int) -> bool:
    return total > 0 and dropped / total <= MAX_NOT_REPRODUCED


def excess_reading(excess_m: float) -> str:
    """The protocol's reading, fixed before any data, against Step 4's measured scale."""
    if excess_m < 0.02:
        return "Under 2 cm: no sign per frame. This clears nothing."
    if excess_m <= 0.07:
        return "2 to 7 cm: the size of removing one middle layer."
    return "Over 7 cm: larger than any middle layer. Run Stage 1 first."


def mask_panel(rgb: np.ndarray, blobs: list[Blob]) -> np.ndarray:
    """The policy's crop as it is, above the same crop with each coloured blob ringed in magenta and each white one in orange."""
    crop = rgb[:policy_rows(rgb.shape[0])]
    ringed = crop.copy()
    for blob in blobs:
        height, width = blob.shape.shape
        centre = (blob.left + width // 2, blob.top + height // 2)
        ring = (255, 140, 0) if blob.colour == WHITE else (255, 0, 255)
        cv2.circle(ringed, centre, max(height, width) // 2 + 6, ring, 1, cv2.LINE_AA)
    return np.vstack([crop, ringed])


def write_sheets(frames: list[FrameRef], output: Path) -> None:
    folder = output / "mask-check"
    folder.mkdir(parents=True, exist_ok=True)
    chosen = random.Random(SEED).sample(frames, min(MASK_CHECK_FRAMES, len(frames)))
    listed = []
    for index, frame in enumerate(chosen):
        rgb = read_rgb(frame.png)
        blobs = find_markers(rgb)
        name = f"{index:02d}-route-{frame.route}-{frame.step:06d}.png"
        Image.fromarray(mask_panel(rgb, blobs)).save(folder / name)
        listed.append({"panel": name, "blobs": [{"colour": blob.colour, "area": int(blob.shape.sum()), "top": blob.top,
                                                 "left": blob.left} for blob in blobs]})
    white_rings = sum(blob["colour"] == WHITE for entry in listed for blob in entry["blobs"])
    template = {"frames_viewed": None, "coloured_dots_visible": None, "coloured_dots_caught": None,
                "frames_touching_traffic_light_or_vehicle": None, "white_rings_drawn": white_rings,
                "white_rings_not_on_a_block": None, "white_blocks_visible": None, "white_blocks_caught": None}
    (output / "mask-check-frames.json").write_text(json.dumps(listed, indent=1) + "\n")
    if not (output / "mask-check.json").exists():
        (output / "mask-check.json").write_text(json.dumps(template, indent=2) + "\n")


def load_mask_check(output: Path) -> dict[str, Any] | None:
    path = output / "mask-check.json"
    return json.loads(path.read_text()) if path.is_file() else None


def by_route(rows: list[dict[str, Any]]) -> list[np.ndarray]:
    groups: dict[str, list[int]] = {}
    for index, row in enumerate(rows):
        groups.setdefault(row["route"], []).append(index)
    return [np.array(indices) for indices in groups.values()]


def route_bootstrap(rows: list[dict[str, Any]], statistic: Callable[[np.ndarray], float]) -> list[float]:
    """90% percentile interval of a statistic over row indices, resampling whole routes."""
    routes = by_route(rows)
    rng = np.random.default_rng(SEED)
    draws = [statistic(np.concatenate([routes[pick] for pick in rng.integers(len(routes), size=len(routes))]))
             for _ in range(BOOTSTRAP_DRAWS)]
    return [float(value) for value in np.percentile(draws, [5, 95])]


def shift_summary(rows: list[dict[str, Any]], field: str) -> dict[str, Any]:
    painted = np.array([row["painted"][field] for row in rows])
    placebo = np.array([row["placebo"][field] for row in rows])
    report: dict[str, Any] = {}
    for name, values in (("painted", painted), ("placebo", placebo)):
        report[name] = {"median": float(np.median(values)), "p90": float(np.percentile(values, 90)),
                        "median_interval_90": route_bootstrap(rows, lambda picks, v=values: float(np.median(v[picks]))),
                        "p90_interval_90": route_bootstrap(rows, lambda picks, v=values: float(np.percentile(v[picks], 90)))}
    report["excess_median"] = report["painted"]["median"] - report["placebo"]["median"]
    report["excess_median_interval_90"] = route_bootstrap(
        rows, lambda picks: float(np.median(painted[picks]) - np.median(placebo[picks])))
    return report


def frame_groups(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    groups = {"all": rows}
    for colour in MARKER_COLOURS:
        groups[f"colour: {colour}"] = [row for row in rows if colour in row["colours"]]
    groups[f"nearest under {NEAR_MARKER_M:.0f} m"] = [row for row in rows if row["nearest_marker_m"] < NEAR_MARKER_M]
    groups[f"nearest {NEAR_MARKER_M:.0f} m or more"] = [row for row in rows if row["nearest_marker_m"] >= NEAR_MARKER_M]
    for name, first, past_last in ROW_BANDS:
        groups[name] = [row for row in rows if first <= row["lowest_marker_row"] < past_last]
    groups[f"placebo within {PLACEBO_ROW_BAND} rows of its marker"] = [row for row in rows if row["placebo_row_gap"] <= PLACEBO_ROW_BAND]
    return {name: members for name, members in groups.items() if members}


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    fields = ("route_m", "speed_m", "layer_driving_mean")
    groups = {name: {"frames": len(members), "routes": len({row["route"] for row in members}),
                     **{field: shift_summary(members, field) for field in fields}}
              for name, members in frame_groups(rows).items()}
    excess = groups["all"]["route_m"]["excess_median"]
    return {"excess_route_m": excess, "reading": excess_reading(excess), "groups": groups}


def read_rows(output: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in (output / "rows.jsonl").read_text().splitlines() if line.strip()]


def spread(values: list[float]) -> dict[str, float] | None:
    return dict(zip(("p10", "median", "p90"), (float(v) for v in np.percentile(values, [10, 50, 90])))) if values else None


def census_summary(census: list[dict[str, Any]]) -> dict[str, Any]:
    """What became of every frame read, and whether the frames with no room for a placebo differ from those replayed."""
    counts = {fate: sum(entry["fate"] == fate for entry in census) for fate in (REPLAYED, NO_MARKER, NO_PLACEBO_SPOT)}
    by_fate = {fate: {field: spread([entry[field] for entry in census if entry["fate"] == fate])
                      for field in ("marker_pixels", "lowest_marker_row")} for fate in (REPLAYED, NO_PLACEBO_SPOT)}
    return {"frames_read": len(census), "frames_by_fate": counts, "replayed_against_no_room": by_fate,
            "frames_with_white_block": sum(entry["white_blocks"] > 0 for entry in census)}


def read_census(output: Path) -> list[dict[str, Any]]:
    path = output / "census.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()] if path.is_file() else []


def write_summary(output: Path, header: dict[str, Any]) -> dict[str, Any]:
    rows = read_rows(output)
    report = {**header, **census_summary(read_census(output)), "frames_replayed": len(rows), **(summarize(rows) if rows else {})}
    (output / "summary.json").write_text(json.dumps(report, indent=1) + "\n")
    return report


class Replayer:
    """The model and the agent's own preprocessing, loaded only here. Everything else in this file runs without torch."""

    def __init__(self, device_name: str) -> None:
        import torch

        sys.path.insert(0, str(ROOT / ".runtime/simlingo"))
        from ablate_replay import load_frame, plan
        from replay_capture import Probe, driving_query_count, load_in_dtype
        from simlingo_training.utils.internvl2_utils import build_transform, dynamic_preprocess

        self.torch, self.load_frame, self.plan = torch, load_frame, plan
        self.dynamic_preprocess, self.transform = dynamic_preprocess, build_transform(input_size=448)
        self.device, self.dtype = torch.device(device_name), torch.bfloat16
        self.make_model = lambda: load_in_dtype(self.dtype).to(self.device).eval()
        self.make_probe, self.query_count = Probe, driving_query_count
        self.model: Any = None
        self.probe: Any = None
        self.queries = 0

    def load_model(self) -> None:
        self.model = self.make_model()
        self.probe = self.make_probe(self.model)
        self.queries = self.query_count(self.model)

    def pixel_values(self, rgb: np.ndarray) -> Any:
        """The agent's tick() from the camera image on (team_code/agent_simlingo.py:372-416), which needs CARLA to import."""
        _, encoded = cv2.imencode(".jpg", np.ascontiguousarray(rgb[:, :, ::-1]))
        camera = cv2.cvtColor(cv2.imdecode(encoded, cv2.IMREAD_UNCHANGED), cv2.COLOR_BGR2RGB)
        tiles = self.dynamic_preprocess(Image.fromarray(camera[:policy_rows(camera.shape[0])]), image_size=448,
                                        use_thumbnail=False, max_num=2)
        stacked = self.torch.stack([self.transform(tile) for tile in tiles])
        return stacked.view(1, 1, *stacked.shape).to(device=self.device, dtype=self.dtype)

    def reproduces(self, frame: FrameRef) -> bool:
        saved = self.load_frame(frame.inputs, self.dtype, self.device).camera_images
        return bool(self.torch.equal(self.pixel_values(read_rgb(frame.png)), saved))

    def plan_with(self, frame: Any, rgb: np.ndarray) -> tuple[Any, Any, Any]:
        speed, route = self.plan(self.model, frame._replace(camera_images=self.pixel_values(rgb)))
        driving_mean = self.probe.layers[DECODER_LAYER][0, -self.queries:].float().mean(dim=0)
        return route, speed, driving_mean

    def shifts(self, intact: tuple[Any, Any, Any], changed: tuple[Any, Any, Any]) -> dict[str, float]:
        """Mean waypoint distance in metres, as Step 4 Part B, and the distance between the two layer means."""
        return {"route_m": (changed[0] - intact[0]).norm(dim=1).mean().item(),
                "speed_m": (changed[1] - intact[1]).norm(dim=1).mean().item(),
                "layer_driving_mean": (changed[2] - intact[2]).norm().item()}

    def replay(self, ref: FrameRef, rgb: np.ndarray, markers: list[Blob], placebo: list[Blob]) -> dict[str, Any]:
        frame = self.load_frame(ref.inputs, self.dtype, self.device)
        intact = self.plan_with(frame, rgb)
        return {"route": ref.route, "step": ref.step, "colours": sorted({blob.colour for blob in markers}),
                **marker_facts(rgb, markers), "placebo_row_gap": placebo_row_gap(markers, placebo),
                "nearest_marker_m": nearest_marker_m(markers, *rgb.shape[:2]),
                "layer_driving_mean_norm": intact[2].norm().item(),
                "painted": self.shifts(intact, self.plan_with(frame, paint(rgb, markers))),
                "placebo": self.shifts(intact, self.plan_with(frame, paint(rgb, placebo)))}


def marker_facts(rgb: np.ndarray, markers: list[Blob]) -> dict[str, int]:
    return {"marker_pixels": int(blob_mask(rgb.shape, markers).sum()), "lowest_marker_row": max(blob.bottom for blob in markers)}


def reproduction_gate(replayer: Replayer, frames: list[FrameRef], output: Path) -> list[FrameRef]:
    kept = [frame for frame in frames if replayer.reproduces(frame)]
    dropped = len(frames) - len(kept)
    report = {"frames": len(frames), "dropped": dropped, "passed": reproduction_passes(dropped, len(frames))}
    (output / "reproduction.json").write_text(json.dumps(report, indent=2) + "\n")
    if not report["passed"]:
        raise SystemExit(f"{dropped} of {len(frames)} frames did not rebuild their saved pixel_values: the offline work stops")
    return kept


def replay_frames(replayer: Replayer, frames: list[FrameRef], output: Path, paint_white: bool = True) -> None:
    with (output / "rows.jsonl").open("w") as rows, (output / "census.jsonl").open("w") as census:
        for frame in random.Random(SEED).sample(frames, len(frames)):
            rgb = read_rgb(frame.png)
            found = find_markers(rgb)
            markers = [blob for blob in found if paint_white or blob.colour != WHITE]
            placebo = placebo_blobs(rgb, markers, frame.route, frame.step) if markers else None
            fate = NO_MARKER if not markers else NO_PLACEBO_SPOT if placebo is None else REPLAYED
            if fate == REPLAYED:
                rows.write(json.dumps(replayer.replay(frame, rgb, markers, placebo)) + "\n")
                rows.flush()
            facts = marker_facts(rgb, markers) if markers else {"marker_pixels": 0, "lowest_marker_row": 0}
            census.write(json.dumps({"route": frame.route, "step": frame.step, "fate": fate, **facts,
                                     "white_blocks": sum(blob.colour == WHITE for blob in found)}) + "\n")
            census.flush()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", choices=["sheets", "replay", "summary"])
    parser.add_argument("run", type=Path, help="the array's results folder, holding route-<id> folders")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--limit", type=int, default=0, help="use only the first N frames (smoke test)")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    frames, used, passed_over = usable_frames(args.run, drawn_routes(args.manifest))
    frames = frames[: args.limit or None]
    header = {"run": str(args.run), "routes_used": used, "routes_passed_over": passed_over, "frames_usable": len(frames)}
    if args.mode == "sheets":
        write_sheets(frames, args.output)
        print(json.dumps(header, indent=1))
    elif args.mode == "summary":
        print(json.dumps(write_summary(args.output, header), indent=1))
    else:
        run_replay(args, frames, header)


def run_replay(args: argparse.Namespace, frames: list[FrameRef], header: dict[str, Any]) -> None:
    mask_check = load_mask_check(args.output)
    if not mask_check_passes(mask_check):
        raise SystemExit(f"{args.output / 'mask-check.json'} does not pass: view the sheets first, or the offline work stops")
    paint_white = white_rule_holds(mask_check)
    replayer = Replayer(args.device)
    kept = reproduction_gate(replayer, frames, args.output)
    replayer.load_model()
    replay_frames(replayer, kept, args.output, paint_white)
    print(json.dumps(write_summary(args.output, {**header, "frames_reproduced": len(kept), "white_blocks_painted": paint_white}), indent=1))


if __name__ == "__main__":
    main()
