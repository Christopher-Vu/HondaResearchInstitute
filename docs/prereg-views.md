# Pre-registration: a ranking of failure-discovery views across three driving models

**Status: DRAFT, not tagged.** Written 2026-11-19 by Chris's agent after the unpooled experiment was read
(`docs/research/experiments/f2d-unpooled/protocol.md`; the reading was "neither"). It becomes binding when Chris
approves it and it is tagged `views-prereg-v1`. No UniAD outcome has been read; none is read before the tag
(`docs/prereg-fail2drive.md` §10, A4).

## Open for Chris before the tag

1. **The settled row.** The unpooled reading was "neither", so no unpooled row becomes the headline. Proposal: carry
   one unpooled row, `topk` at each model's image-token site, as a named row. That is SimLingo's best grid row in every
   draw. Carry the averaged rows at the same sites beside it.
2. **The UniAD site mapping** for the averaged and top-k rows. Proposal: UniAD's last BEV encoder grid as the image
   site, and the track queries as the query site (the `dq` analogue). The FPN rows are reported only.
3. **Whether the rank claim needs UniAD alone or all three models pooled.** Proposal: pooled is the headline, and
   UniAD alone is reported beside it, because only UniAD is blind.

## Question

Which ways of looking at a driving model find its Fail2Drive gaps best, and is any of them better than what a fleet
already observes (the car's behaviour)? The answer comes as a ranking with honest, narrow intervals across SimLingo,
TransFuser++ (TF++) and UniAD.

## Data and labels

| Model | Pool | Outcomes |
|---|---|---|
| SimLingo | test pool, 1,185 scored routes | already read (dev for rounds 1–2) |
| TF++ | test pool; the image rows use re-driven pairs that contain a failure, where the failure reproduces | already read |
| UniAD | test pool, routes with the unpooled capture | **blind** until the tag |

- Every SimLingo and TF++ number is labelled "outcomes already read".
- Seeds 24–26 (H21, H21b) are a dev pool and never count as evidence.
- Coverage (routes, pairs, failing routes per gap) is stated beside every row on TF++ and UniAD.
- Every preparation step (PCA, codebook, baseline) is fit only on the routes that have that row's capture.
- Every rival is rescored on the same routes, so contrasts stay paired.

## Rows (fixed at the tag)

Rivals and frozen finalists (not new tries):
- **B3-behaviour** (primary rival), **B3-infraction**, **B7-pool**: per model, as in `transfer-spec.md`.
- **m23** (primary finalist) and **m40**: §9 and `transfer-spec.md`, unchanged.

New views. Each counts as a try; the running total is 216 before the tag.
- `img-mean` and `img-topk` at each model's image-token site, and `query-mean` at its query site. The mapping is
  open item 2:

  | Model | Image-token site | Query site |
  |---|---|---|
  | SimLingo | `llm10` | `dq` |
  | TF++ | backbone output grid | decoder join tokens |
  | UniAD | BEV grid | track queries |

- Discovery is m03 for every new view, the same as the unpooled grid. The window is the last 25 saved frames before
  the failure, or the route's last 25.

## Units, metric and intervals

As in the unpooled protocol:
- **Units:** the named gaps plus the units by rule (`units_rule.py`; on UniAD the rule runs inside the blind read),
  reported with and without Wall.
- **Metric:** the rank-averaged best match is primary, and top-10 best match is secondary.
- **Intervals:** a pair bootstrap with 2,000 draws. The pooled number is a fixed mean over units, with no random
  effect.

## Decision rule

- **A row ranks above the fleet** if its pooled three-model 95% interval against B3-behaviour lies above 0.
- **Row A ranks above row B** only if the paired interval of A minus B lies above 0. Otherwise they are reported as
  tied, and the ranking is the partial order these intervals give.
- **Selection.** Where a "best of the new views" is quoted, it is re-selected in every draw.
- **Reporting.** UniAD alone, each model alone, and the full try count (216 plus the new views) are reported whatever
  the result.

## Order

1. Chris approves this file, then it is tagged `views-prereg-v1`.
2. The TF++ rows are scored (outcomes already read).
3. The one UniAD read: m23 and m40 under §9, plus every row here.
4. The pooled ranking.
