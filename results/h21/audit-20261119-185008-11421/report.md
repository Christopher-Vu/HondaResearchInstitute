# Audit: the one-command UniAD views read against `views-prereg-v1`

Auditor: laptop worker 20261119-185008-11421, independent. Code at `0a57ce0`. No UniAD output, Savio job folder or
`gaps/sealed/` was opened. `adapters/uniad/` was not read either, so anything that depends on UniAD's layer names is
marked unclear.

Line references:
- "tag L*n*" is a line of `git show views-prereg-v1:docs/prereg-views.md`.
- "main L*n*" is a line of the current `docs/prereg-views.md`.
- `read.sh` is `docs/research/experiments/f2d-unpooled/uniad_read.sh`.
- `vs.py` is `view_score.py` and `ur.py` is `units_rule.py`, both in that folder.

## Prereg edits after the tag

There is one: `2847aef` adds main L28–36 under Decisions and changes nothing else. It fixes the last layer at the TF++
join tokens, UniAD's BEV encoder and UniAD's track queries, which the tag left open. It also records UniAD's 256 px
frames and the caption agents' mechanics. `read.sh` already used the last layers in `dac5035`, before this edit. The
rows, units, metric, intervals and decision rule are unchanged since the tag. The synonym table parsed from main is
identical to the tagged one (checked mechanically: 17 types, same stems).

## Table

| # | Item | Prereg text | Code | Verdict | Severity |
|---|---|---|---|---|---|
| 1a | Rows scored | tag L51–52 "B3-behaviour … B3-infraction and B7-pool … m23 … and m40"; L55–57 `img-mean`, `query-mean`, `caption` | `read.sh:144-150` scores B3_behaviour, B3_infraction, B7_pool, m23, m40, img-mean and query-mean | match, except `caption` (1b) | — |
| 1b | Caption row in the read | tag L57 "`caption` … counts as a try"; L127 "other rows … rescored on the same routes beside it" | not in `read.sh`; only frames are exported (`read.sh:68-71`). Scoring is a separate manual step (`f2d-views-caption/protocol.md:60-67`) | mismatch (scope) | changes the read: the one command cannot rank `caption` or include it in a best-of-new-views selection |
| 1c | `img-topk` dropped | tag L15 | absent from `read.sh` | match | — |
| 1d | `vit-mean` post hoc | tag L58–62 "always labelled post hoc, enters no ranking claim … image site … stays `llm10`" | `read.sh:126-127`: `SIMLINGO_IMG=vit` makes the ViT bridge the row named `img-mean` in the pooled ranking. The `[ -f … ] \|\|` cache then keeps whichever variant ran first | mismatch (latent: default is `llm10`) | changes the read if the variable is ever set or a stale `$V/simlingo/img-mean.json` exists |
| 1e | SimLingo image site | tag L55 "per-frame mean over the image-token site"; L66 `llm10`; `protocol.md:27` "the same 512 image tokens in the language model's layer 10 output" | `read.sh:126` `--site all_tokens --layer 10`. `all_tokens` is `layer_mean`, the mean over the whole sequence (`adapters/simlingo/capture_agent.py:180`, `export_activations.py:114`), which also holds prompt text and driving queries | unclear: the prereg contradicts itself, since tag L44 says every row except caption comes from "per-step layer means that every route logs", and only the whole-sequence mean is logged | changes the read for SimLingo's `img-mean` in the pooled headline, which is not the 512-image-token mean the unpooled experiment scored |
| 1f | SimLingo query site | tag L66 "`dq`, driving queries at layer 10" | `read.sh:128` `--site driving_queries --layer 10` (`capture_agent.py:181`, the last `driving_tokens` positions) | match | — |
| 1g | TF++ sites | tag L67 `vision_bridge`, "decoder join tokens"; main L29–30 last layer | `read.sh:129` `vision_bridge`; `read.sh:130` `driving_queries --layer-fraction 1`, i.e. the last layer of the last `join` call (`tfpp_agent.py:10`, `tfpp_unpooled.py:15`) | match | — |
| 1h | UniAD sites | tag L68 "last BEV encoder grid … track queries"; main L29–30 last layer | `read.sh:100-111`: the highest-numbered `bev_encoder.N` and `track_decoder.N` in `steps.pt` `layer_names`, used as the `all_tokens` layer index | unclear: needs UniAD's layer names to confirm that `track_decoder` holds the track queries and that the `all_tokens` axis is in `layer_names` order (not read, by rule) | changes the read if wrong |
| 1i | Window and m03 | tag L70–72 "12.5 s before the failure step, or the route's last 12.5 s … standardise, PCA 32 over all routes, Ward … A2 … top 10" | `read.sh:63` `cache_pool.py --window 50`; export stride 5 (`export_activations.py:202`) and 5 sim steps per frame on all three models (`transfer-spec.md:20-22`), so 50 × 5 × 0.05 s = 12.5 s; `cache_pool.py:36-41`; `cache_methods.py:116-117,171,177` | match. m03 also standardises the PCA output (`cache_methods.py:171`), which is the frozen m03 | — |
| 1j | Rivals and finalists per model | tag L51–52 "per model as in `transfer-spec.md`" | `read.sh:112-122` matches `heldout.sh:29-39` line for line. B7 is at round(10/23·(D−1)), k 18, seed 0, min support 20 (`read.sh:105,120-122`; `transfer-spec.md:56-60`). SimLingo's B3 comes from the A3 full-speed cache (`read.sh:144`, `heldout.sh:14-15`) | match | — |
| 2a | Rule units | tag L156–158 "at least 1.5× as often as their base twins, with at least 5 failing generalisation routes"; run inside each read | `ur.py:19,38-45` (`RATIO, MIN_FAILING = 1.5, 5`; slices are `pilot_slice`, twins come from `neighbourhood_of`; a zero twin rate passes). Run on this read's routes at `read.sh:134-136` | match | — |
| 2b | Primary units: no Wall, excluded by name | tag L12, L159 | `read.sh:137` `grep -v ':F2D_Wall$'`, used at `read.sh:166,170` | match | — |
| 2c | Named gaps | tag L160 "the named gaps" | UniAD: class `gap` under prereg-fail2drive §1, with ceiling excluded (`read.sh:80-87,96,138`; `prereg-fail2drive.md:30-36`). SimLingo and TF++ are hardcoded at `read.sh:140-141` (= `protocol.md:60`, `heldout.sh:43`) | match | — |
| 2d | Synonym list | tag L131–151, "case-insensitive, word stems" | `f2d-views-caption/agents.py:144-155` parses the table from the working-tree prereg at run time | match. It reads main, not the tag, so a later edit to the table would change flags silently | cosmetic |
| 3a | Primary metric | tag L161 "rank-averaged best match is primary; top-10 best match is secondary" | `vs.py:40-48` (mean over k = 1..M of the best Jaccard in the first k); top 10 via `sprint_score.best` (`vs.py:109`) | match | — |
| 3b | Budget M = 10, own order, A2 | `protocol.md:67-71`; A1/A2 | `sprint_score.py:31` `M = 10`; `distinct()` at `sprint_score.py:34-40` in each method's own order; B7 sorted by `rank` (`sprint_score.py:51`); m23/m40 dedupe at Jaccard 0.8 (`pool_axes.py:36`) | match | — |
| 3c | Weighted Jaccard; empty-empty is 0 | CLAUDE.md subtlety | `harness/bootstrap.py:31-35`; `harness/scoring.py:24` | match | — |
| 3d | Precision denominator | not used by this read | no precision in `vs.py` | n/a | — |
| 3e | Pooled = fixed mean over units | tag L162 | `vs.py:110`: a mean over every (model, gap) unit, equally weighted | match | — |
| 3f | Axes cut to the pool after A2 | — | `vs.py:98` intersects axes with the pool after `distinct()` and does not deduplicate again | match for this read, since every row is built on its own scored pool | cosmetic |
| 4a | Replicates | tag L162 "2,000 draws" | `vs.py:66` default 2000, not overridden in `read.sh:162` | match | — |
| 4b | Resampling unit, test mode | tag L162 "a pair bootstrap"; A1: the pair carries all its seeds | `vs.py:79,105,125-126` use the manifest `pair`. Test manifest `configs/rollout/f2d-test-simlingo.manifest.json`: 1,200 entries in 100 pairs `f2d-N`, each with 12 entries over 6 seeds (measured). UniAD uses the same ids and manifest (`f2d-test-uniad-s101.yaml:2,32`), and `read.sh:52` `setdefault` is a no-op there | match | — |
| 4c | Resampling unit, dev mode | same | `read.sh:52` sets pair to `base_id`. The screen manifest's `base_id` is `f2d-N` with no seed suffix (measured), so it lines up with the test pairs in the pooled dev call | match | — |
| 4d | Pairs joint across models | `vs.py:13` | one `pair_of` over every model (`vs.py:79,105`). Smoke run with two model names: 1,186 routes, 100 pairs | match | — |
| 4e | Guard against seed-suffixed pairs | A1 | none in `vs.py`. On H21b the unstripped manifest gives 299 "pairs", which narrows the intervals and flips m23 and m40 to "above B3-behaviour" (below) | no effect on the UniAD read (its manifest is correct) | cosmetic here; a real risk for any H21-style manifest |
| 4f | Seed | not stated | `vs.py:67` default 0 | match (prereg is silent) | — |
| 4g | Sidedness | tag L166 "95% interval … lies above 0" | `vs.py:52` 2.5th and 97.5th percentiles, two-sided; `p_one_sided` is reported beside it | match | — |
| 4h | A unit with no drawn pair | — | `weighted_jaccard` returns 0 for every row on that draw (`bootstrap.py:33-34`), so the unit is not dropped | unclear, but it is paired across rows | cosmetic |
| 5a | Row above the fleet | tag L166 | `vs.py:135-138` `vs_primary` per row, both metrics; `read.sh:162` `--primary-rival B3_behaviour` | match | — |
| 5b | Row A above row B; partial order | tag L167–168 "only if the paired interval of A minus B lies above 0 … the partial order these intervals give" | `vs.py` computes contrasts only against the primary rival (`vs.py:135-138`) and saves no draws, so no A − B interval exists for other pairs | mismatch | changes the read: the ranking the headline promises cannot be built from the output |
| 5c | Selection adjustment | tag L169 "wherever a 'best of the new views' is quoted, it is re-selected in every draw" | `vs.py:139-156` supports `--select`, but `read.sh:159-172` passes none; the dry run prints `{}` | mismatch | changes the read if a best view is quoted from this output |
| 6a | Interim label | tag L176 "labelled interim" | `read.sh:36` TAG has "$READ read … (blind)"; output folder `uniad-test-$READ-<time>` | match. The label goes to the JSON, not to stdout | cosmetic |
| 6b | Coverage: routes, pairs, failing per unit | tag L176 | `read.sh:88-95` writes `coverage.json` (routes, twin pairs per seed, by seed, jobs); `vs.py:162` prints units (failing per unit), routes and pairs; `read.sh:174-175` prints them | match | — |
| 6c | Interim uses every driven route | tag L175, L24 | `score_routes.py` keeps the first valid attempt of every manifest id (`route_run.py:70-75`), but only over the hardcoded `JOBS` (`read.sh:35`) | unclear: a rerun job submitted after `dac5035` is left out unless `JOBS` is overridden | changes coverage, not the method |
| 6d | What the read prints | tag L166–170 | `read.sh:175` tails the logs, which carry only point scores (`vs.py:163-165`). The `vs_primary` intervals, which the decision rule needs, are only in `$O/*.json` | mismatch | cosmetic (the data exist) |
| 6e | Try count reported | tag L170 "the full try count … reported whatever the result" | not printed or written by `read.sh` or `vs.py` | mismatch | cosmetic |
| 6f | Caption coverage stated on its own | tag L45–46, L122–128 | `uniad_frames.py:58,70` lists routes without frames; it covers failing routes only (`:50`) | match | — |
| 6g | Caption frames | tag L84–88; main L32 | `uniad_frames.py:27,31-34,65,67`: 4 frames, every 4th JPEG (1 s), at or before the failure step, 640 px, native width recorded; mapping kept outside the frames tree (`:44`) | match | — |
| 6h | Caption salt | tag L100 "a new salt" | `read.sh:68-69`: one salt file shared by dev and test (ids are disjoint) | match in effect | cosmetic |
| 7a | Tag gate | tag L4, L184–186 | `read.sh:32` checks only that the tag exists. It does not check that HEAD descends from the tag or that the prereg is unchanged. `read.sh` itself was first committed after the tag (`dac5035` 13:27:55 against tag commit `69668f5` 13:24:50, then `f14b40d`, `7d89d1c`, `3ef2629`), so the code is not frozen by the tag. `read.sh:40` records HEAD | match to the prereg's wording, which fixes rows rather than code | cosmetic; pinning a code tag would close it |
| 7b | Outcome reads before the gate | tag L4 | nothing before `read.sh:32` reads data. Dev mode reads the seed-24 screen only, because its config's manifest ids are disjoint from the test ids (measured, 0 overlap), so a `JOBS` override cannot pull test routes in (`route_run.py:70-75`) | match | — |
| 7c | Failures in background scoring | — | `read.sh:163` runs `vs.py` in the background, and `wait` (`:173`) does not propagate a failure; it shows only in the log | cosmetic | cosmetic |

## Real mismatches

1. **No pairwise contrasts.** The decision rule ranks row A above row B only on the A − B paired interval
   (tag L167–168). `view_score.py:135-138` computes only row − B3-behaviour and saves no draws. The partial order
   cannot be built from the read's output. Changes the read.
2. **No selection adjustment.** Tag L169 requires a best-of-new-views to be re-selected in every draw.
   `uniad_read.sh:159-172` passes no `--select`, although `view_score.py:139-156` supports it. Changes the read if a
   best view is quoted.
3. **The caption row is outside the one command.** Tag L57 and L127 make `caption` a ranked new view, with the other
   rows rescored on its routes. `uniad_read.sh` only exports frames (`:68-71`). Scoring is a later manual step
   (`f2d-views-caption/protocol.md:60-67`), so the Saturday read is incomplete as a ranking. Changes the read.
4. **SimLingo `img-mean` is the whole-sequence layer-10 mean, not the 512 image tokens.** Compare
   `uniad_read.sh:126` and `capture_agent.py:180` with tag L55 and L66 and `protocol.md:27`. The prereg's tag L44
   ("per-step layer means that every route logs") supports the code, so this is a contradiction inside the prereg
   that someone has to rule on. It affects the pooled headline only.
5. **`SIMLINGO_IMG=vit` can put `vit-mean` into the ranking under the name `img-mean`.** This breaks tag L58–62, and
   the cached file at `uniad_read.sh:127` makes the choice sticky across reads. It is latent: the default is
   correct, but check that `results/savio/f2d-views/simlingo/img-mean.json` was built with `llm10` (its `settings`
   field records `site` and `layer`).
6. **The decision-relevant intervals are not printed** (`uniad_read.sh:175` and `view_score.py:163-165`), and **the
   try count is not reported** (tag L170). Both are cosmetic.

## Dry run (dev data only: H21b SimLingo seeds 24–26, never evidence)

Inputs: `results/h21/h21b/{manifest.json, routes.jsonl, axes/*.json}`. The `-sNN` suffix was stripped from `pair`
into `manifest-pairfix.json`, which gives 100 pairs.

| Stage | Runs | What it printed (measured) |
|---|---|---|
| `units_rule.py … --model simlingo` | yes, exit 0 | 7 rule units: Animals 12/29 failing (twins 5/30), BadParking 12/30, CustomObstacles 28/30, FullyBlocked 11/15, PedestriansOnRoad 9/15, RightConstruction 8/15, Wall 14/14 (twins 0/15). Full lines in `units-h21b.txt` |
| class heredoc (`read.sh:72-97`, coverage part dropped) | yes | the only named gap is CustomObstacles. Wall is "background" because it has 14 slice runs, under §9.1's 30 (`classes-h21b.txt`) |
| `view_score.py`, rule units without Wall | yes, 12 s | 593 routes, 100 pairs, 174 failing. Rank-averaged best match: B3-behaviour 0.133; B3-infraction 0.214, Δ +0.081 [+0.036, +0.121]; m23 0.190, Δ +0.057 [−0.004, +0.135]; m40 0.168, Δ +0.035 [−0.002, +0.102]; j09 0.133, Δ +0.000 [−0.039, +0.059] |
| `view_score.py`, all rule units | yes, 13 s | B3-behaviour 0.129; m23 0.213, Δ +0.084 [+0.023, +0.157]; m40 0.186, Δ +0.057 [+0.011, +0.127]; j09 0.150, Δ +0.021 [−0.015, +0.080]; B3-infraction 0.210 |
| `view_score.py`, named | yes, 4 s | one unit (CustomObstacles, 28): B3-behaviour 0.178; m23 0.189, Δ +0.011 [−0.024, +0.039]; m40 0.169; j09 0.186; B3-infraction 0.357 |
| `view_score.py`, pooled path (two model names over the same pool) | yes | 1,186 routes, 100 pairs; m23 Δ +0.057 [−0.004, +0.135], identical to the single-model run, so pairs are resampled jointly |
| control: unstripped manifest, rule units without Wall | yes | 299 "pairs". Same point scores, narrower intervals: m23 Δ +0.057 [+0.010, +0.104], m40 [+0.007, +0.079], so both wrongly clear B3-behaviour |

Every `view_score.py` run printed `selections` as `{}` (no `--select`). Under zsh the unquoted `$U`/`$ROWS` lists do
not split, so the stages must run under bash, as `uniad_read.sh` does. The dry run did not cover stages 1–3 (merge,
shards, cache, row building): they need Savio job folders.

## Unverified

- That UniAD's `track_decoder.N` output is the track queries, and that its `all_tokens` layer axis follows
  `layer_names` order (item 1h). This needs `adapters/uniad/`, which was not read.
- That `$REF/f2d-dev/round2/simlingo/cache-w50.npz` and `$REF/f2d-heldout/tfpp/cache-w50.npz` cover the same routes
  as `$REF/f2d-test-{simlingo,tfpp}/routes.jsonl`. They live on Savio.
- That the `JOBS` list at `uniad_read.sh:35` is complete for Saturday.
- `python -m pytest -q`: 806 passed, 24 failed, 43 skipped. The failures are in `test_submit.py`,
  `test_savio_runtime.py`, `test_slow_watchdog.py` and `test_j10_hmmfisher.py` (no hmmlearn here). This audit
  changed no code. `scripts/check_sealed_imports.py`: clean.

## Commands

The exact commands are in `dryrun.sh` (the four `view_score.py` runs and the pooled smoke). Before it:

```bash
# pair fix: strip -sNN from pair into manifest-pairfix.json (inline python: re.sub(r"-s\d+$", "", pair))
PYTHONPATH=src /opt/miniconda3/bin/python docs/research/experiments/f2d-unpooled/units_rule.py \
  results/h21/audit-20261119-185008-11421/manifest-pairfix.json results/h21/h21b/routes.jsonl --model simlingo
# class heredoc of uniad_read.sh:72-97 (named part only) on the same manifest and routes -> classes-h21b.txt
bash results/h21/audit-20261119-185008-11421/dryrun.sh
PYTHONPATH=src /opt/miniconda3/bin/python -m pytest -q
PYTHONPATH=src /opt/miniconda3/bin/python scripts/check_sealed_imports.py
```
