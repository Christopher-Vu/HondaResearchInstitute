#!/usr/bin/env python3
"""TransFuser++'s unpooled activations from its re-drive captures, in replay_unpooled.py's per-route npz format
(protocol.md in this folder, "Other models"). No replay: the closed-loop capture is read as it was logged.

    PYTHONPATH=src:adapters/simlingo .runtime/policy-venv/bin/python \
        docs/research/experiments/f2d-unpooled/tfpp_unpooled.py SHARDS OUT [--part I --parts N] [--limit K]

SHARDS is export_activations.py's output for the re-driven route folders (<id>.json + <id>.npz); each sidecar's
`source` is the route run whose capture/unpooled/<step>.pt and capture/inputs/<step>.pt (every 10 steps, written by
adapters/tfpp/tfpp_agent.py) are read. Routes with success None are skipped, as cache_pool.py does. A route whose
OUT/<id>.npz exists is skipped, so a rerun resumes.

Sites, per saved frame (frames are the steps that have both files):
- image: the backbone's image grid before fusion, (1512, 12, 32) -> 384 tokens of width 1512.
- join:  the last `join` call's last-layer tokens (the checkpoint query the controller acts on), 11 x 256.
- dino:  DINOv2-base patch tokens of the saved front camera (RGB, 384 x 1024, uint8), resized to 378 x 1008
         (patch 14, same aspect) and ImageNet-normalised: 27 x 72 = 1944 tokens of width 768.
Aggregations exactly as replay_unpooled.aggregate: per-frame mean, max and top-k mean (k tokens farthest from the
route's own baseline, the per-position mean of its first BASE_FRAMES frames), and every token of the last LAST frames
before the failure step projected to PROJ dims by a fixed Gaussian matrix (seed 0, drawn per site in sorted order).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

from harness.failure_time import failure_step

ROOT = Path(__file__).resolve().parents[4]
TOPK = {"image": 16, "join": 4, "dino": 16}
WIDTH = {"image": 1512, "join": 256, "dino": 768}
BASE_FRAMES, LAST, PROJ = 4, 8, 256
DINO_SIZE = (378, 1008)
IMAGENET_MEAN, IMAGENET_STD = (0.485, 0.456, 0.406), (0.229, 0.224, 0.225)


def projections(device: torch.device) -> dict[str, torch.Tensor]:
    g = torch.Generator().manual_seed(0)
    return {s: (torch.randn(WIDTH[s], PROJ, generator=g) / PROJ ** 0.5).to(device) for s in sorted(WIDTH)}


def aggregate(tokens: torch.Tensor, k: int, last: torch.Tensor, proj: torch.Tensor) -> dict[str, np.ndarray]:
    """tokens (F, P, D) float32 on the GPU -> per-frame mean, max, top-k mean; projected tokens of the `last` frames."""
    base = tokens[:BASE_FRAMES].mean(0)
    far = (tokens - base).norm(dim=2).topk(min(k, tokens.shape[1]), dim=1).indices  # (F, k)
    picked = torch.gather(tokens, 1, far[..., None].expand(-1, -1, tokens.shape[2]))
    out = {"mean": tokens.mean(1), "max": tokens.max(1).values, "topk": picked.mean(1), "codes": tokens[last] @ proj}
    return {key: value.to(torch.float16).cpu().numpy() for key, value in out.items()}


def camera(saved_input: dict) -> torch.Tensor:
    """The forward call's `rgb` kwarg, (1, 3, H, W), 0..255, stored by tfpp_agent.packed as uint8 when lossless."""
    rgb = saved_input["kwargs"]["rgb"]
    return (rgb["uint8"] if isinstance(rgb, dict) else rgb).float()


def dino_tokens(dino, rgb: torch.Tensor, device: torch.device) -> torch.Tensor:
    image = F.interpolate(rgb.to(device) / 255.0, size=DINO_SIZE, mode="bilinear", align_corners=False)
    mean = torch.tensor(IMAGENET_MEAN, device=device)[None, :, None, None]
    std = torch.tensor(IMAGENET_STD, device=device)[None, :, None, None]
    return dino(pixel_values=(image - mean) / std).last_hidden_state[0, 1:]  # drop CLS: (1944, 768)


def route_features(sidecar: Path, out: Path, dino, proj, device) -> dict:
    info = json.loads(sidecar.read_text())
    with np.load(sidecar.with_suffix(".npz")) as archive:
        arrays = {k: archive[k] for k in archive.files}
    failed = failure_step(info, arrays)
    capture = ROOT / info["source"] / "capture"
    steps = sorted(int(p.stem) for p in (capture / "unpooled").glob("*.pt") if (capture / "inputs" / p.name).is_file())
    if not steps:
        raise RuntimeError(f"{capture}: no frame has both unpooled and inputs files")
    tokens = {s: [] for s in WIDTH}
    for step in steps:
        unpooled = torch.load(capture / "unpooled" / f"{step:06d}.pt", map_location="cpu", weights_only=False)
        image = unpooled["image"][0]  # (C, H, W)
        tokens["image"].append(image.reshape(image.shape[0], -1).T.to(device))
        tokens["join"].append(unpooled["join"][-1].to(device))
        saved_input = torch.load(capture / "inputs" / f"{step:06d}.pt", map_location="cpu", weights_only=False)
        with torch.inference_mode():
            tokens["dino"].append(dino_tokens(dino, camera(saved_input), device).to(torch.float16))
    steps_np = np.array(steps)
    before = np.flatnonzero(steps_np < failed) if failed is not None else np.arange(len(steps))
    last = torch.as_tensor((before if len(before) else np.arange(1))[-LAST:], device=device)
    saved = {"step": steps_np, "code_step": steps_np[last.cpu().numpy()],
             "failure_step": np.array(-1 if failed is None else failed), "success": np.array(bool(info["success"]))}
    for site, frames in tokens.items():
        for key, value in aggregate(torch.stack(frames).float(), TOPK[site], last, proj[site]).items():
            saved[f"{site}_{key}"] = value
    np.savez(out, **saved)
    return {"route": info["route_id"], "frames": len(steps), "failure_step": None if failed is None else int(failed),
            "shapes": {k: list(v.shape) for k, v in saved.items()}}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("shards", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--part", type=int, default=0)
    parser.add_argument("--parts", type=int, default=1)
    parser.add_argument("--limit", type=int, default=0, help="at most this many routes (smoke)")
    args = parser.parse_args()
    sidecars = [p for p in sorted(args.shards.glob("*.json")) if json.loads(p.read_text()).get("success") is not None]
    mine = sidecars[args.part::args.parts][: args.limit or None]
    args.out.mkdir(parents=True, exist_ok=True)
    device = torch.device("cuda")
    from transformers import Dinov2Model
    dino = Dinov2Model.from_pretrained(ROOT / ".runtime/dinov2-base").to(device).eval()
    proj = projections(device)
    log = (args.out / f"part{args.part}.jsonl").open("a")
    for sidecar in mine:
        out = args.out / f"{sidecar.stem}.npz"
        if out.exists():
            continue
        try:
            row = route_features(sidecar, out, dino, proj, device)
        except Exception as error:  # one bad route must not stop the part; a rerun picks up missing ones
            row = {"route": sidecar.stem, "error": f"{type(error).__name__}: {error}"}
        log.write(json.dumps(row) + "\n")
        log.flush()
        print(json.dumps(row), flush=True)


if __name__ == "__main__":
    main()
