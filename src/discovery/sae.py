"""TopK sparse autoencoder on per-token driving-query activations (PRD 12.2).

    python -m src.discovery.sae SHARD_DIR [SHARD_DIR ...] --layer 10 --k 64 --seed 0 --output OUT_DIR

Inputs are the `driving_query_tokens` arrays that export_activations.py writes, (T, token layers, 30, hidden), at the
decoder layer named by `--layer`. Every token is one sample, mean-subtracted and L2-normalised on its own. A tenth of
the base routes, chosen by the seed, is held out for evaluation.

The recipe is PRD 12.2's: TopK with an AuxK loss (k_aux 512, coefficient 1/32), expansion ratio 1, no encoder or
decoder bias, a pre-bias initialised to the geometric median of 10,000 samples, unit-norm decoder columns with
tangent-projected gradients, Adam (0.9, 0.999) at lr 1e-4, batch 4096, gradient clipping at 1.0. A latent is dead when
it has not fired in the last 500 steps. Not done here: waypoint error with reconstructions spliced back into the policy.

OUT_DIR receives `sae.pt` (weights and config) and `metrics.json` (explained variance, normalised MSE and dead fraction
on held-out tokens, and the training curve).
"""
from __future__ import annotations

import argparse
import json
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch import nn

K_AUX = 512
AUX_COEFFICIENT = 1 / 32
DEAD_AFTER_STEPS = 500
MEDIAN_SAMPLES = 10_000
HELD_OUT_FRACTION = 0.1


@dataclass
class SaeConfig:
    layer: int
    k: int = 64
    expansion: float = 1.0
    seed: int = 0
    epochs: int = 100
    batch: int = 4096
    lr: float = 1e-4
    grad_clip: float = 1.0


def normalise(tokens: torch.Tensor) -> torch.Tensor:
    centred = tokens - tokens.mean(dim=-1, keepdim=True)
    return centred / centred.norm(dim=-1, keepdim=True).clamp_min(1e-8)


def geometric_median(points: torch.Tensor, iterations: int = 100) -> torch.Tensor:
    """Weiszfeld's algorithm."""
    median = points.mean(dim=0)
    for _ in range(iterations):
        weights = 1 / (points - median).norm(dim=1).clamp_min(1e-8)
        updated = (weights[:, None] * points).sum(dim=0) / weights.sum()
        if (updated - median).norm() < 1e-6:
            return updated
        median = updated
    return median


class TopKSae(nn.Module):
    def __init__(self, hidden: int, latents: int, k: int, pre_bias: torch.Tensor) -> None:
        super().__init__()
        self.k = k
        self.pre_bias = nn.Parameter(pre_bias.clone())
        self.encoder = nn.Parameter(torch.randn(latents, hidden) / hidden ** 0.5)
        self.decoder = nn.Parameter(self.encoder.data.T.clone())
        self.normalise_decoder()

    @torch.no_grad()
    def normalise_decoder(self) -> None:
        self.decoder.data /= self.decoder.data.norm(dim=0, keepdim=True).clamp_min(1e-8)

    @torch.no_grad()
    def project_decoder_gradient(self) -> None:
        """Remove each column's gradient component along the column, so the step keeps it on the unit sphere."""
        if self.decoder.grad is not None:
            columns = self.decoder.data
            self.decoder.grad -= columns * (self.decoder.grad * columns).sum(dim=0, keepdim=True)

    def pre_activations(self, x: torch.Tensor) -> torch.Tensor:
        return (x - self.pre_bias) @ self.encoder.T

    def top_k(self, pre: torch.Tensor, k: int, mask: torch.Tensor | None = None) -> torch.Tensor:
        masked = pre if mask is None else pre.masked_fill(~mask, float("-inf"))
        values, indices = masked.topk(min(k, pre.shape[-1]), dim=-1)
        return torch.zeros_like(pre).scatter(-1, indices, values.clamp_min(0).nan_to_num(0.0, 0.0, 0.0))

    def decode(self, latents: torch.Tensor) -> torch.Tensor:
        return latents @ self.decoder.T + self.pre_bias

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        pre = self.pre_activations(x)
        latents = self.top_k(pre, self.k)
        return self.decode(latents), latents, pre


def aux_loss(model: TopKSae, x: torch.Tensor, reconstruction: torch.Tensor, pre: torch.Tensor,
             dead: torch.Tensor) -> torch.Tensor:
    """AuxK: the dead latents' top k_aux pre-activations reconstruct the main reconstruction's error."""
    if not dead.any():
        return x.new_zeros(())
    error = (x - reconstruction).detach()
    auxiliary = model.top_k(pre, K_AUX, dead.expand_as(pre)) @ model.decoder.T
    return ((auxiliary - error) ** 2).sum(dim=-1).mean() / (error ** 2).sum(dim=-1).mean().clamp_min(1e-8)


def load_tokens(shard_dirs: list[Path], layer: int) -> tuple[torch.Tensor, np.ndarray]:
    """Every driving-query token at `layer`, float16, with the base route of its rollout."""
    tokens, bases = [], []
    for sidecar in sorted(path for directory in shard_dirs for path in directory.glob("*.json")):
        with np.load(sidecar.with_suffix(".npz")) as archive:
            if "driving_query_tokens" not in archive.files:
                continue
            position = list(archive["driving_query_token_layers"]).index(layer)
            array = archive["driving_query_tokens"][:, position]
        array = array.reshape(-1, array.shape[-1])
        tokens.append(torch.from_numpy(array))
        bases += [json.loads(sidecar.read_text())["base_id"]] * len(array)
    if not tokens:
        raise ValueError(f"no shard in {shard_dirs} has driving-query tokens")
    return torch.cat(tokens), np.asarray(bases)


def held_out_mask(bases: np.ndarray, seed: int) -> np.ndarray:
    unique = sorted(set(bases.tolist()))
    if len(unique) < 2:
        raise ValueError("holding out base routes for evaluation needs at least two of them")
    count = min(len(unique) - 1, max(1, round(HELD_OUT_FRACTION * len(unique))))
    held = set(random.Random(seed).sample(unique, count))
    return np.array([base in held for base in bases.tolist()])


@torch.no_grad()
def evaluate(model: TopKSae, x: torch.Tensor, batch: int) -> dict[str, float]:
    squared_error = total = 0.0
    fired = torch.zeros(model.encoder.shape[0], dtype=torch.bool, device=x.device)
    mean = x.mean(dim=0)
    for start in range(0, len(x), batch):
        chunk = x[start:start + batch]
        reconstruction, latents, _pre = model(chunk)
        squared_error += float(((chunk - reconstruction) ** 2).sum())
        total += float(((chunk - mean) ** 2).sum())
        fired |= (latents > 0).any(dim=0)
    return {"explained_variance": 1 - squared_error / total, "normalised_mse": squared_error / total,
            "never_fired_fraction": float((~fired).float().mean())}


def train(x: torch.Tensor, config: SaeConfig, device: torch.device) -> tuple[TopKSae, list[dict[str, float]]]:
    torch.manual_seed(config.seed)
    generator = torch.Generator().manual_seed(config.seed)
    sample = x[torch.randperm(len(x), generator=generator)[:MEDIAN_SAMPLES]].float().to(device)
    model = TopKSae(x.shape[1], round(config.expansion * x.shape[1]), config.k, geometric_median(sample)).to(device)
    optimiser = torch.optim.Adam(model.parameters(), lr=config.lr, betas=(0.9, 0.999))
    last_fired = torch.zeros(model.encoder.shape[0], dtype=torch.long, device=device)
    curve, step = [], 0
    for epoch in range(config.epochs):
        order = torch.randperm(len(x), generator=generator)
        for start in range(0, len(x), config.batch):
            batch = x[order[start:start + config.batch]].float().to(device)
            reconstruction, latents, pre = model(batch)
            last_fired[(latents > 0).any(dim=0)] = step
            dead = step - last_fired >= DEAD_AFTER_STEPS
            main = ((batch - reconstruction) ** 2).sum(dim=-1).mean()
            loss = main + AUX_COEFFICIENT * aux_loss(model, batch, reconstruction, pre, dead)
            optimiser.zero_grad()
            loss.backward()
            model.project_decoder_gradient()
            nn.utils.clip_grad_norm_(model.parameters(), config.grad_clip)
            optimiser.step()
            model.normalise_decoder()
            step += 1
        curve.append({"epoch": epoch, "loss": float(loss.detach()), "dead_fraction": float(dead.float().mean())})
    return model, curve


def seed_agreement(decoders: list[torch.Tensor]) -> float:
    """Mean over seed pairs and latents of each latent's best |cosine| with any latent of the other seed: 1 when two
    seeds learn the same dictionary up to order and sign (PRD 12.2's consistency check)."""
    scores = []
    for first in range(len(decoders)):
        for second in range(first + 1, len(decoders)):
            cosine = (decoders[first].T @ decoders[second]).abs()
            scores.append(float(cosine.max(dim=1).values.mean()))
    return sum(scores) / len(scores) if scores else float("nan")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("shards", type=Path, nargs="+")
    parser.add_argument("--layer", type=int, required=True)
    parser.add_argument("--k", type=int, default=64)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    config = SaeConfig(layer=args.layer, k=args.k, seed=args.seed, epochs=args.epochs)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    tokens, bases = load_tokens(args.shards, args.layer)
    held = held_out_mask(bases, args.seed)
    x = normalise(tokens.float())
    model, curve = train(x[torch.from_numpy(~held)].to(device), config, device)
    metrics: dict[str, Any] = {"config": asdict(config), "train_tokens": int((~held).sum()),
                               "held_out_tokens": int(held.sum()), "dead_fraction_at_end": curve[-1]["dead_fraction"],
                               "held_out": evaluate(model, x[torch.from_numpy(held)].to(device), config.batch),
                               "curve": curve}
    args.output.mkdir(parents=True, exist_ok=True)
    torch.save({"config": asdict(config), "state": model.state_dict()}, args.output / "sae.pt")
    (args.output / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")
    print(json.dumps({key: value for key, value in metrics.items() if key != "curve"}, indent=2))


if __name__ == "__main__":
    main()
