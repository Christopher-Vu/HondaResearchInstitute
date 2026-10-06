"""Visible agent that also records Step 3 replay inputs and per-layer residual-stream means (PRD 12.1).

Every model step logs both waypoint heads plus, for each decoder layer, the block output mean-pooled
over all tokens and over the driving-query tokens. Every Nth step (SIMLINGO_CAPTURE_EVERY) also
saves the exact preprocessed model input, so `replay_capture.py` can rerun the frame offline.
"""
from __future__ import annotations

import os
from typing import Any

import torch
from replay_capture import decoder, driving_query_count, move
from torch import nn
from visible_agent import VisibleAgent

CPU = torch.device("cpu")


def get_entry_point() -> str:
    return "CaptureAgent"


class CaptureAgent(VisibleAgent):
    def setup(self, path_to_conf_file: str, route_index: Any = None) -> None:
        super().setup(path_to_conf_file, route_index)
        self.capture_every = int(os.environ.get("SIMLINGO_CAPTURE_EVERY", "10"))
        self.capture_dir = self.evidence / "capture"
        (self.capture_dir / "inputs").mkdir(parents=True, exist_ok=True)
        self.layer_outputs: dict[int, torch.Tensor] = {}
        self.driving_tokens = driving_query_count(self.model)
        self.records: list[dict[str, Any]] = []
        for index, layer in enumerate(decoder(self.model).layers):
            layer.register_forward_hook(self._layer_hook(index))
        self.model.register_forward_pre_hook(self._input_hook)
        self.model.register_forward_hook(self._output_hook)

    def _layer_hook(self, index: int) -> Any:
        def hook(_module: nn.Module, _inputs: Any, output: Any) -> None:
            self.layer_outputs[index] = output[0] if isinstance(output, tuple) else output
        return hook

    def _input_hook(self, _module: nn.Module, inputs: tuple[Any, ...]) -> None:
        self.layer_outputs.clear()
        if self.step % self.capture_every == 0:
            torch.save(move(inputs[0], CPU), self.capture_dir / "inputs" / f"{self.step:06d}.pt")

    def _output_hook(self, _module: nn.Module, _inputs: Any, output: Any) -> None:
        speed_wps, route, _language = output
        stacked = torch.stack([self.layer_outputs[index][0] for index in sorted(self.layer_outputs)])
        self.records.append({
            "step": self.step, "sequence_length": int(stacked.shape[1]), "driving_tokens": self.driving_tokens,
            "speed_wps": move(speed_wps.float(), CPU), "route": move(route.float(), CPU),
            "layer_mean": move(stacked.float().mean(dim=1), CPU),
            "layer_driving_mean": move(stacked[:, -self.driving_tokens:].float().mean(dim=1), CPU),
        })
        if len(self.records) % 200 == 0:
            self._flush()

    def _flush(self) -> None:
        torch.save({"capture_every": self.capture_every, "dtype": str(self.dtype), "device": str(self.device),
                    "records": self.records}, self.capture_dir / "steps.pt")

    def destroy(self, results: Any = None) -> None:
        if getattr(self, "records", None):
            self._flush()
        super().destroy(results)
