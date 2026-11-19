# H21b headline: independent reproduction (dev)

Laptop worker 20261119-143947-7082, 2026-11-19. Scorer: `score_repro.py`, written from
`docs/prereg-fail2drive.md` A1 and A2 before the existing scorer was read. Output: `scores.json`.

## Result

All five point scores reproduce exactly. Both intervals differ, and the cause is the bootstrap's resampling unit.

| Method or contrast | This scorer | Recorded | Difference | Cause |
|---|---:|---:|---:|---|
| m23 | 0.395 | 0.395 | 0.000 | none |
| m40 | 0.310 | 0.310 | 0.000 | none |
| j09 | 0.298 | 0.298 | 0.000 | none |
| B3-behaviour | 0.152 | 0.152 | 0.000 | none |
| B3-infraction | 0.287 | 0.287 | 0.000 | none |
| m23 - B3-behaviour, delta | +0.242 | +0.242 | 0.000 | none |
| m23 - B3-behaviour, 95% interval | [+0.041, +0.450] | [+0.111, +0.380] | -0.070, +0.070 | resampling unit (below) |
| m23 - B3-behaviour, one-sided p | 0.005 | 0.000 | +0.005 | resampling unit |
| m23 - B3-infraction, delta | +0.108 | +0.108 | 0.000 | none |
| m23 - B3-infraction, 95% interval | [-0.091, +0.335] | [-0.030, +0.260] | -0.061, +0.075 | resampling unit |
| m23 - B3-infraction, one-sided p | 0.173 | 0.080 | +0.093 | resampling unit |

Pool: 593 scored routes, 174 failing, 100 Fail2Drive pairs over seeds 24-26. Gap failures: CustomObstacles 28, Wall 14,
PedestriansOnRoad 9. Bootstrap seed 0. Seeds 1 and 2 give m23 - B3-behaviour [+0.042, +0.453] and [+0.032, +0.464],
and m23 - B3-infraction [-0.079, +0.338] and [-0.091, +0.343], so Monte Carlo noise is about 0.01.

## Cause of the interval difference

The two scorers use the same weighted Jaccard (a resampled pair's routes count once per draw). They differ in what a
"pair" is.

- In the H21b manifest, `pair` and `base_id` carry the seed: `f2d-99-s24`, `f2d-99-s25`, `f2d-99-s26`.
- `sprint_score.py` resamples `e["pair"]` (line 106), so it draws 299 pair-seed units independently. The three seeds of
  one Fail2Drive route are treated as unrelated.
- `score_repro.py` strips the `-sNN` suffix and draws 100 Fail2Drive pairs, each carrying its three seeds.
- With the seed-tagged unit, `score_repro.py` gives m23 - B3-behaviour [+0.109, +0.382] (p 0.000) and
  m23 - B3-infraction [-0.032, +0.262] (p 0.075), within noise of the recorded numbers. So the unit explains all of it.

**Which follows the pre-registration:** this scorer. A1, Statistics: "These come from a paired bootstrap of 2,000
replicates that resamples Fail2Drive pairs, each carrying all its seeds." The `sprint_score.py` docstring says the same,
but the pool's manifest gives it seed-specific pairs, so it does not do it on H21b.

The seeds of one route are correlated (same route, same model), so the recorded intervals are too narrow. The
qualitative reading does not change: m23 still beats B3-behaviour with an interval above 0, and still does not separate
from B3-infraction.

## Not checked

- TransFuser++ round 1 (m23 0.117 against B3-behaviour 0.079): that data is not on this laptop, so it was not attempted.
- The "pair carries the seed" issue may also affect other pooled-seed reports built with the same pool builder
  (`build_pool.py`, not on this laptop). Single-seed pools are unaffected, since one seed per pair makes the two units
  the same. Unverified.
- The gap list (CustomObstacles, Wall, PedestriansOnRoad) was taken as an input from `../h21b/SUMMARY.md`, not
  re-derived by the units rule.
- `results/savio/f2d-h21b/pooled/` is not in this clone. The same pool is at `results/h21/h21b/` (`routes.jsonl`,
  `manifest.json`), which is what was scored.

## Command

```bash
A=results/h21/h21b/axes
PYTHONPATH=src /opt/miniconda3/bin/python results/h21/repro/score_repro.py \
  --manifest results/h21/h21b/manifest.json --routes results/h21/h21b/routes.jsonl \
  --gaps F2D_CustomObstacles F2D_Wall F2D_PedestriansOnRoad \
  --method m23=$A/m23.json --method m40=$A/m40.json --method j09=$A/j09.json \
  --method B3-behaviour=$A/b3_behaviour.json --method B3-infraction=$A/b3_infraction.json \
  --compare m23:B3-behaviour --compare m23:B3-infraction --compare m40:B3-behaviour --compare j09:B3-behaviour \
  --output results/h21/repro/scores.json
```
