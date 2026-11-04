"""Action-residual orthogonalization (PRD 9.2): vision's share goes, the decision signal stays, and downstream code
reads the result as ordinary shards."""
import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from discovery import probe_residual, residualize  # noqa: E402
from discovery.residualize import ActionResidual, fit, write_shard  # noqa: E402
from harness import shards  # noqa: E402
from harness.failure_time import failure_step  # noqa: E402

HIDDEN, LAYERS, LAYER, FRAMES = 12, 3, 1, 40
VISION_TO_QUERY = np.random.default_rng(0).normal(size=(HIDDEN, HIDDEN))


def write_rollout(directory, name, rng, *, success=True, decision=0.0, keep_vision=True, base="b", noise=0.01):
    visual = rng.normal(size=(FRAMES, HIDDEN))
    queries = rng.normal(scale=noise, size=(FRAMES, LAYERS, HIDDEN))
    queries[:, LAYER] += visual @ VISION_TO_QUERY.T + 3.0
    queries[:, LAYER, 0] += decision
    arrays = {"step": np.arange(FRAMES, dtype=np.int32) * 5, "driving_queries": queries.astype(np.float16),
              "driving_queries_episode_mean": queries.mean(axis=0).astype(np.float32),
              "all_tokens": queries.astype(np.float16), "all_tokens_episode_mean": queries.mean(axis=0).astype(np.float32),
              "ego_speed": rng.uniform(1, 5, FRAMES).astype(np.float32),
              "lead_distance": rng.uniform(5, 50, FRAMES).astype(np.float32)}
    if keep_vision:
        arrays["vision_bridge"] = visual.astype(np.float16)
        arrays["vision_bridge_episode_mean"] = visual.mean(axis=0).astype(np.float32)
    np.savez(directory / f"{name}.npz", **arrays)
    (directory / f"{name}.json").write_text(json.dumps({
        "route_id": name, "base_id": base, "success": success, "infractions": {}, "first_collision_step": None,
        "practice_gaps": ["G"], "role": "pilot_slice"}))


@pytest.fixture
def pool(tmp_path):
    source = tmp_path / "shards"
    source.mkdir()
    rng = np.random.default_rng(1)
    for i in range(30):
        write_rollout(source, f"ok{i}", rng)
    for i in range(6):
        write_rollout(source, f"bad{i}", rng, success=False, decision=5.0)
    write_rollout(source, "crash", rng, success=None)
    return source


def stored(directory, name):
    with np.load(directory / f"{name}.npz") as archive:
        return {key: archive[key] for key in archive.files}


def test_vision_is_removed_and_the_decision_signal_survives(pool, tmp_path):
    model = fit([pool], LAYER)
    output = tmp_path / "residual"
    output.mkdir()
    for name in ("ok0", "bad0"):
        assert write_shard(pool / f"{name}.json", model, output)
    assert model.explained_on_fit > 0.99
    ok, bad = stored(output, "ok0")["driving_queries"][:, LAYER], stored(output, "bad0")["driving_queries"][:, LAYER]
    assert np.abs(ok).mean() < 0.05
    assert bad[:, 0].mean() > 4.5 and np.abs(bad[:, 1:]).mean() < 0.05


def test_the_fit_reads_successful_frames_only(pool):
    """Failing rollouts carry a large offset, so if they reached the fit its intercept would move."""
    model = fit([pool], LAYER)
    assert model.success_frames == 30 * FRAMES
    assert abs(model.intercept[0] - 3.0) < 0.3


def test_a_saved_fit_reproduces_itself_and_reads_no_outcome(pool, tmp_path):
    model = fit([pool], LAYER)
    model.save(tmp_path / "fit.npz")
    loaded = ActionResidual.load(tmp_path / "fit.npz")
    visual = np.random.default_rng(2).normal(size=(4, HIDDEN))
    queries = visual @ VISION_TO_QUERY.T
    assert np.array_equal(model.residual(queries, visual), loaded.residual(queries, visual))
    assert (loaded.layer, loaded.alpha, loaded.success_frames) == (model.layer, model.alpha, model.success_frames)


def test_applying_a_frozen_fit_does_not_depend_on_who_succeeded(pool, tmp_path):
    model = fit([pool], LAYER)
    first, second = tmp_path / "first", tmp_path / "second"
    first.mkdir()
    second.mkdir()
    write_shard(pool / "ok0.json", model, first)
    flipped = json.loads((pool / "ok0.json").read_text())
    (pool / "ok0.json").write_text(json.dumps({**flipped, "success": False}))
    write_shard(pool / "ok0.json", model, second)
    assert np.array_equal(stored(first, "ok0")["driving_queries"], stored(second, "ok0")["driving_queries"],
                          equal_nan=True)


def test_output_conforms_to_the_shard_contract_and_loaders_read_it(pool, tmp_path):
    model = fit([pool], LAYER)
    output = tmp_path / "residual"
    output.mkdir()
    write_shard(pool / "bad0.json", model, output)
    assert shards.shard_problems(output / "bad0.json") == []
    meta = json.loads((output / "bad0.json").read_text())
    assert meta["preprocessing"] == "action_residual" and meta["success"] is False and meta["base_id"] == "b"
    rollout = probe_residual.load_shard(output / "bad0.json", "driving_queries", LAYER)
    assert rollout.failed and rollout.activations.shape == (FRAMES, HIDDEN) and not np.isnan(rollout.activations).any()
    assert set(rollout.states) == {"lead_distance"}
    with np.load(output / "bad0.npz") as archive:
        assert failure_step(meta, archive) is None and "ego_speed" in archive.files


def test_other_layers_are_nan_and_no_other_site_or_mean_travels(pool, tmp_path):
    model = fit([pool], LAYER)
    output = tmp_path / "residual"
    output.mkdir()
    write_shard(pool / "ok0.json", model, output)
    arrays = stored(output, "ok0")
    assert np.isnan(arrays["driving_queries"][:, 0]).all() and arrays["driving_queries"].shape[1] == LAYER + 1
    assert not ({"all_tokens", "vision_bridge", "vision_bridge_episode_mean"} & arrays.keys())
    assert arrays["driving_queries"].dtype == np.float32


def test_the_episode_mean_is_the_residual_of_the_means(pool, tmp_path):
    model = fit([pool], LAYER)
    output = tmp_path / "residual"
    output.mkdir()
    write_shard(pool / "ok0.json", model, output)
    source = stored(pool, "ok0")
    expected = model.residual(source["driving_queries_episode_mean"][LAYER].astype(np.float64),
                              source["vision_bridge_episode_mean"].astype(np.float64))
    assert np.allclose(stored(output, "ok0")["driving_queries_episode_mean"][LAYER], expected, atol=1e-5)


def test_a_rollout_with_no_outcome_is_not_written(pool, tmp_path):
    model = fit([pool], LAYER)
    output = tmp_path / "residual"
    output.mkdir()
    assert not write_shard(pool / "crash.json", model, output)
    assert list(output.iterdir()) == []


def test_a_shard_without_the_visual_site_stops_the_run(tmp_path):
    source = tmp_path / "shards"
    source.mkdir()
    write_rollout(source, "old", np.random.default_rng(3), keep_vision=False)
    with pytest.raises(ValueError, match="vision_bridge"):
        fit([source], LAYER)


def test_a_pool_with_no_success_cannot_fit(tmp_path):
    source = tmp_path / "shards"
    source.mkdir()
    write_rollout(source, "bad", np.random.default_rng(4), success=False)
    with pytest.raises(ValueError, match="no successful"):
        fit([source], LAYER)


def test_the_command_fits_once_then_reuses_the_saved_fit(pool, tmp_path, monkeypatch, capsys):
    model_path, first = tmp_path / "fit.npz", tmp_path / "first"
    arguments = ["residualize", str(pool), "--layer", str(LAYER), "--model", str(model_path), "--output", str(first)]
    monkeypatch.setattr(sys, "argv", arguments)
    residualize.main()
    assert json.loads(capsys.readouterr().out)["shards_written"] == 36
    monkeypatch.setattr(residualize, "fit", lambda *_: pytest.fail("refitted a frozen model"))
    monkeypatch.setattr(sys, "argv", arguments[:-1] + [str(tmp_path / "second")])
    residualize.main()
    monkeypatch.setattr(sys, "argv", ["residualize", str(pool), "--layer", "0", "--model", str(model_path), "--output", str(first)])
    with pytest.raises(SystemExit):
        residualize.main()
