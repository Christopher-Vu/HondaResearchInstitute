#!/usr/bin/env python3
"""j20: a self-supervised route encoder over the per-frame activations, then m15's clustering of the failing routes.

The encoder never sees pass/fail, route types or the manifest. Only `frames.npz` is read (route ids, the per-frame
activations, `n_frames`, and `meta.success` for the clustering step, as m03 reads it), in its salted row order.

- Input: `frames[:, layer]` (layer 8 by default), the last 50 frames, left-padded with NaN on short routes. Each
  column is standardised over every valid frame of every route, PCA --dims (fit on all valid frames, random_state 0),
  and each PCA score standardised.
- Encoder: Conv1d(dims, hidden, 5) -> GELU -> Conv1d(hidden, hidden, 5) -> GELU -> mean over the valid frames ->
  Linear(hidden, 32). The embedding is that output scaled to unit length.
- Training (SimCLR / NT-Xent): two views per route, each a random contiguous sub-window of length uniform in
  [ceil(n / 2), n] of the route's n valid frames, plus Gaussian noise of SD --noise. The other routes in the batch
  are the negatives. Temperature --temperature, Adam, all routes, fixed seed, CPU, deterministic algorithms.
- Embedding: each route's full valid window, no crop, no noise.
- Axes: Ward on the failing routes' unit-length embeddings, `cache_methods.axes_from` (cuts 2, 3, 5, largest first
  within a cut, continued under A2 to 10 distinct axes), as m15 clusters.

    PYTHONPATH=src python docs/research/experiments/f2d-dev-simlingo/j20_ssl.py FRAMES --output OUT.json
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import time
from pathlib import Path

import numpy as np
import torch
from sklearn.decomposition import PCA

SPEC = importlib.util.spec_from_file_location("cache_methods", Path(__file__).with_name("cache_methods.py"))
cache_methods = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cache_methods)

KERNEL = 5


def frame_inputs(frames: np.ndarray, dims: int) -> tuple[np.ndarray, np.ndarray]:
    """Standardised PCA scores per frame (routes, frames, dims), NaN rows zeroed, and the valid-frame mask."""
    x = frames.astype(np.float32)
    valid = ~np.isnan(x).any(axis=2)
    flat = cache_methods.standardise(x[valid])
    scores = cache_methods.standardise(PCA(n_components=dims, random_state=0).fit_transform(flat))
    out = np.zeros(x.shape[:2] + (dims,), dtype=np.float32)
    out[valid] = scores
    return out, valid


class RouteEncoder(torch.nn.Module):
    def __init__(self, dims: int, hidden: int, embedding: int) -> None:
        super().__init__()
        self.conv = torch.nn.Sequential(
            torch.nn.Conv1d(dims, hidden, KERNEL, padding=KERNEL // 2), torch.nn.GELU(),
            torch.nn.Conv1d(hidden, hidden, KERNEL, padding=KERNEL // 2), torch.nn.GELU())
        self.head = torch.nn.Linear(hidden, embedding)

    def forward(self, x: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
        h = self.conv(x.transpose(1, 2)).transpose(1, 2)
        pooled = (h * mask[..., None]).sum(1) / mask.sum(1, keepdim=True)
        return torch.nn.functional.normalize(self.head(pooled), dim=1)


def packed(z: np.ndarray, valid: np.ndarray) -> list[np.ndarray]:
    return [z[i][valid[i]] for i in range(len(z))]


def batch_of(windows: list[np.ndarray], length: int) -> tuple[torch.Tensor, torch.Tensor]:
    """Windows placed at the start of a zero tensor, with a mask over their frames."""
    x = np.zeros((len(windows), length, windows[0].shape[1]), dtype=np.float32)
    mask = np.zeros((len(windows), length), dtype=np.float32)
    for i, w in enumerate(windows):
        x[i, :len(w)] = w
        mask[i, :len(w)] = 1.0
    return torch.from_numpy(x), torch.from_numpy(mask)


def view(route: np.ndarray, rng: np.random.Generator, noise: float) -> np.ndarray:
    n = len(route)
    length = int(rng.integers(-(-n // 2), n + 1))
    start = int(rng.integers(0, n - length + 1))
    window = route[start:start + length]
    return window + rng.normal(scale=noise, size=window.shape).astype(np.float32)


def nt_xent(a: torch.Tensor, b: torch.Tensor, temperature: float) -> torch.Tensor:
    z = torch.cat([a, b])
    sim = z @ z.T / temperature
    sim.fill_diagonal_(float("-inf"))
    n = len(a)
    target = torch.cat([torch.arange(n, 2 * n), torch.arange(n)])
    return torch.nn.functional.cross_entropy(sim, target)


def train_encoder(routes: list[np.ndarray], length: int, args: argparse.Namespace) -> tuple[RouteEncoder, list[float]]:
    torch.manual_seed(args.seed)
    rng = np.random.default_rng(args.seed)
    model = RouteEncoder(routes[0].shape[1], args.hidden, args.embedding)
    optimiser = torch.optim.Adam(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    losses = []
    for _ in range(args.epochs):
        order = rng.permutation(len(routes))
        total = 0.0
        for start in range(0, len(order), args.batch):
            rows = order[start:start + args.batch]
            first = batch_of([view(routes[i], rng, args.noise) for i in rows], length)
            second = batch_of([view(routes[i], rng, args.noise) for i in rows], length)
            loss = nt_xent(model(*first), model(*second), args.temperature)
            optimiser.zero_grad()
            loss.backward()
            optimiser.step()
            total += loss.item() * len(rows)
        losses.append(total / len(routes))
    return model, losses


def embed_routes(frames: np.ndarray, args: argparse.Namespace) -> tuple[np.ndarray, list[float]]:
    """Unit-length route embeddings from the activations alone (no labels), and the per-epoch training loss."""
    torch.use_deterministic_algorithms(True)
    torch.set_num_threads(1)
    z, valid = frame_inputs(frames, args.dims)
    routes = packed(z, valid)
    model, losses = train_encoder(routes, frames.shape[1], args)
    model.eval()
    with torch.no_grad():
        embedding = model(*batch_of(routes, frames.shape[1])).numpy()
    return embedding, losses


def parse() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("frames", type=Path)
    parser.add_argument("--layer", type=int, default=8)
    parser.add_argument("--dims", type=int, default=64)
    parser.add_argument("--hidden", type=int, default=64)
    parser.add_argument("--embedding", type=int, default=32)
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--batch", type=int, default=128)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--temperature", type=float, default=0.1)
    parser.add_argument("--noise", type=float, default=0.1)
    parser.add_argument("--cuts", type=int, nargs="+", default=list(cache_methods.CUTS))
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--name", default="j20")
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse()
    began = time.time()
    with np.load(args.frames) as archive:
        ids = archive["route_id"].tolist()
        failing = np.array([not json.loads(m)["success"] for m in archive["meta"]])
        layer = archive["layers"].tolist().index(args.layer)
        frames = archive["frames"][:, layer]
    embedding, losses = embed_routes(frames, args)
    axes = cache_methods.axes_from(embedding, failing, ids, args.name, cuts=tuple(args.cuts))[:10]
    trained = {"loss_first_epoch": losses[0], "loss_last_epoch": losses[-1], "seconds": round(time.time() - began, 1),
               "embedding_sha256": hashlib.sha256(np.round(embedding, 5).tobytes()).hexdigest()}
    out = {"method": args.name, "settings": vars(args) | {"frames": str(args.frames), "output": str(args.output)} | trained,
           "axes": axes}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, indent=1) + "\n")
    np.save(args.output.with_suffix(".embedding.npy"), embedding)
    print(json.dumps({"method": args.name, **trained, "axes": [len(a["rollouts"]) for a in axes]}))


if __name__ == "__main__":
    main()
