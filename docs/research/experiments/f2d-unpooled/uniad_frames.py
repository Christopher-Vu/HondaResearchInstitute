#!/usr/bin/env python3
"""The caption row's frames for UniAD (docs/prereg-views.md, "The caption row"): h25-caption-cluster/export_frames.py
on UniAD's front JPEGs.

    PYTHONPATH=src python docs/research/experiments/f2d-unpooled/uniad_frames.py SHARDS --salt-file SALT \
        --frames-out DIR --mapping MAPPING.json

UniAD saves its front camera every 5 steps to `<route run>/capture/frames/<step>.jpg`. Each failing route takes the
last JPEG at or before its failure step (or its last step when the failure has no step) and every 4th JPEG before it,
FRAMES in all, so 1 s apart; a gap in the saved steps is not filled. They are written oldest first as f0.png..f3.png,
resized to WIDTH pixels wide (UniAD saves them 256 px wide, so this upscales), into a folder named
sha256(salt + route id)[:12]. The mapping (opaque id -> route id, frame count, steps and native width, sorted by
opaque id) must live outside the frames tree. Routes with no saved frame are listed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image

from harness.failure_time import failure_step

FRAMES, EVERY, WIDTH = 4, 4, 640
ROOT = Path(__file__).resolve().parents[4]


def chosen(directory: Path, end: int) -> list[Path]:
    saved = [p for _, p in sorted((int(p.stem), p) for p in directory.glob("*.jpg") if p.stem.isdigit()
                                  and int(p.stem) <= end)]
    return saved[::-1][::EVERY][:FRAMES][::-1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("shards", type=Path)
    parser.add_argument("--salt-file", type=Path, required=True)
    parser.add_argument("--frames-out", type=Path, required=True)
    parser.add_argument("--mapping", type=Path, required=True)
    args = parser.parse_args()
    if args.mapping.resolve().is_relative_to(args.frames_out.resolve()):
        parser.error("the mapping must live outside the frames tree that agents read")
    salt = args.salt_file.read_text().strip()
    mapping, missing = {}, []
    for sidecar in sorted(args.shards.glob("*.json")):
        meta = json.loads(sidecar.read_text())
        if meta.get("success") is not False:
            continue
        with np.load(sidecar.with_suffix(".npz")) as archive:
            arrays = {k: archive[k] for k in archive.files if archive[k].ndim == 1}
        end = failure_step(meta, arrays)
        directory = ROOT / meta["source"] / "capture/frames"
        frames = chosen(directory, end if end is not None else int(arrays["step"][-1])) if directory.is_dir() else []
        if not frames:
            missing.append(meta["route_id"])
            continue
        opaque = hashlib.sha256((salt + meta["route_id"]).encode()).hexdigest()[:12]
        out = args.frames_out / opaque
        out.mkdir(parents=True, exist_ok=True)
        for index, path in enumerate(frames):
            image = Image.open(path).convert("RGB")
            image.resize((WIDTH, round(image.height * WIDTH / image.width))).save(out / f"f{index}.png")
        mapping[opaque] = {"route": meta["route_id"], "frames": len(frames), "steps": [int(p.stem) for p in frames],
                           "native_width": Image.open(frames[0]).width}
    args.mapping.parent.mkdir(parents=True, exist_ok=True)
    args.mapping.write_text(json.dumps({"mapping": mapping, "missing_frames": missing}, indent=1, sort_keys=True) + "\n")
    print(f"{len(mapping)} failing routes exported, {len(missing)} without frames")


if __name__ == "__main__":
    main()
