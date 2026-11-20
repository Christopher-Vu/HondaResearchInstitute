# Audit: the one-command UniAD views read against `views-prereg-v1`

Auditor: LAPTOPWORKER 20261119-185011-8298, 2026-11-19. Independent of the second auditor.
Audited at HEAD `0a57ce0` on branch `lw/20261119-185011-8298`. Nothing under `gaps/sealed/`, no UniAD output and no
`results/savio/<UniAD job>/` folder was opened.

## Sources checked

- Prereg: `git show views-prereg-v1:docs/prereg-views.md` (tag on `69668f5`, 2026-11-19 13:24:50 -0800). Line numbers
  below are the **tagged** file's ("tag:L"). On HEAD, one later edit, `2847aef`, inserts 9 lines after tag:L27, so tag
  lines from L28 onward sit 9 lines lower on HEAD. That edit is quoted as "HEAD:L28-36".
- Code: `docs/research/experiments/f2d-unpooled/uniad_read.sh`, `view_score.py`, `units_rule.py`, `protocol.md`, and
  everything the read calls: `f2d-dev-simlingo/{sprint_score,cache_pool,cache_methods,pool_axes,b3_behaviour,
  b3_infractions,train_saes}.py`, `f2d-unpooled/uniad_frames.py`, `src/harness/{bootstrap,scoring,scoring_run,
  efficacy}.py`, `adapters/simlingo/export_activations.py`, the capture agents (`adapters/simlingo/capture_agent.py`,
  `adapters/tfpp/tfpp_agent.py`, `adapters/uniad/uniad_agent.py`), `configs/rollout/f2d-test-uniad-s10*.yaml`,
  `f2d-screen-uniad.yaml`, `f2d-test-simlingo.manifest.json`, `f2d-tfpp-screen.manifest.json`, `transfer-spec.md`,
  `heldout.sh`, and `f2d-views-caption/{agents.py,export.sh,protocol.md}`.
- Commits: `dac5035` (read added, 13:27:55), `f14b40d` (pooled named gaps without a UniAD one, 13:35), `7d89d1c`
  (caption frame export, 18:18), `2847aef` (post-tag prereg record, 18:19), `3ef2629` (median-over-runs rows, 18:21).
  Every one of them is later than the tag.

## Line-by-line table

Abbreviations: `read` = `uniad_read.sh`, `vs` = `view_score.py`, `ur` = `units_rule.py`, `cm` = `cache_methods.py`,
`ss` = `sprint_score.py`. All in `docs/research/experiments/` unless a path is given.

### (1) Rows, views and settings

| # | Item | Prereg text | Code | Verdict | Severity |
|---|---|---|---|---|---|
| 1 | Two headlines | tag:L9-11 "The pooled three-model ranking ... UniAD alone, labelled as the only blind test" | read:166-172 (3 UniAD-alone and 3 pooled scorings); labels read:36, read:169 | match | - |
| 2 | Rows | tag:L51-57 B3-behaviour, B3-infraction, B7-pool, m23, m40, img-mean, query-mean, caption | read:144-150 has the first seven; no caption row | match for 7 rows; caption: see #20 | - |
| 3 | img-topk dropped | tag:L15 "`img-topk` is dropped everywhere" | read:144-150 has no topk row | match | - |
| 4 | Rivals and finalists as transfer-spec | tag:L51-52 "per model as in `transfer-spec.md` ... §9 and `transfer-spec.md`, unchanged" | read:112-122 vs `f2d-dev-simlingo/heldout.sh:29-39` and `transfer-spec.md:29-61` (m23 8/23 window+route; m40 8/23 dims 64 + route 20/23; B7 at 10/23, k 18, seed 0, min support 20) | match | - |
| 5 | UniAD image site | tag:L16 "the last BEV encoder grid"; HEAD:L29-30 "The last layer is used at every site" | read:100-110: `all_tokens` at the highest `bev_encoder.N`; `uniad_agent.py:8-9` (mean over all BEV cells) | match | - |
| 6 | UniAD query site | tag:L16 "the track queries are the query site"; HEAD:L29-30 last layer | read:105,111: `all_tokens` at the highest `track_decoder.N` (mean over all track queries) | match | - |
| 7 | UniAD FPN rows | tag:L16-17 "The FPN rows are reported only" | read: no FPN row | mismatch (not reported) | cosmetic |
| 8 | SimLingo image site | tag:L22 "The image site stays `llm10`"; tag:L66 "`llm10`"; `protocol.md:27` "`llm10`: the same 512 image tokens in the language model's layer 10 output"; tag:L55 "`img-mean`: the per-frame mean over the image-token site" | read:126-127 `--site all_tokens --layer 10`. `all_tokens` is `layer_mean` (`export_activations.py:114`), which is the mean over **every sequence position** at that layer (`adapters/simlingo/capture_agent.py:179-180`, `stacked.float().mean(dim=1)`): prompt, image and driving-query tokens. The unpooled llm10 row took only the 512 image positions (`replay_unpooled.py:14,87-90,122`) | **mismatch** | changes the read (pooled ranking's SimLingo img-mean row) |
| 9 | `SIMLINGO_IMG=vit` switch | tag:L58-62 "`vit-mean` ... the pooled vision tokens before the projector ... does not change the image site, which stays `llm10`" | read:126: with `SIMLINGO_IMG=vit` the img-mean row becomes `vision_bridge`, which is the **projector output** (`capture_agent.py:3-4,166-167`, `mlp1`), not the tokens before it | mismatch (latent; default is llm10) | cosmetic unless the variable is set |
| 10 | Cached SimLingo/TF++ rows | tag:L48 "Rows (fixed at the tag)" | read:127-130 `[ -f $V/... ] \|\|` reuses any file already at `results/savio/f2d-views/{simlingo,tfpp}/*.json`, whatever built it | unclear (cannot see Savio) | changes the read if a stale file exists |
| 11 | vit-mean post hoc row | tag:L58-62 "reported as a labelled post hoc row" | read: absent | mismatch (not produced by the read) | cosmetic (no ranking claim) |
| 12 | TF++ image site | tag:L67 "the fused backbone grid (`vision_bridge`)" | read:129 `--site vision_bridge` | match | - |
| 13 | TF++ query site | tag:L67 "the decoder join tokens"; HEAD:L29 "the last layer ... the TF++ join tokens" | read:130 `--site driving_queries --layer-fraction 1`. On TF++ `driving_queries` is the **last `join` call only** (the checkpoint query; `adapters/tfpp/tfpp_agent.py:10-11`, `transfer-spec.md:21`). The mean over every join token is `all_tokens` (`tfpp_agent.py:8-9`). UniAD's query-mean (#6) uses `all_tokens` | unclear, leaning mismatch | changes the read (pooled TF++ query-mean row) |
| 14 | SimLingo query site | tag:L66 "`dq`, driving queries at layer 10" | read:128 `--site driving_queries --layer 10`; `capture_agent.py:181` | match | - |
| 15 | Approach window | tag:L70 "12.5 s before the failure step, or the route's last 12.5 s" | read:63 `--window 50`; export stride 5 (`adapters/simlingo/export_activations.py:202`); UniAD logs every step (`uniad_agent.py:7`); `cache_pool.py:38-41` takes frames strictly before the failure step, else the last 50. 50 x 5 steps = 250 steps = 12.5 s at 20 Hz | match (20 Hz from code comments, not measured) | - |
| 16 | Discovery step | tag:L70-72 "m03: standardise, PCA 32 over all routes, Ward clustering of the failing routes, A2 distinct axes, top 10" | `cm:117` (standardise, PCA, dims 32 default `cm:136`), `cm:58` Ward on failing, `cm:62-73` A2, `cm:177` `[:10]` | match | - |
| 17 | Fit on scored routes | tag:L72 "runs on the routes being scored" | UniAD cache from the merged routes only (read:44-63). SimLingo/TF++ caches at `$REF` paths (read:125) | match for UniAD; unclear for SimLingo/TF++ (not on laptop) | - |
| 18 | Try count | tag:L54 "219"; tag:L170 "the full try count ... reported whatever the result" | read: nothing prints a try count | mismatch | cosmetic |

### (2) Units

| # | Item | Prereg text | Code | Verdict | Severity |
|---|---|---|---|---|---|
| 19 | Rule | tag:L156-158 "at least 1.5x as often as their base twins, with at least 5 failing generalisation routes" | `ur:19,44` `sum(s) >= 5 and (rt == 0 or rs >= 1.5 * rt)`; twins from `neighbourhood_of` (`ur:38-39`) | match | - |
| 20 | Rule runs inside the read on its routes | tag:L156, L179-180 | read:134 on `$MANIFEST $R` of this read; read:135-136 on SimLingo/TF++ test pools | match | - |
| 21 | Primary minus Wall, by name | tag:L12, L159 | read:137 `grep -v ':F2D_Wall$'`, used at read:166,170; type name `F2D_Wall` exists in the test manifest | match | - |
| 22 | All rule units and named gaps reported | tag:L13-14, L160 | read:167-168, 171-172; UniAD named gaps from `prereg-fail2drive.md` §1 class "gap", ceilings excluded (read:80-87); SimLingo 3 and TF++ 2 hardcoded (read:140-141, as `heldout.sh:20,43`) | match | - |
| 23 | Synonym list | tag:L131-151 | `f2d-views-caption/agents.py:144-168` parses the prereg table: 17 types parsed (measured). It parses the HEAD file, whose table is unchanged since the tag (`git diff views-prereg-v1 HEAD` touches only HEAD:L28-36) | match | - |

### (3) Metric

| # | Item | Prereg text | Code | Verdict | Severity |
|---|---|---|---|---|---|
| 24 | Primary rank-averaged best match | tag:L161; `protocol.md:67-70` "mean over k = 1..10 of the best Jaccard among the method's top-k axes" | `vs:40-48`; per unit equal weight `vs:108-110` | match | - |
| 25 | Secondary top-10 best match | tag:L161 | `vs:109` -> `ss:56-57` | match | - |
| 26 | Budget M = 10, own order (A1), distinct (A2) | tag:L71 "A2 distinct axes, top 10" | `ss:31` M = 10; `ss:34-40` drops exact repeats then `[:10]`; `ss:43-53` keeps file order or directive rank order; `vs:90` | match | - |
| 27 | Precision denominator | not used by the views prereg | no precision metric anywhere in the read | match (nothing to check) | - |
| 28 | Empty sets | CLAUDE.md "jaccard(empty, empty) == 0" | `src/harness/scoring.py:21-26`, `src/harness/bootstrap.py:31-35` | match | - |

### (4) Intervals

| # | Item | Prereg text | Code | Verdict | Severity |
|---|---|---|---|---|---|
| 29 | Replicates | tag:L162 "2,000 draws" | `vs:66` default 2000; read:162 does not override | match | - |
| 30 | Resampling unit | tag:L162 "a pair bootstrap"; `prereg-fail2drive.md:95` "resampling Fail2Drive pairs jointly across models and seeds" | `vs:79,105,125-126`: weight = draw count of the route's `pair`, keys prefixed by model so one pair carries every model | match | - |
| 31 | Pair field, test mode | as #30 | test CONFIG manifest is `f2d-test-simlingo.manifest.json` (`f2d-test-uniad-s101.yaml:31`); its `pair` has no seed (`"f2d-75"`): 100 pairs x 12 routes = 6 seeds x 2 twins (measured). Pooled manifest read:153-158 is the same file in test mode | match | - |
| 32 | Pair field, dev mode | as #30 | screen manifest has no `pair`; read:52 sets `pair = base_id` (`"f2d-75"`), the same strings as the test pool | match | - |
| 33 | Bootstrap seed | not fixed in the prereg | `vs:67` seed 0 | match (unspecified) | - |
| 34 | Sidedness | tag:L166 "95% interval ... lies above 0" | `vs:51-53` two-sided 2.5/97.5 percentiles; one-sided p beside it | match | - |
| 35 | Pooled = fixed mean over units | tag:L162 | `vs:110` plain mean over all units of all models | match | - |

### (5) Decision rule and selection

| # | Item | Prereg text | Code | Verdict | Severity |
|---|---|---|---|---|---|
| 36 | Row above fleet | tag:L166 | `vs:135-138` interval vs `--primary-rival B3_behaviour` (read:162) | match | - |
| 37 | Row A above row B | tag:L167-168 "only if the paired interval of A minus B lies above 0 ... the ranking is the partial order these intervals give" | `vs` writes only each row minus B3-behaviour (`vs:135-138`) and `--select` contrasts (`vs:139-156`); the draws are not saved. read:162 passes no `--select`. No A-minus-B interval for other row pairs is produced | **mismatch** | changes the read (the ranking cannot be built from the output) |
| 38 | Selection adjustment | tag:L169 "wherever a 'best of the new views' is quoted, it is re-selected in every draw" | `vs:139-156` supports it; read:162 passes no `--select` | **mismatch** (missing) | changes the read if a best new view is quoted |
| 39 | Each model alone | tag:L170 | the read scores UniAD alone and pooled only; SimLingo and TF++ alone are Order step 2 (tag:L185) | unclear (outside the read) | cosmetic |

### (6) Coverage and what the read prints

| # | Item | Prereg text | Code | Verdict | Severity |
|---|---|---|---|---|---|
| 40 | Interim uses every driven route | tag:L24, L175 "every test-pool route that has a driven record by then" | read:35 fixed list of 18 jobs (override `JOBS`); read:43 silently skips a listed job with no folder | unclear (job list completeness not checkable here) | changes the read if a job is missing from the list |
| 41 | Missing last job stops the read | - | read:43 under `set -euo pipefail`: if the **last** job in `JOBS` has no folder, the `for` loop returns 1 and the assignment kills the script with no message (reproduced in bash) | bug | blocks the read (no wrong number) |
| 42 | Interim label and coverage | tag:L176 "labelled interim, with coverage stated: routes, pairs, and failing routes per unit" | label read:36; `coverage.json` read:88-95; `vs:162` prints units (failing routes per unit), routes and Fail2Drive pairs into each log; read:174-175 prints them | match | - |
| 43 | Coverage field names | as #42 | read:90-93: `twin_pairs_*` counts per-seed base/twin pairs (600 listed), not the 100 Fail2Drive pairs; `jobs` lists the requested jobs, not those found | mismatch (labels) | cosmetic |
| 44 | Intervals in printed output | tag:L166-168 | `vs:162-165` prints point scores only; intervals are only in `$O/*.json` | mismatch (printing) | cosmetic |
| 45 | Scorer failure visibility | - | read:163,173 runs scorers with `&` and bare `wait`, so a crashed scorer does not fail the read; it shows only in its log | risk | cosmetic |
| 46 | Caption row and its paired rescoring | tag:L57; tag:L123-129 "The other rows and rivals are rescored on the same routes beside it" | read:66-71 only exports frames. Scoring is manual (`f2d-views-caption/protocol.md` steps 4-10: agents, `to_axes.py`, `vs --row caption ...=runs:`, `--restrict`). `vs:86-89,112-118` has the median-of-runs path | mismatch for a one-command read | changes the read if the interim is reported without the caption row |
| 47 | Caption frames | tag:L80-90; HEAD:L31 "upscaled to 640" | `uniad_frames.py:27,31-34,65-67`; `uniad_agent.py:47-48` (every 5 steps, 256 px) | match | - |
| 48 | Label hiding | tag:L100-103 | salt read:68-69 (kept across reads); folders `sha256(salt+id)[:12]` `uniad_frames.py:60`; mapping refused inside the frames tree `uniad_frames.py:44-45` | match | - |
| 49 | UniAD marker check | tag:L118-120 "frame 200 of 2 routes per type per model" | `f2d-views-caption/export.sh:16-17` runs `markers.py` for SimLingo/TF++; `read` never calls it, so no UniAD marker sheet is made | mismatch | cosmetic (a flag, not a number) |
| 50 | debug_level 0 | tag:L116 | `configs/rollout/f2d-test-uniad-s101..s106.yaml:22` all `debug_level: 0` | match | - |

### (7) Tag gate and outcome reading

| # | Item | Prereg text | Code | Verdict | Severity |
|---|---|---|---|---|---|
| 51 | Test read refuses without the tag | tag:L4 "none is read before the tag" | read:32 checks `refs/tags/views-prereg-v1` before any test-mode step | match | - |
| 52 | Gate strength | - | read:32 checks only that a ref of that name exists, not that it is `69668f5` or an ancestor of HEAD | weak | cosmetic (the tag exists) |
| 53 | Dev mode has no gate | tag:L43 seeds 24-26 are dev | read:27-30; `JOBS` override could point dev mode at test jobs | risk | cosmetic |
| 54 | Post-tag prereg edit | CLAUDE.md: divergences get a `CONFLICTS.md` entry | `2847aef` fixes the TF++/UniAD layers, frame upscaling and caption mechanics after the tag; no `CONFLICTS.md` entry mentions it | process gap | cosmetic |
| 55 | Code frozen by the tag | - | the tag freezes only `docs/prereg-views.md`; all five audited commits are after it | unclear (no evidence of an outcome read; cannot verify) | - |

## Dry run on dev data (SimLingo H21b pool, seeds 24-26, never evidence)

Setup: `results/h21/h21b/manifest.json` with `-sNN` stripped from `pair` (300 -> 100 pairs), written to
`dry/manifest-stripped.json`. Stage 4 of the read run unchanged by `dry/run.sh`, with the model named `uniad` so the
read's own unit filters (read:137-138, 161) run as written. Rows: B3-behaviour, B3-infraction, m23, m40, j09 from
`results/h21/h21b/axes/`. Stages 1-3 (merge, shards, caches, row building) need the Savio job folders and were not run.

- `units_rule.py`: ran, exit 0. Units: Animals, BadParking, CustomObstacles, FullyBlocked, PedestriansOnRoad,
  RightConstruction, Wall (7). Without Wall: 6. Output `dry/units-uniad.txt`.
- `view_score.py`: ran, exit 0, for all three UniAD-alone scorings and a pooled-path mechanics check. 593 routes,
  100 pairs, 174 failing.

Measured (dev only), rank-averaged best match, and the interval against B3-behaviour:

| Units | B3-behaviour | B3-infraction | m23 | m40 | j09 |
|---|---|---|---|---|---|
| rule without Wall (6) | 0.133 | 0.214 [+0.036, +0.121] | 0.190 [-0.004, +0.135] | 0.168 [-0.002, +0.102] | 0.133 [-0.039, +0.059] |
| all rule (7) | 0.129 | 0.210 [+0.040, +0.116] | 0.213 [+0.023, +0.157] | 0.186 [+0.011, +0.127] | 0.150 [-0.015, +0.080] |
| named (3) | 0.116 | 0.252 [+0.074, +0.200] | 0.288 [+0.033, +0.340] | 0.199 [-0.008, +0.200] | 0.187 [+0.025, +0.143] |

- Control with the seed-suffixed pairs (299 pairs, the wrong unit): point scores identical, m23's interval narrows from
  [-0.004, +0.135] to [+0.010, +0.104] and crosses 0. The read itself is not exposed, because the test manifest's
  `pair` carries no seed (#31), but any dev check on the H21b manifest must strip the suffix.
- Pooled path (the same pool entered twice as `simlingo` and `uniad`): 1,186 routes, 100 pairs, results identical to
  one copy. This confirms that one pair carries both models' routes in a draw.
- As #44 says, the logs print only point scores (e.g. `{"m23": [0.19, 0.238]}`); the intervals above were read from
  the JSON files.

## Real mismatches

1. **SimLingo img-mean is the all-token mean, not the 512 image tokens (`llm10`).** `uniad_read.sh:126-127` uses
   `--site all_tokens --layer 10`, which is `capture_agent.py:180`'s mean over every sequence position. Prereg tag:L22,
   L55, L66 and `protocol.md:27`. It changes the pooled ranking's SimLingo img-mean row.
2. **No row-versus-row intervals, so the ranking cannot be built.** Tag:L167-168 ranks A above B only on a paired A-B
   interval. `view_score.py:135-138` writes only each row minus B3-behaviour, and `uniad_read.sh:162` passes no
   `--select`. The draws are not saved.
3. **No selection-adjusted "best new view".** Tag:L169. `uniad_read.sh:162` passes no `--select`, so any best-of
   quote from this output would be unadjusted.
4. **TF++ query-mean probably uses the wrong token set.** `uniad_read.sh:130` uses `driving_queries` (the last `join`
   call only, `tfpp_agent.py:10-11`) where tag:L67 says "the decoder join tokens" (every join token is `all_tokens`,
   `tfpp_agent.py:8-9`). It is marked unclear, because "join tokens" could be read either way.
5. **The caption row is not in the one-command read.** Tag:L57, L123-129. `uniad_read.sh:66-71` only exports frames.
   Its scoring, its paired `--restrict` rescoring, and the UniAD marker sheet (tag:L118-120) are manual steps outside
   the read.
6. **A missing last job stops the read silently.** `uniad_read.sh:43` under `set -e`. It produces no wrong number,
   but it could stop the 09:00 run.

Cosmetic, listed in the table: FPN rows and vit-mean not reported (#7, #11), no try count (#18), latent
`SIMLINGO_IMG=vit` switch (#9), coverage field names (#43), intervals not printed (#44), weak tag gate (#52), and no
`CONFLICTS.md` entry for `2847aef` (#54).

## Unverified

- That the `$REF` SimLingo/TF++ caches and rows cover the routes being scored, and that no stale
  `results/savio/f2d-views/{simlingo,tfpp}/*.json` exists (#10, #17).
- That the 18-job list holds every driven test route (#40).
- That the simulator runs at 20 Hz, so 50 frames = 12.5 s (#15). This comes from code comments, not a measurement.
- Stages 1-3 of the read (merge, export, cache, row building, B7, frames, classes). They need the Savio job folders.

## Commands

```bash
git show views-prereg-v1:docs/prereg-views.md
git diff views-prereg-v1 HEAD -- docs/prereg-views.md
git show dac5035 f14b40d 7d89d1c 3ef2629 2847aef
bash results/h21/audit-20261119-185011-8298/dry/run.sh      # the dry run; builds on dry/manifest-stripped.json
```

`dry/manifest-stripped.json` was built from `results/h21/h21b/manifest.json` by replacing each `pair` with
`re.sub(r"-s\d+$", "", pair)`, using `/opt/miniconda3/bin/python`.
