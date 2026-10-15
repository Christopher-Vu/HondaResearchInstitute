"""The per-token TopK SAE (PRD 12.2) on synthetic sparse data: what it must keep true while training."""
import json

import numpy as np
import pytest

torch = pytest.importorskip("torch")

from src.discovery import sae  # noqa: E402

HIDDEN = 32


def sparse_data(n=4000, atoms=32, active=3, seed=0):
    rng = np.random.default_rng(seed)
    dictionary = rng.normal(size=(atoms, HIDDEN))
    codes = np.zeros((n, atoms))
    for row in codes:
        row[rng.choice(atoms, active, replace=False)] = rng.uniform(1, 2, active)
    return sae.normalise(torch.tensor(codes @ dictionary, dtype=torch.float32))


def config(**overrides):
    return sae.SaeConfig(**{"layer": 10, "k": 4, "epochs": 30, "batch": 256, "lr": 3e-3, **overrides})


def test_training_explains_most_of_the_variance_of_sparse_signals():
    x = sparse_data()
    model, curve = sae.train(x, config(), torch.device("cpu"))
    assert sae.evaluate(model, x, 512)["explained_variance"] > 0.8
    assert curve[-1]["loss"] < curve[0]["loss"]


def test_at_most_k_latents_fire_and_decoder_columns_stay_unit_norm():
    x = sparse_data(n=1000)
    model, _ = sae.train(x, config(epochs=3), torch.device("cpu"))
    _reconstruction, latents, _pre = model(x)
    assert int((latents > 0).sum(dim=-1).max()) <= 4
    assert torch.allclose(model.decoder.norm(dim=0), torch.ones(model.decoder.shape[1]), atol=1e-5)


def test_normalise_centres_and_scales_each_token():
    x = sae.normalise(torch.randn(10, HIDDEN) * 5 + 3)
    assert torch.allclose(x.mean(dim=-1), torch.zeros(10), atol=1e-5)
    assert torch.allclose(x.norm(dim=-1), torch.ones(10), atol=1e-5)


def test_geometric_median_ignores_an_outlier_that_moves_the_mean():
    points = torch.cat([torch.zeros(99, 2), torch.tensor([[1000.0, 1000.0]])])
    assert sae.geometric_median(points).norm() < 1.0 < points.mean(dim=0).norm()


def write_shard(directory, route_id, base_id, layers=(10, 14), frames=4):
    tokens = np.zeros((frames, len(layers), 30, HIDDEN), dtype=np.float16)
    for position, layer in enumerate(layers):
        tokens[:, position] = layer
    np.savez(directory / f"{route_id}.npz", driving_query_tokens=tokens,
             driving_query_token_layers=np.asarray(layers, dtype=np.int32))
    (directory / f"{route_id}.json").write_text(json.dumps({"route_id": route_id, "base_id": base_id}))


def test_tokens_load_at_the_requested_layer_and_held_out_bases_stay_out(tmp_path):
    for index in range(20):
        write_shard(tmp_path, f"r{index}", f"b{index // 2}")
    tokens, bases = sae.load_tokens([tmp_path], 14)
    assert tokens.shape == (20 * 4 * 30, HIDDEN) and float(tokens[0, 0]) == 14.0
    held = sae.held_out_mask(bases, seed=0)
    assert set(bases[held]).isdisjoint(bases[~held]) and len(set(bases[held])) == 1
