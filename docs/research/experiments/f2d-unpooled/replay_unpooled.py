#!/usr/bin/env python3
"""Replay SimLingo's saved model inputs and keep patch-level activations unpooled (protocol.md in this folder).

    HF_HUB_OFFLINE=1 PYTHONPATH=src:adapters/simlingo .runtime/policy-venv/bin/python \
        docs/research/experiments/f2d-unpooled/replay_unpooled.py SHARDS OUT --part I --parts N [--limit K]

SHARDS is an export folder (<id>.json + <id>.npz per route, as f2d-test-simlingo/shards); each sidecar's `source`
is the route run whose capture/inputs/<step>.pt (every 10 steps) and capture/steps.pt are replayed. Routes with
success None are skipped, as cache_pool.py does. Every Nth route in id order from I; a route whose OUT/<id>.npz
exists is skipped, so a rerun resumes.

Sites, per saved frame:
- vit:   InternVL's vision tokens entering the projector (mlp1 input), 2 tiles x 256, width 4096.
- llm10: the same 512 image positions in the language model's decoder layer 10 output, width 896.
- dino:  DINOv2-base patch tokens of the same two 448 px tiles (2 x 1024, width 768), the image-model ceiling.
- dq:    the driving-query tokens at layer 10, read from steps.pt (logged closed loop, no replay needed).
Per site and frame: mean and max over tokens; top-k mean (the k tokens farthest from the route's own baseline, the
per-position mean of its first BASE_FRAMES frames); and for the last LAST frames before the failure step (or the
route's end) every token projected to PROJ dims by a fixed Gaussian matrix (seed 0), for the codebook rows.
Alignment: each replayed frame's per-layer means are compared with the logged `layer_mean` of the same step and of the
step CAPTURE before it. Logged on A40s and replayed elsewhere, bfloat16 drifts a little, so the check is relative:
per frame the worst absolute difference (`align_max_abs`), the relative error |replay - logged| / |logged| over all
layers (`align_rel`), and the same against the previous step (`align_rel_prev`). A route is refused when any frame's
relative error exceeds ALIGN_LIMIT. The previous-step error is kept for inspection only (a stopped car's neighbouring
frames are nearly identical, so it cannot be a rule).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import torch

from harness.failure_time import failure_step

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "adapters/simlingo"))
from replay_capture import decoder, load_in_dtype, move  # noqa: E402

TOPK = {"vit": 16, "llm10": 16, "dino": 16, "dq": 4}
WIDTH = {"vit": 4096, "llm10": 896, "dino": 768, "dq": 896}
BASE_FRAMES, LAST, PROJ, LAYER, ALIGN_LIMIT, CAPTURE = 4, 8, 256, 10, 0.05, 10


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


class Hooks:
    def __init__(self, model: torch.nn.Module) -> None:
        self.vit = self.img = self.first = None
        self.means: dict[int, torch.Tensor] = {}
        self.layer = None
        bridge = [m for n, m in model.named_modules() if n.endswith("mlp1")][0]
        bridge.register_forward_pre_hook(lambda _m, inputs: setattr(self, "vit", inputs[0]))
        bridge.register_forward_hook(lambda _m, _i, out: setattr(self, "img", out))
        layers = decoder(model).layers
        layers[0].register_forward_pre_hook(self._first, with_kwargs=True)
        for index, layer in enumerate(layers):
            layer.register_forward_hook(self._output(index))

    def _first(self, _module, args, kwargs) -> None:
        self.first = args[0] if args else kwargs["hidden_states"]

    def _output(self, index: int):
        def hook(_module, _inputs, output) -> None:
            hidden = output[0] if isinstance(output, tuple) else output
            self.means[index] = hidden[0].float().mean(0)
            if index == LAYER:
                self.layer = hidden[0]
        return hook

    def image_positions(self) -> torch.Tensor:
        """Positions of the projected image tokens in the decoder input, matched exactly (they are copied in)."""
        img = self.img.reshape(-1, self.img.shape[-1])
        seq = self.first[0]
        hit = (seq[:, None, :16] == img[None, :, :16]).all(-1)  # (L, 512)
        if not bool(hit.any(0).all()):
            raise RuntimeError("Image tokens not found in the decoder input")
        return hit.float().argmax(0)


def replay_route(sidecar: Path, out: Path, model, dino, hooks: Hooks, proj, device) -> dict:
    info = json.loads(sidecar.read_text())
    with np.load(sidecar.with_suffix(".npz")) as archive:
        arrays = {k: archive[k] for k in archive.files}
    failed = failure_step(info, arrays)
    run = ROOT / info["source"]
    logged = torch.load(run / "capture/steps.pt", map_location="cpu", weights_only=False)
    by_step = {r["step"]: r for r in logged["records"]}
    paths = [p for p in sorted((run / "capture/inputs").glob("*.pt")) if int(p.stem) in by_step]
    if not paths:
        raise RuntimeError(f"{run}: no saved inputs")
    tokens = {s: [] for s in WIDTH}
    steps, align, rel, rel_prev = [], [], [], []
    for path in paths:
        frame = torch.load(path, map_location="cpu", weights_only=False)
        frame = frame._replace(camera_images=frame.camera_images.to(torch.bfloat16))
        record = by_step[int(path.stem)]
        with torch.inference_mode():
            model(move(frame, device))
            stacked = torch.stack([hooks.means[i] for i in sorted(hooks.means)]).cpu()
            logged_mean = record["layer_mean"].float()
            align.append(float((stacked - logged_mean).abs().max()))
            rel.append(float((stacked - logged_mean).norm() / logged_mean.norm()))
            prev = by_step.get(int(path.stem) - CAPTURE)
            rel_prev.append(float((stacked - prev["layer_mean"].float()).norm() / logged_mean.norm()) if prev else np.nan)
            tokens["vit"].append(hooks.vit.reshape(-1, hooks.vit.shape[-1]).to(torch.float16))
            tokens["llm10"].append(hooks.layer[hooks.image_positions()].to(torch.float16))
            tiles = frame.camera_images.reshape(-1, 3, 448, 448).to(device, torch.float32)
            patches = dino(pixel_values=tiles).last_hidden_state[:, 1:]  # drop CLS: (2, 1024, 768)
            tokens["dino"].append(patches.reshape(-1, patches.shape[-1]).to(torch.float16))
            tokens["dq"].append(record["driving_query_tokens"][logged["token_layers"].index(LAYER)].to(device, torch.float16))
        steps.append(int(path.stem))
    steps_np = np.array(steps)
    rel_np, prev_np = np.array(rel), np.array(rel_prev)
    if rel_np.max() > ALIGN_LIMIT:
        raise RuntimeError(f"{run}: replay misaligned: relative error up to {rel_np.max():.4f}, "
                           f"previous-step error down to {np.nanmin(prev_np):.4f}")
    before = np.flatnonzero(steps_np < failed) if failed is not None else np.arange(len(steps))
    last = torch.as_tensor((before if len(before) else np.arange(1))[-LAST:], device=device)
    saved = {"step": steps_np, "align_max_abs": np.array(align, np.float32), "align_rel": rel_np.astype(np.float32),
             "align_rel_prev": prev_np.astype(np.float32), "code_step": steps_np[last.cpu().numpy()],
             "failure_step": np.array(-1 if failed is None else failed), "success": np.array(bool(info["success"]))}
    for site, frames in tokens.items():
        try:
            agg = aggregate(torch.stack(frames).float(), TOPK[site], last, proj[site])
        except torch.cuda.OutOfMemoryError:  # a long route's vit tokens; same arithmetic on the CPU
            torch.cuda.empty_cache()
            cpu = torch.device("cpu")
            agg = aggregate(torch.stack([f.cpu() for f in frames]).float(), TOPK[site], last.to(cpu), proj[site].to(cpu))
        for key, value in agg.items():
            saved[f"{site}_{key}"] = value
    np.savez(out, **saved)
    return {"route": info["route_id"], "frames": len(steps), "align_abs": round(max(align), 4),
            "align_rel": round(float(rel_np.max()), 5), "prev_rel_min": round(float(np.nanmin(prev_np)), 4)}


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
    sys.path.insert(0, str(ROOT / ".runtime/simlingo"))
    model = load_in_dtype(torch.bfloat16).to(device).eval()
    from transformers import Dinov2Model
    dino = Dinov2Model.from_pretrained(ROOT / ".runtime/dinov2-base").to(device).eval()
    hooks, proj = Hooks(model), projections(device)
    log = (args.out / f"part{args.part}.jsonl").open("a")
    for sidecar in mine:
        out = args.out / f"{sidecar.stem}.npz"
        if out.exists():
            continue
        try:
            row = replay_route(sidecar, out, model, dino, hooks, proj, device)
        except Exception as error:  # one bad route must not stop the part; the check job resubmits missing ones
            row = {"route": sidecar.stem, "error": f"{type(error).__name__}: {error}"}
        log.write(json.dumps(row) + "\n")
        log.flush()
        print(json.dumps(row), flush=True)


if __name__ == "__main__":
    main()
