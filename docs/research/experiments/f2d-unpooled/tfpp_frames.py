#!/usr/bin/env python3
"""The caption row's frames for TF++ (docs/prereg-views.md, "The caption row"): uniad_frames.py on TF++'s re-drive.

    PYTHONPATH=src python docs/research/experiments/f2d-unpooled/tfpp_frames.py SHARDS --salt-file SALT \
        --frames-out DIR --mapping MAPPING.json [--keep IDS.txt]

SHARDS is the re-drive's export (tfpp_unpooled.sbatch's OUT/shards). TF++'s re-drive saved each 10th step's forward
call to `<route run>/capture/inputs/<step>.pt`, whose `rgb` argument is the camera image the model saw (1, 3, H, W),
0..255. Each failing route takes the last capture at or before its failure step (or its last step when the failure
has no step) and every 2nd capture before it, FRAMES in all, so 1 s apart. --keep limits export to the listed route
ids (the routes of pairs whose failure reproduced, match_rate.py). Folder names, resizing and the mapping are
uniad_frames.py's.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import torch
from PIL import Image

from harness.failure_time import failure_step

FRAMES, EVERY, WIDTH = 4, 2, 640
ROOT = Path(__file__).resolve().parents[4]


def chosen(directory: Path, end: int) -> list[Path]:
    saved = [p for _, p in sorted((int(p.stem), p) for p in directory.glob("*.pt") if p.stem.isdigit()
                                  and int(p.stem) <= end)]
    return saved[::-1][::EVERY][:FRAMES][::-1]


def image_of(path: Path) -> Image.Image:
    rgb = torch.load(path, map_location="cpu", weights_only=False)["kwargs"]["rgb"]
    rgb = rgb["uint8"] if isinstance(rgb, dict) else rgb
    return Image.fromarray(rgb[0].float().clamp(0, 255).byte().permute(1, 2, 0).numpy())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("shards", type=Path)
    parser.add_argument("--salt-file", type=Path, required=True)
    parser.add_argument("--frames-out", type=Path, required=True)
    parser.add_argument("--mapping", type=Path, required=True)
    parser.add_argument("--keep", type=Path)
    args = parser.parse_args()
    if args.mapping.resolve().is_relative_to(args.frames_out.resolve()):
        parser.error("the mapping must live outside the frames tree that agents read")
    salt = args.salt_file.read_text().strip()
    keep = set(args.keep.read_text().split()) if args.keep else None
    mapping, missing = {}, []
    for sidecar in sorted(args.shards.glob("*.json")):
        meta = json.loads(sidecar.read_text())
        if meta.get("success") is not False or (keep is not None and str(meta["route_id"]) not in keep):
            continue
        with np.load(sidecar.with_suffix(".npz")) as archive:
            arrays = {k: archive[k] for k in archive.files if archive[k].ndim == 1}
        end = failure_step(meta, arrays)
        directory = ROOT / meta["source"] / "capture/inputs"
        frames = chosen(directory, end if end is not None else int(arrays["step"][-1])) if directory.is_dir() else []
        if not frames:
            missing.append(meta["route_id"])
            continue
        opaque = hashlib.sha256((salt + str(meta["route_id"])).encode()).hexdigest()[:12]
        out = args.frames_out / opaque
        out.mkdir(parents=True, exist_ok=True)
        width = None
        for index, path in enumerate(frames):
            image = image_of(path)
            width = width or image.width
            image.resize((WIDTH, round(image.height * WIDTH / image.width))).save(out / f"f{index}.png")
        mapping[opaque] = {"route": meta["route_id"], "frames": len(frames), "steps": [int(p.stem) for p in frames],
                           "native_width": width}
    args.mapping.parent.mkdir(parents=True, exist_ok=True)
    args.mapping.write_text(json.dumps({"mapping": mapping, "missing_frames": missing}, indent=1, sort_keys=True) + "\n")
    print(f"{len(mapping)} failing routes exported, {len(missing)} without frames")


if __name__ == "__main__":
    main()
