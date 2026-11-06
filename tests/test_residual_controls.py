"""H18's controls: the shuffle removes almost nothing vision predicts, and the variance match removes as much variance
as the real fit without using vision."""
import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tests")]

from discovery.residual_controls import shuffled_fit, top_variance_fit, write_control_shards  # noqa: E402
from discovery.residualize import fit  # noqa: E402
from harness.schema import ACTION_RESIDUAL  # noqa: E402
from test_residualize import LAYER, stored, write_rollout  # noqa: E402


@pytest.fixture
def pool(tmp_path):
    source = tmp_path / "shards"
    source.mkdir()
    rng = np.random.default_rng(2)
    for i in range(30):
        write_rollout(source, f"ok{i}", rng)
    write_rollout(source, "bad0", rng, success=False, decision=5.0)
    write_rollout(source, "crash", rng, success=None)
    return source


def query_layer(directory, name):
    return stored(directory, name)["driving_queries"][:, LAYER].astype(np.float64)


def test_the_shuffle_keeps_what_vision_predicts(pool, tmp_path):
    real, control = fit([pool], LAYER), shuffled_fit([pool], LAYER, seed=18)
    assert real.explained_on_fit > 0.99 and control.explained_on_fit < 0.1
    written = write_control_shards([pool], control, "shuffle", tmp_path / "shuffle")
    assert written == 31
    raw, kept = query_layer(pool, "ok0"), query_layer(tmp_path / "shuffle", "ok0")
    assert np.var(kept, axis=0).sum() > 0.8 * np.var(raw, axis=0).sum()


def test_the_variance_match_reaches_the_real_share_with_the_fewest_components(pool):
    target = fit([pool], LAYER).explained_on_fit
    model = top_variance_fit([pool], LAYER, target)
    assert model.explained_on_fit >= target
    assert np.allclose(model.components @ model.components.T, np.eye(len(model.components)), atol=1e-8)
    centred = query_layer(pool, "ok0") - model.mean
    one_fewer = model.components[:-1]
    if len(one_fewer):
        all_success = np.concatenate([query_layer(pool, f"ok{i}") for i in range(30)]) - model.mean
        share = np.sum((all_success @ one_fewer.T) ** 2) / np.sum(all_success ** 2)
        assert share < target
    assert len(top_variance_fit([pool], LAYER, 0.0).components) == 1
    assert centred.shape[1] == model.mean.size


def test_the_variance_match_removes_the_mean_and_its_span_only(pool, tmp_path):
    model = top_variance_fit([pool], LAYER, 0.5)
    write_control_shards([pool], model, "top-variance", tmp_path / "top")
    residual = query_layer(tmp_path / "top", "ok0")
    assert np.abs(residual @ model.components.T).max() < 1e-3
    queries = np.random.default_rng(3).normal(size=(4, model.mean.size))
    assert np.allclose(model.residual(queries, None), model.residual(queries, np.zeros((4, 99))))


def test_control_shards_say_which_control_made_them(pool, tmp_path):
    write_control_shards([pool], shuffled_fit([pool], LAYER, seed=18), "shuffle", tmp_path / "shuffle")
    meta = json.loads((tmp_path / "shuffle" / "ok0.json").read_text())
    assert meta["preprocessing"] == ACTION_RESIDUAL and meta["residual_control"] == "shuffle"
    assert not (tmp_path / "shuffle" / "crash.json").exists()


def test_the_match_uses_the_variance_weighted_share_the_real_fit_removes(tmp_path):
    """Loud units that vision misses and quiet units it predicts: the per-unit average R squared is high, the share
    of variance removed is low, and the control must match the second."""
    from discovery.residual_controls import removed_share
    source = tmp_path / "shards"
    source.mkdir()
    rng = np.random.default_rng(4)
    for i in range(30):
        write_rollout(source, f"ok{i}", rng)
    for path in source.glob("*.npz"):
        arrays = dict(np.load(path))
        arrays["driving_queries"] = arrays["driving_queries"].astype(np.float32)
        arrays["driving_queries"][:, LAYER, :2] = rng.normal(scale=50.0, size=(len(arrays["step"]), 2))
        np.savez(path, **arrays)
    real = fit([source], LAYER)
    from discovery.residual_controls import success_sites
    share = removed_share(real, *success_sites([source], LAYER))
    assert real.explained_on_fit > 0.5 and share < 0.2
    model = top_variance_fit([source], LAYER, share)
    assert share <= model.explained_on_fit < real.explained_on_fit


def test_centre_removes_the_success_mean_and_nothing_else(pool, tmp_path):
    from discovery.residual_controls import centre_fit
    model = centre_fit([pool], LAYER)
    queries = np.random.default_rng(5).normal(size=(6, model.mean.size))
    assert np.allclose(model.residual(queries, None), queries - model.mean)
    write_control_shards([pool], model, "centre", tmp_path / "centre")
    assert json.loads((tmp_path / "centre" / "ok1.json").read_text())["residual_control"] == "centre"
