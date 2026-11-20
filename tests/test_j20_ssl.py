"""j20 trains a contrastive route encoder on activations alone; it is deterministic and never reads pass/fail."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import torch

SPRINT_DIR = Path(__file__).resolve().parents[1] / "docs/research/experiments/f2d-dev-simlingo"
SPEC = importlib.util.spec_from_file_location("j20_ssl", SPRINT_DIR / "j20_ssl.py")
j20 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(j20)


def _frames(n: int = 30, length: int = 12, width: int = 10) -> np.ndarray:
    rng = np.random.default_rng(0)
    frames = rng.normal(size=(n, 2, length, width)).astype(np.float16)
    frames[:3, :, :4] = np.nan
    return frames


def _write(path: Path, success: list[bool]) -> None:
    frames = _frames(len(success))
    np.savez(path, route_id=np.array([f"r{i}" for i in range(len(success))]),
             meta=np.array([json.dumps({"success": s}) for s in success]), frames=frames,
             n_frames=(~np.isnan(frames[:, 0].astype(np.float32)).any(2)).sum(1), layers=np.array([5, 8]))


def _run(tmp_path: Path, monkeypatch, success: list[bool], tag: str) -> dict:
    frames, out = tmp_path / f"frames-{tag}.npz", tmp_path / f"out-{tag}.json"
    _write(frames, success)
    monkeypatch.setattr(sys, "argv", ["j20_ssl.py", str(frames), "--dims", "4", "--hidden", "8", "--embedding", "4",
                                      "--epochs", "3", "--batch", "8", "--output", str(out)])
    j20.main()
    return json.loads(out.read_text())


def test_deterministic_and_the_encoder_never_reads_pass_fail(tmp_path, monkeypatch) -> None:
    first = _run(tmp_path, monkeypatch, [i % 3 != 0 for i in range(30)], "a")
    again = _run(tmp_path, monkeypatch, [i % 3 != 0 for i in range(30)], "b")
    flipped = _run(tmp_path, monkeypatch, [i % 2 != 0 for i in range(30)], "c")
    assert first["axes"] == again["axes"]
    assert first["settings"]["embedding_sha256"] == again["settings"]["embedding_sha256"]
    assert first["settings"]["embedding_sha256"] == flipped["settings"]["embedding_sha256"]
    assert first["settings"]["loss_last_epoch"] == flipped["settings"]["loss_last_epoch"]
    failing = {f"r{i}" for i in range(30) if i % 3 == 0}
    assert all(set(a["rollouts"]) <= failing for a in first["axes"])
    embedding = np.load(tmp_path / "out-a.embedding.npy")
    assert embedding.shape == (30, 4)
    assert np.allclose(np.linalg.norm(embedding, axis=1), 1.0, atol=1e-5)


def test_padded_frames_are_masked_and_views_stay_inside_the_route() -> None:
    z, valid = j20.frame_inputs(_frames()[:, 1], dims=4)
    assert valid[:3, :4].sum() == 0 and valid[3:].all()
    assert not np.isnan(z).any() and np.all(z[:3, :4] == 0)
    route = np.arange(20, dtype=np.float32).reshape(10, 2)
    rng = np.random.default_rng(0)
    for _ in range(50):
        window = j20.view(route, rng, noise=0.0)
        assert 5 <= len(window) <= 10
        start = int(window[0, 0]) // 2
        assert np.array_equal(window, route[start:start + len(window)])


def test_nt_xent_is_low_when_views_match_and_high_when_they_are_swapped() -> None:
    a = torch.nn.functional.normalize(torch.eye(4), dim=1)
    assert j20.nt_xent(a, a, 0.1) < 0.01
    assert j20.nt_xent(a, a.roll(1, 0), 0.1) > 5.0
