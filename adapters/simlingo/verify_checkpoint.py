"""Verify the released SimLingo checkpoint with an offline CPU forward pass."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import hydra
import torch
import yaml
from omegaconf import OmegaConf
from transformers import AutoTokenizer

ROOT = Path(__file__).resolve().parents[2]
SPECIAL_TOKENS = [
    "<WAYPOINTS>", "<WAYPOINTS_DIFF>", "<ORG_WAYPOINTS_DIFF>",
    "<ORG_WAYPOINTS>", "<WAYPOINT_LAST>", "<ROUTE>", "<ROUTE_DIFF>",
    "<TARGET_POINT>",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_artifacts(source: Path, checkpoint: Path) -> dict[str, Any]:
    manifest = yaml.safe_load((ROOT / "configs/setup/simlingo-artifacts.yaml").read_text())
    revision = subprocess.check_output(
        ["git", "-C", str(source), "rev-parse", "HEAD"], text=True,
    ).strip()
    if revision != manifest["source"]["revision"]:
        raise ValueError("SimLingo source revision does not match the artifact manifest")
    if sha256(checkpoint) != manifest["checkpoint"]["sha256"]:
        raise ValueError("SimLingo checkpoint checksum does not match the publisher")
    subprocess.run([
        "git", "-C", str(source), "apply", "--reverse", "--check",
        str(ROOT / manifest["source"]["patch"]),
    ], check=True)
    return manifest


def load_model(base: Path, checkpoint: Path) -> tuple[Any, Any]:
    config = OmegaConf.load(checkpoint.parents[2] / ".hydra/config.yaml")
    config.model.vision_model.variant = str(base)
    config.model.language_model.variant = str(base)
    config.model.vision_model.use_global_img = config.data_module.use_global_img
    tokenizer = AutoTokenizer.from_pretrained(base, trust_remote_code=True, local_files_only=True)
    tokenizer.add_special_tokens({"additional_special_tokens": SPECIAL_TOKENS})
    tokenizer.padding_side = "left"
    model = hydra.utils.instantiate(
        config.model, cfg_data_module=config.data_module,
        processor=tokenizer, cache_dir=str(base), _recursive_=False,
    )
    state = torch.load(checkpoint, map_location="cpu", weights_only=True)
    model.load_state_dict(state, strict=True)
    model.eval()
    model.predict_language = False
    return model, tokenizer


def dummy_camera_input(tokenizer: Any) -> Any:
    from simlingo_training.utils.custom_types import DrivingInput, LanguageLabel

    prompt = "<img>" + "<IMG_CONTEXT>" * 256 + "</img>\n"
    prompt += "Current speed: 0.0 m/s. Target point: [10, 0]. Predict the waypoints."
    ids = tokenizer(prompt, return_tensors="pt", add_special_tokens=False).input_ids
    valid = torch.ones_like(ids, dtype=torch.bool)
    label = LanguageLabel(ids, valid, valid, [], [prompt], torch.zeros_like(valid))
    image = torch.linspace(-1, 1, 3 * 448 * 448).reshape(1, 1, 1, 3, 448, 448)
    return DrivingInput(
        image, torch.tensor([[[448, 448]]]), torch.eye(3).reshape(1, 1, 3, 3),
        torch.eye(4).reshape(1, 1, 4, 4), torch.zeros(1, 1),
        torch.tensor([[10., 0.]]), label, label,
    )


def verify_forward(model: Any, tokenizer: Any) -> dict[str, Any]:
    camera_input = dummy_camera_input(tokenizer)
    start = time.monotonic()
    with torch.inference_mode():
        speed, route, language = model(camera_input, return_language=False)
    if speed.shape != (1, 10, 2) or route.shape != (1, 20, 2):
        raise ValueError("Unexpected SimLingo waypoint shapes")
    if not torch.isfinite(speed).all() or not torch.isfinite(route).all():
        raise ValueError("SimLingo produced non-finite waypoints")
    if language:
        raise ValueError("Commentary-off inference produced language")
    return {
        "scope": "offline_model_dummy_input", "device": "cpu",
        "checkpoint_strict_load": True, "hidden_size": model.language_model.hidden_size,
        "decoder_layers": model.language_model.model.config.num_hidden_layers,
        "speed_waypoints_shape": list(speed.shape), "route_shape": list(route.shape),
        "finite_outputs": True, "commentary": False,
        "forward_wall_seconds": time.monotonic() - start,
        "carla_camera_verified": False, "closed_loop_route_verified": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / ".runtime/simlingo")
    parser.add_argument("--base", type=Path, default=ROOT / ".runtime/InternVL2-1B")
    parser.add_argument("--checkpoint", type=Path, default=
                        ROOT / "checkpoints/simlingo/checkpoints/epoch=013.ckpt/pytorch_model.pt")
    parser.add_argument("--output", type=Path, default=ROOT / "results/setup/model-smoke.json")
    args = parser.parse_args()
    source, base, checkpoint = args.source.resolve(), args.base.resolve(), args.checkpoint.resolve()
    manifest = verify_artifacts(source, checkpoint)
    sys.path.insert(0, str(source))
    torch.set_num_threads(8)
    model, tokenizer = load_model(base, checkpoint)
    report = verify_forward(model, tokenizer)
    report["source_revision"] = manifest["source"]["revision"]
    report["checkpoint_sha256"] = manifest["checkpoint"]["sha256"]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
