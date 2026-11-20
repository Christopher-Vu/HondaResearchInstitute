# j20 and j21: a self-supervised route encoder (exploratory, dev, H21b only)

Laptop worker 20261120-055952-26854, 2026-11-20. These are dev numbers. None of them can enter the UniAD read (`docs/prereg-views.md`, tag `views-prereg-v1`). No number here is significant, confirmed or a finding. Every score was measured on this laptop. The rows are in `VARIANTS.md` under "Exploratory, H21b pool, laptop j20-j21 (2026-11-20)". They were committed before any score was read: j20 in `a5824c9` and j21 in `a428935`.

## What the methods do

- **j20.** A small encoder learns a 32-number summary of each route from the per-frame activations alone. It never sees pass or fail, the route type or the manifest.
  - **Input.** `frames.npz`, layer 8, the last 50 frames. Padding frames are masked. Each column is standardised over all frames, then reduced to 64 numbers by PCA (principal component analysis), which is fit on all frames.
  - **Encoder.** Two 1-D convolutions over time, with kernel 5 and 64 channels. A mean over the frames follows, then a linear map to 32 numbers. The output is scaled to unit length.
  - **Training.** The loss is SimCLR's NT-Xent. Two "views" of a route are two random contiguous stretches of it, each at least half its length, with small Gaussian noise added. The loss pulls the two views of a route together and pushes every other route in the batch away. Temperature 0.1, batch 128, 100 epochs, Adam. The run uses seed 0 on the CPU with one thread and deterministic algorithms.
  - **Axes.** Ward clustering of the failing routes' embeddings, cut at 2, 3 and 5 as m15 does, then continued under amendment A2 to 10 distinct axes. The order is label-free: cut order, then the largest cluster first. The result is pooled with whole-route L8 (m03) by `pool_axes.py`, with whole-route first.
- **j21.** It is j20 with temperature 0.5. The reason is in the next section.

## Scores

Measured with 2,000 replicates. `pair` is stripped of its `-sNN` suffix, so 100 Fail2Drive pairs are resampled. There are 593 routes and 174 of them fail.

| row | score | CustomObstacles | Wall | PedestriansOnRoad | vs B3-behaviour | vs B3-infraction | tried |
|---|---:|---:|---:|---:|---|---|---|
| j20 | 0.291 | 0.243 | 0.529 | 0.100 | +0.139 [+0.016, +0.296], p 0.011 | +0.004 [−0.139, +0.177], p 0.45 | 224 + 1 |
| j21 | 0.280 | 0.198 | 0.529 | 0.111 | +0.127 [−0.006, +0.290], p 0.037 | −0.007 [−0.159, +0.180], p 0.51 | 224 + 2 |
| m23 (recorded) | 0.395 | 0.210 | 0.529 | 0.444 | | | |
| B3-behaviour | 0.152 | 0.191 | 0.165 | 0.101 | | | |
| B3-infraction | 0.287 | 0.394 | 0.200 | 0.267 | | | |

The failing-only chance is 0.121 for j20 and 0.120 for j21. Both rows have recall at Jaccard 0.5 of 0.33 and 0 decoy hits.

**Training-seed spread for j20 (robustness, not tries, 200 replicates, measured).**

| training seed | score | PedestriansOnRoad | vs B3-behaviour |
|---|---:|---:|---|
| 0 (the j20 score, 2,000 replicates) | 0.291 | 0.100 | p 0.011 |
| 1 | 0.287 | 0.122 | p 0.040 |
| 2 | 0.274 | 0.081 | p 0.020 |
| 3 | 0.269 | 0.068 | p 0.055 |

The four seeds span 0.269 to 0.291. In every seed CustomObstacles is 0.210 or more and Wall is 0.529.

## Reading

- Both rows sit below m23 and are not separated from B3-infraction.
- The loss is in PedestriansOnRoad, which falls from m23's 0.444 to between 0.068 and 0.122 across all runs. Wall equals m23's value. That match probably comes from the shared whole-route source, but no per-axis attribution was run, so this is unverified.
- **The j21 reason (label-free, from j20's outputs).** The j20 Ward tree splits the failing routes into even blocks, 110 and 64 at cut 2, and no top-10 axis has fewer than 12 routes. m15 and whole-route L8 instead split off small tight groups, 167/7 and 166/8. The j20 axes also agree only loosely across training seeds (best-match Jaccard 0.10 to 0.73). The embedding is only partly a linear function of the route's mean input: the 5-fold ridge R² is 0.39 to 0.48 over seeds 0 to 3. A low temperature makes the loss spread routes evenly over the sphere, so j21 raised it to 0.5.
- At temperature 0.5 the tree was less even: 137 and 37 at cut 2, with two axes under 10 routes. The score did not improve (0.280), and the pedestrian group did not come back.
- The training loss at temperature 0.1 fell from 2.71 to 0.145. Telling two stretches of the same route apart from other routes is easy, so the encoder may not need features that separate failure kinds. This is unverified.

## Compute

Each training run took 136 to 172 s on one CPU thread (measured). The earlier draft's settings (128 channels, 200 epochs) ran at about 8 s per epoch, which projects past the 20-minute limit. It was stopped before it wrote any output, and the defaults became 64 channels and 100 epochs before the rows were written. The battery monitor reported drain while the laptop was on power. The top CPU users were other processes. The runs were kept sequential on one thread.

## Checks

- `route-L8`, `b3_behaviour` and `b3_infraction` were rebuilt here. Their axes equal `results/h21/j18/axes/` exactly.
- `tests/test_j20_ssl.py` checks four things. The same input gives the same embedding hash and axes. Changing the pass/fail flags leaves the embedding and the loss unchanged, so the encoder does not read the label. Axes hold only failing routes. Padding is masked.
- `frames.npz` and `cache-w50.npz` have the same `route_id` and `meta` in the same salted order. The NaN mean of the frames matches the cache window to 0.002 (measured).

## Files

- `commands.sh` holds the exact commands.
- `axes/` holds the j20 and j21 sources, the pools, the rivals, route-L8 and the embeddings (`*.embedding.npy`).
- `report-j20.json` and `report-j21.json` are the scorer's reports.
- `seeds/` holds the training-seed check.
