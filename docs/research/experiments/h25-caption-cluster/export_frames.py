#!/usr/bin/env python3
"""H25's inputs: the last FRAMES saved camera frames up to each failing route's failure step, under opaque ids.

    PYTHONPATH=src python docs/research/experiments/h25-caption-cluster/export_frames.py SHARD_DIR [...] \
        --salt-file SALT --frames-out DIR --mapping MAPPING.json

The driver's camera was saved every 20 steps (1 s) to `<route run>/**/frames/<step>.png` since 2026-10-02. Each
failing route gets a folder named by sha256(salt + route id)[:12], holding f0.png (oldest) to f3.png (newest), resized
to WIDTH pixels wide; a route with fewer saved frames gets what exists, and the mapping records how many. The mapping
from opaque id to route id is sorted by opaque id and must be written outside the frames tree, so the agents that
caption and group never see a route id, scenario name or category. Routes with no saved frame are listed, not skipped
silently.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image

from discovery import dev_eval
from harness.failure_time import failure_step

FRAMES, WIDTH = 4, 640


def frame_dir(source: Path) -> Path | None:
    found = sorted(path for path in source.rglob("frames") if path.is_dir())
    return found[0] if found else None


def last_frames(directory: Path, end: int) -> list[Path]:
    saved = sorted((int(p.stem), p) for p in directory.glob("*.png") if p.stem.isdigit())
    return [p for step, p in saved if step <= end][-FRAMES:]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("shards", type=Path, nargs="+")
    parser.add_argument("--salt-file", type=Path, required=True)
    parser.add_argument("--frames-out", type=Path, required=True)
    parser.add_argument("--mapping", type=Path, required=True)
    args = parser.parse_args()
    if args.mapping.resolve().is_relative_to(args.frames_out.resolve()):
        parser.error("the mapping must live outside the frames tree that agents read")
    salt = args.salt_file.read_text().strip()
    mapping, missing = {}, []
    for shard in dev_eval.load_shards(args.shards):
        if shard.meta["success"]:
            continue
        with np.load(shard.sidecar.with_suffix(".npz")) as archive:
            end = failure_step(shard.meta, archive)
            last = int(archive["step"][-1])
        directory = frame_dir(Path(shard.meta["source"]))
        chosen = last_frames(directory, end if end is not None else last) if directory else []
        if not chosen:
            missing.append(shard.route_id)
            continue
        opaque = hashlib.sha256((salt + shard.route_id).encode()).hexdigest()[:12]
        out = args.frames_out / opaque
        out.mkdir(parents=True, exist_ok=True)
        for index, path in enumerate(chosen):
            image = Image.open(path).convert("RGB")
            image.resize((WIDTH, round(image.height * WIDTH / image.width))).save(out / f"f{index}.png")
        mapping[opaque] = {"route": shard.route_id, "frames": len(chosen)}
    args.mapping.write_text(json.dumps({"mapping": mapping, "missing_frames": missing}, indent=1, sort_keys=True) + "\n")
    print(f"{len(mapping)} failing routes exported, {len(missing)} without frames")


if __name__ == "__main__":
    main()
