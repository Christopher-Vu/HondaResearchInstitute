"""Replay frames saved by `capture_agent.py` offline and compare them with what the closed-loop run logged.

    HF_HUB_OFFLINE=1 .runtime/policy-venv/bin/python adapters/simlingo/replay_capture.py RUN_DIR --device mps

Step 3's done-condition (PRD 13) is that a replayed frame reproduces the logged waypoints to within
1e-3 m. This also checks that the last `driving_tokens` positions of the final block, after the final
norm, are exactly the features the driving head decodes, which is what the driving-query mean assumes.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import torch
from torch import nn
from verify_checkpoint import ROOT, load_model

TOLERANCE_METRES = 1e-3


def move(value: Any, device: torch.device) -> Any:
    if isinstance(value, torch.Tensor):
        return value.detach().to(device)
    if isinstance(value, tuple) and hasattr(value, "_fields"):
        return type(value)(*(move(item, device) for item in value))
    if isinstance(value, (list, tuple)):
        return type(value)(move(item, device) for item in value)
    return value


def decoder(model: nn.Module) -> nn.Module:
    """The language model's decoder stack, whose `.layers` and final `.norm` sit under the PEFT wrapper."""
    stacks = [module for module in model.language_model.model.modules()
              if isinstance(getattr(module, "layers", None), nn.ModuleList) and hasattr(module, "norm")]
    if len(stacks) != 1:
        raise RuntimeError(f"Expected one decoder stack, found {len(stacks)}")
    return stacks[0]


def driving_query_count(model: nn.Module) -> int:
    """Driving queries are appended after the language tokens, so with batch 1 they are the last positions."""
    head = model.adaptors.driving
    return sum(int(head.queries[name].shape[1]) for name in head.order)


class Probe:
    def __init__(self, model: Any) -> None:
        self.layers: dict[int, torch.Tensor] = {}
        self.driving_features: torch.Tensor | None = None
        for index, layer in enumerate(decoder(model).layers):
            layer.register_forward_hook(self._hook(index))
        head = model.adaptors.driving
        original = head.get_predictions

        def recording(features: torch.Tensor, *args: Any, **kwargs: Any) -> Any:
            self.driving_features = features
            return original(features, *args, **kwargs)

        head.get_predictions = recording
        self.final_norm = decoder(model).norm

    def _hook(self, index: int) -> Any:
        def hook(_module: Any, _inputs: Any, output: Any) -> None:
            self.layers[index] = output[0] if isinstance(output, tuple) else output
        return hook

    def stacked(self) -> torch.Tensor:
        return torch.stack([self.layers[index][0] for index in sorted(self.layers)]).float()


def replay_frame(model: Any, probe: Probe, frame: Any, record: dict[str, Any],
                 device: torch.device) -> dict[str, Any]:
    started = time.monotonic()
    with torch.inference_mode():
        speed_wps, route, _language = model(move(frame, device))
    stacked = probe.stacked().cpu()
    n = record["driving_tokens"]
    assert probe.driving_features is not None
    normed_last = probe.final_norm(probe.layers[max(probe.layers)])[:, -n:].float()
    return {
        "step": record["step"], "forward_seconds": round(time.monotonic() - started, 3),
        "sequence_length": int(stacked.shape[1]),
        "speed_wps_max_abs_m": float((speed_wps.float().cpu() - record["speed_wps"]).abs().max()),
        "route_max_abs_m": float((route.float().cpu() - record["route"]).abs().max()),
        "layer_mean_max_abs": float((stacked.mean(dim=1) - record["layer_mean"]).abs().max()),
        "layer_driving_mean_max_abs": float((stacked[:, -n:].mean(dim=1) - record["layer_driving_mean"]).abs().max()),
        "driving_slot_matches_head": bool(torch.allclose(normed_last, probe.driving_features.float(), atol=1e-5)),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("run", type=Path)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--limit", type=int, default=0, help="replay only the first N saved frames")
    args = parser.parse_args()
    capture = args.run / "capture"
    steps = torch.load(capture / "steps.pt", weights_only=False)
    by_step = {record["step"]: record for record in steps["records"]}
    frames = sorted((capture / "inputs").glob("*.pt"))[: args.limit or None]
    sys.path.insert(0, str(ROOT / ".runtime/simlingo"))
    torch.set_num_threads(8)
    device = torch.device(args.device)
    model, _tokenizer = load_model(ROOT / ".runtime/InternVL2-1B",
                                   ROOT / "checkpoints/simlingo/checkpoints/epoch=013.ckpt/pytorch_model.pt")
    model.to(device)
    probe = Probe(model)
    rows = [replay_frame(model, probe, torch.load(path, weights_only=False), by_step[int(path.stem)], device)
            for path in frames if int(path.stem) in by_step]
    worst = max(max(row["speed_wps_max_abs_m"], row["route_max_abs_m"]) for row in rows)
    report = {
        "run": str(args.run), "logged_device": steps["device"], "logged_dtype": steps["dtype"],
        "replay_device": args.device, "frames": len(rows), "worst_waypoint_abs_m": worst,
        "within_1e-3_m": worst <= TOLERANCE_METRES,
        "worst_layer_mean_abs": max(row["layer_mean_max_abs"] for row in rows),
        "driving_slot_matches_head": all(row["driving_slot_matches_head"] for row in rows),
        "sequence_lengths": sorted({row["sequence_length"] for row in rows}), "rows": rows,
    }
    output = capture / f"replay-{args.device}.json"
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: value for key, value in report.items() if key != "rows"}, indent=2))


if __name__ == "__main__":
    main()
