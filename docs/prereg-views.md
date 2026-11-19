# Pre-registration: a ranking of failure-discovery views across three driving models

**Status: written, awaiting Chris's approval; not yet tagged.** It becomes binding when it is tagged
`views-prereg-v1`. No UniAD outcome has been read, and none is read before the tag (`docs/prereg-fail2drive.md` §10,
A4, as amended by `CONFLICTS.md` C43). Drafted 2026-11-19 after the unpooled experiment was read
(`docs/research/experiments/f2d-unpooled/protocol.md`; its reading was "neither").

## Decisions (Chris, voice, 2026-11-19 ~13:10, before any UniAD outcome is read)

- **Headline:** both of these, each under the decision rule below.
  - The pooled three-model ranking, labelled "SimLingo/TF++ outcomes already read".
  - UniAD alone, labelled as the only blind test.
- **Primary units:** the rule units without Wall. Wall is excluded by name, not by a rule that reads outcomes. Wall
  was set aside as a ceiling control before the sprint and fails on every slice. All rule units (with Wall) and the
  named gaps are reported beside the primary.
- **Rows:** `img-topk` is dropped everywhere. Only the averaged rows are new.
- **UniAD sites:** the last BEV encoder grid is the image site, and the track queries are the query site. The FPN rows
  are reported only.
- **Coverage:** two UniAD reads, both fixed here: an interim on Saturday and the final on the full pool (below).
- **Expected outcome:** "Behaviour ties or beats every view" is an expected, reportable outcome, not a failure of the
  study.

## Question

Which ways of looking at a driving model find its Fail2Drive gaps best, and is any of them better than what a fleet
already observes (the car's behaviour)? The answer is a ranking with honest, narrow intervals across SimLingo,
TransFuser++ (TF++) and UniAD.

## Data

| Model | Pool | Outcomes |
|---|---|---|
| SimLingo | test pool, 1,185 scored routes | already read (dev for rounds 1–2) |
| TF++ | test pool | already read |
| UniAD | test pool, 6 seeds (101–106), 1,200 routes | **blind** until the tag |

- Seeds 24–26 (H21, H21b, and UniAD's screen) are a dev pool and never count as evidence.
- Every row below is computed from per-step layer means that every route logs. So a route counts toward coverage
  once it is driven, whether or not it has the unpooled capture.

## Rows (fixed at the tag)

Rivals and frozen finalists (not new tries):
- **B3-behaviour** (the primary rival), **B3-infraction** and **B7-pool**, per model as in `transfer-spec.md`.
- **m23** (the primary finalist) and **m40**: §9 and `transfer-spec.md`, unchanged.

New views. Each counts as a try, so the running total goes from 216 to **218**:
- **`img-mean`**: the per-frame mean over the image-token site.
- **`query-mean`**: the per-frame mean over the query site.

| Model | Image site | Query site |
|---|---|---|
| SimLingo | `llm10` (see the note to Chris) | `dq`, driving queries at layer 10 |
| TF++ | the fused backbone grid (`vision_bridge`) | the decoder join tokens |
| UniAD | the last BEV encoder grid | the track queries |

Each new view is the mean over the approach window: 12.5 s before the failure step, or the route's last 12.5 s. Its
discovery step is m03: standardise, PCA 32 over all routes, Ward clustering of the failing routes, A2 distinct axes,
top 10. Every fit is label-free and runs on the routes being scored.

## Units, metric and intervals

As in the unpooled protocol:
- **Units:** `units_rule.py`, run inside each read (on UniAD that means inside the blind read). It admits every
  Fail2Drive type whose generalisation routes fail at least 1.5× as often as their base twins, with at least 5
  failing generalisation routes.
  - **Primary:** those units minus Wall.
  - Also reported: all rule units, and the named gaps.
- **Metric:** rank-averaged best match is primary; top-10 best match is secondary.
- **Intervals:** a pair bootstrap with 2,000 draws. Pooled numbers are a fixed mean over units, with no random effect.

## Decision rule (both headlines: pooled, and UniAD alone)

- **A row ranks above the fleet** if its 95% interval against B3-behaviour lies above 0.
- **Row A ranks above row B** only if the paired interval of A minus B lies above 0. Otherwise they tie, and the
  ranking is the partial order these intervals give.
- **Selection:** wherever a "best of the new views" is quoted, it is re-selected in every draw.
- **Reporting:** each model alone, the full try count and the coverage are reported whatever the result.

## UniAD reads

1. **Interim: Saturday 2026-11-21, 09:00 PT.**
   - It uses every test-pool route that has a driven record by then.
   - It is labelled interim, with coverage stated: routes, pairs, and failing routes per unit.
2. **Final: the full 6-seed pool once it lands.** This is the result of record.

Nothing changes between the two reads: not the rows, units, metric or rules. The units rule runs inside each read,
on that read's routes.

## Order

1. Chris approves this file, then it is tagged `views-prereg-v1`.
2. The SimLingo and TF++ rows are scored. Their outcomes are already read, so this needs no tag.
3. The interim UniAD read, then the final.
4. The pooled ranking at each read.
