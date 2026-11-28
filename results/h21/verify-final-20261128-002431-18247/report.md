# Verifier A: final UniAD read in `docs/research/comparison-table.md`

Commit checked: `5786614` (branch base). Rules: `docs/prereg-views.md`, including the record after the tag (N1: each
model's median over its own runs, then the fixed mean over units; N2: a row ranks above the fleet only from its own
interval). No raw UniAD data exists in this clone, and none was looked for. `gaps/sealed/` was not read. No doc or
table was edited.

Summary: 1 fail in the reading (line 38), 2 presentation fails (line 30 sign label; pooled columns on two route
sets), 1 latent pre-existing code defect (`units_rule.py:44` at exactly 1.5x). Every bold cell is correct (42 of 42).
The units stated in the table follow from the stated counts under the rule. The `--restrict` fix, N1, reported-only
rows and the final-read cutoff refusal behave as the prereg says, and each now has a test that fails when the
behaviour is reverted.

Marks: **pass**, **fail**, **cannot-check** (cannot-check-from-main), **nit** (no wrong number; wording or a latent
risk).

## (a) Bold cells and ranking sentences of "Final UniAD read"

Notation: Δ = row minus B3-behaviour, rank-averaged best match. "U" = UniAD alone, "P" = pooled.

| # | Claim (comparison-table.md line) | Check | Mark |
|---|---|---|---|
| a1 | 42 cells, lines 12-18: bold exactly where the 95% interval lies above 0 | Parsed every cell. In all 42, bold matches lower bound > 0, and the point lies inside its interval. Bold cells: caption in all 6 columns, m23 and m40 in P all-rule, B3-infraction in U primary, U all-rule, U named, P primary and P all-rule. B3-infraction P named (+0.031 [−0.001, 0.078]) is correctly not bold. | pass |
| a2 | Line 19, B3-behaviour scores 0.029 / 0.042 / 0.052 (U) | The mean of the per-unit B3 values on line 37 (0.04, 0.02, 0.07 for Ped, RightConstr, Wall) is 0.030 (2 primary units), 0.043 (3 rule units) and 0.055 (Ped + Wall). These match within the 2-decimal rounding. | pass |
| a3 | Lines 27-28: caption ranks above the fleet on UniAD (primary +0.048 [0.010, 0.114], all rule +0.059, named +0.083) and pooled (+0.065 [0.030, 0.095]) | All four use the caption row's own interval against B3-behaviour, and every lower bound is > 0 (0.010, 0.026, 0.031, 0.030). This complies with N2. | pass |
| a4 | Line 28-29: pooled primary, caption ranks above `query-mean` (`query-mean` − caption −0.055 [−0.096, −0.003]) | The upper bound is < 0, so caption ranks above `query-mean`. The point is consistent with the column: 0.065 − 0.010 = 0.055. The pooled activation cells come from a different route set (see a17), so this match holds only approximately. | pass |
| a5 | Line 28-29: pooled primary, caption ranks above "every other row", incl. m23 | The pairwise intervals for caption − m23, − m40, − `img-mean`, − B3-infraction and − B7-pool are not in the table or anywhere on main. | cannot-check |
| a6 | Line 29-30: on UniAD alone caption ties `query-mean` (+0.001 [−0.082, 0.082]) | The tie holds because the interval spans 0. | pass |
| a7 | Line 30: the sign of "+0.001" | The sentence is about caption, but the number is `query-mean` − caption. As caption − `query-mean`, the point must be 0.048 − 0.049, which lies in (−0.002, 0.000) for any unrounded values. Line 29 labels its contrast "the other way", but line 30 has no label. | fail (label) |
| a8 | Line 30: caption ties `img-mean` on UniAD alone | No caption − `img-mean` interval is stated. The point is 0.048 − 0.040 = +0.008. | cannot-check |
| a9 | Line 30: caption per unit 0.11 / 0.03 / 0.15 (Ped / RightConstr / Wall) | These are consistent with the columns. Primary (0.11+0.03)/2 = 0.070 vs 0.029+0.048 = 0.077. All rule 0.097 vs 0.101. Named 0.130 vs 0.135. Exact values cannot be recomputed, because per-unit numbers of a multi-run row come from its lower-middle run (`view_score.py:128-131`). | pass (consistency) |
| a10 | Lines 31-32: UniAD primary, best new view re-selected per draw: caption 51%, `img-mean` 31%, `query-mean` 17%; +0.049 [0.014, 0.165] | The shares sum to 99%, which is rounding. The point +0.049 equals `query-mean`'s, and `query-mean` is the point choice (0.078 > caption 0.077 > `img-mean` 0.069). The interval lies on or above every member's own interval, as the max over members must in every draw: caption [0.010, 0.114], `query-mean` [−0.006, 0.138], `img-mean` [−0.019, 0.160]. | pass |
| a11 | Line 32: pooled primary, caption 98%, +0.065 [0.032, 0.095] | The point equals caption's +0.065, and the interval dominates caption's own [0.030, 0.095]. | pass |
| a12 | Line 33: "On the blind model, no activation view ranks above the fleet's behaviour signal" | `query-mean`, `img-mean`, m23, m40 and B7-pool all have a lower bound ≤ 0 in all three UniAD columns. Also, m23's U primary interval [−0.025, −0.002] lies wholly below 0, so m23 ranks below behaviour there. The section does not say this, but STATUS and the journal ("tie or lose") cover it. | pass |
| a13 | Lines 33-34: selection without caption (`query-mean` 59%), +0.049 [−0.003, 0.163], a tie | The point equals `query-mean`'s. The interval dominates both members' own intervals, and it is dominated by the with-caption selection (−0.003 ≤ 0.014, 0.163 ≤ 0.165). It spans 0, so it is a tie. | pass |
| a14 | Line 34: "It does rank above m23 (+0.058 [0.008, 0.173])" | The point is 0.049 − (−0.009) = 0.058 and the lower bound is > 0. Under the selection rule, this is a valid quote of the re-selected best new view. The risk is that "It" reads as `query-mean`. The selection interval is, draw by draw, ≥ `query-mean` − m23, so it does not establish that the `query-mean` row ranks above m23 (N2: a row's ranking comes only from its own interval). That row interval is not on main. | pass (selection); nit (wording) |
| a15 | Lines 35-36: the interim UniAD lead did not hold; PedestriansOnRoad 0.42 (14 failing routes) → 0.07 with 16 | Interim `query-mean` +0.169 [0.047, 0.206] (line 56) is above 0. Final +0.049 [−0.006, 0.138] spans 0. 0.42 and 14 match lines 97 and 105. 16 matches the 16/30 count. | pass |
| a16 | Line 37: per-unit final scores, `query-mean` 0.07/0.09/0.05, `img-mean` 0.03/0.11/0.05, B3 0.04/0.02/0.07 | Unit means against the columns: `query-mean` 0.080 / 0.070 / 0.060 vs 0.078 / 0.067 / 0.058, and `img-mean` 0.070 / 0.063 / 0.040 vs 0.069 / 0.062 / 0.037 (primary / all rule / named). All match within rounding. | pass (consistency) |
| a17 | Line 38: "The only row above behaviour everywhere on UniAD is B3-infraction" | False as written. The caption row is also above behaviour in all three UniAD columns (line 12: [0.010, 0.114], [0.026, 0.114], [0.031, 0.163]). It probably means "the only row besides caption". | **fail** |
| a18 | Line 39: m23/m40 lead only when Wall is in (pooled all-rule), "as on dev and TF++" | m23 and m40 are bold only in P all-rule, so "only when Wall is in" holds (UniAD all-rule also has Wall and they do not lead there, which this one-way claim allows). TF++ all-rule m23 +0.082 [0.038, 0.116] and m40 +0.064 [0.025, 0.083] are bold, and TF++ primary is not (lines 58-59, 86-87). "Dev" is not in this table. The nearest column, SimLingo all-rule, has m23 bold but m40 not (+0.060 [−0.019, 0.142]). "Lead" is loose: in P all-rule, caption (+0.066) is higher than both. | pass (TF++); cannot-check (dev) |
| a19 | Line 5: 1,198 of 1,200 routes, 598 of 600 twin pairs, 10301059 and 10501067 missing | In the test manifest, both ids are slices of different base routes (RightOfWay s103 and PedestrianCrowd s105). So 2 pairs are incomplete, which gives 598. 837 failing cannot be checked. | pass (arithmetic); cannot-check (837) |
| a20 | Line 8: the named class is PedestriansOnRoad + Wall | It comes from `harness.efficacy` in `uniad_read.sh:89-114` (`classes.txt`, on Savio). For Wall to be "gap" and not "ceiling", UniAD's Wall cannot have slice fail rate ≥ 0.95 together with twin fail rate ≤ 0.20. Its counts are not stated. | cannot-check |
| a21 | Prereg "Coverage": "the other rows and rivals are rescored on the same routes beside it" (applied to the pooled columns, lines 12-19 and 23-24) | Lines 23-24 say the pooled caption files use TF++'s reproduced-pair routes, and the pooled activation cells come from the full TF++ pool. So each pooled column mixes two route sets. The caption cell's baseline is not the B3-behaviour 0.092 printed beneath it. Each contrast is paired within its own file, so no interval is wrong, but the column is not on one route set. The final section also does not state the pooled caption coverage (TF++ 172 of 257 reproduced pairs is only in the interim footnote, line 68). The UniAD columns are unaffected (837 of 837 failing routes have frames). | fail (presentation) |
| a22 | Prereg "Reporting": each model alone, the full try count and the coverage, whatever the result | UniAD alone and its coverage are in the final section. The 219 tries (line 111) and SimLingo/TF++ alone are in the interim part of the same document. | pass |

## (b) Unit-admission rule

The rule (prereg "Units"; `units_rule.py:19, 44`): admit a type if it has ≥ 5 failing generalisation routes and either
its twins never fail or slice rate ≥ 1.5 × twin rate. Wall is then removed by name for the primary set
(`uniad_read.sh:159`, `nowall`).

| # | Claim | Check | Mark |
|---|---|---|---|
| b1 | PedestriansOnRoad 16/30 vs 0/30 admitted | 16 ≥ 5 and the twins never fail (the `rt == 0` branch), so it is admitted. The printed ratio is null. Tested. | pass |
| b2 | RightConstruction 11/30 vs 6/30 admitted | 0.367 ≥ 1.5 × 0.200 = 0.300 (ratio 1.83), and 11 ≥ 5, so it is admitted. Tested. | pass |
| b3 | FullyBlocked 30/30 vs 21/30 out, "ratio 1.43 < 1.5" | 1.000 / 0.700 = 1.4286, which prints as 1.43 and is not admitted. Tested. | pass |
| b4 | Wall admitted | UniAD's Wall counts are not stated anywhere on main. | cannot-check |
| b5 | No other type admitted, so primary = 2 units and all rule = 3 | `units-uniad.txt` is on Savio. Indirect evidence: every all-rule score equals the mean of exactly the three listed per-unit values (a2, a9, a16), so the numbers are consistent with 3 rule units. | cannot-check (consistent) |
| b6 | The denominators are 30 | `configs/rollout/f2d-test-simlingo.manifest.json` has 30 slices and 30 twins for each of PedestriansOnRoad, RightConstruction, FullyBlocked and Wall. The two missing routes are in other types (a19). The ids that the table gives for UniAD are in this manifest, so the inference is that UniAD was scored on it. The UniAD config was not read. | pass (inferred) |
| b7 | The code matches the prereg text | It matches in every case except the 1.5x boundary. `rs >= RATIO * rt` in floating point rejects some types that fail exactly 1.5x as often: with 30-route denominators it fails at 9/30 vs 6/30 and 18/30 vs 12/30 (checked; it passes at 6/4, 12/8, 15/10, 21/14, 24/16, 27/18, 30/20). The prereg says "at least 1.5x". This defect is pre-existing and latent. It does not affect the three stated counts. Whether any UniAD type sat exactly on the boundary cannot be checked. The test is pinned as a strict xfail. | **fail** (pre-existing, `units_rule.py:44`) |
| b8 | The rule runs inside each read, on that read's routes | `uniad_read.sh:156` runs it on the merged `$R` of this read. The caption restriction does not change the units. For UniAD this has no effect (all failing routes have frames). For pooled TF++, the units come from the full TF++ pool and the scoring uses reproduced-pair routes, which the prereg allows (units are fixed per read). | pass |
| b9 | The SimLingo rule units in the pooled columns | Rerun from `results/savio/f2d-test-simlingo/routes.jsonl`: 8 rule units, 7 without Wall (BadParking, CustomObstacles, FullyBlocked, PedestrianCrowd, PedestrianOtherBlocker, PedestriansOnRoad, RightConstruction). This matches "Units 7" (line 65) and line 102. TF++ test routes are not in this clone. | pass (SimLingo); cannot-check (TF++) |

## (c) Code audit at 5786614 against the prereg

| # | Item | Check | Mark |
|---|---|---|---|
| c1 | `--restrict` fix, 47f26b4 (`view_score.py:62`, `action="extend"`) | Repeated flags now accumulate. The pooled call in `uniad_caption.sh:50` passes two of them (TF++, then UniAD). New test: A and B each restricted, and both shrink (failing 5 and 7, units 4 and 6). With the fix reverted, the test fails (checked). Whether caption job 41948480 ran at a commit that contains 47f26b4 cannot be checked: `caption/commit.txt` is on Savio. The dates fit (fix 2026-11-22 07:26, final read folder 2026-11-22 17:44). | pass; cannot-check (job commit) |
| c2 | N1 (`view_score.py:117-126`) | Each model's median is taken over its own runs of the mean over its units. These medians are weighted by unit count and divided by the total number of units, which is the fixed mean over units. New test: model A runs score 1, 1, 0 and model B runs score 1, 0, 1, so the row scores 1.0, where pairing run r across models would give 0.5. The bootstrap interval is [1, 1]. Replacing the scorer with a run-paired median makes the test fail (checked). Every model must have the same run count (`:103-105`). | pass |
| c3 | Per-unit numbers of a multi-run row (`view_score.py:128-131`) | The lower-middle run is picked by `score1`, which pairs run r across models. In pooled reports, per-unit caption numbers therefore come from a pairing that N1 says has no meaning. This affects reporting only (the JSON note says so), and no pooled per-unit number is quoted in the final section. | nit |
| c4 | Reported-only rows (`view_score.py:156-160`) | They are left out of `ranks_above`, both as the ranking row and as the row ranked. They are still scored, with `vs_primary` and `pairwise`. They are not in any `--select`. New test; removing the filter makes it fail (checked). Latent risk: the names are not validated, so a typo in `--reported-only` would rank the row without any error. Both scripts pass these names to UniAD-alone runs where the rows do not exist, which is harmless. | pass; nit |
| c5 | Cutoff refused on a final read (`uniad_read.sh:21`) | The guard runs before anything else, and its `&&` list exits 2 under `set -e` only when READ=final and CUTOFF is non-empty. New test: `test final` with CUTOFF exits 2 with the message and creates no files. `final` without CUTOFF, `final` with an empty CUTOFF, and `interim` with CUTOFF all pass the guard and stop at the mode check. An empty CUTOFF also skips the filter (`:51`), which is consistent. `uniad_caption.sh` takes the read's routes from `score.env` and has no cutoff path. | pass |
| c6 | Best new view re-selected in every draw (`view_score.py:161-178`) | The member is picked by argmax per draw, the contrasts are on the same draws, and the quoted point is the argmax at the point estimate. `uniad_caption.sh:34` includes caption among `img-mean` and `query-mean`. New test: the selection's interval is at or above every member's own interval, and its point equals the point choice's own Δ. This is the property used in a10, a11 and a13. | pass |
| c7 | Partial order: A above B only from the paired A − B interval | Covered by the existing `tests/test_view_score_order.py` and `tests/test_view_score.py`. | pass |
| c8 | Caption coverage and rescoring (`uniad_caption.sh:22-56`) | UniAD keeps every passing route and every failing route that has frames. Every row is rescored with the caption row on those routes. SimLingo is unrestricted (every route has frames). TF++ is restricted to reproduced-pair routes. This matches the prereg "Coverage". | pass |
| c9 | Pair bootstrap unit | In the test manifest, `pair` is `f2d-N` with no seed suffix: 100 pairs of 12 routes (6 seeds × slice + twin). So a base pair is resampled across seeds and models together (`view_score.py:82`, one shared manifest). The H21 seed-suffix defect is absent here. | pass |
| c10 | A failed scoring job stops the script | `wait $p` under `set -e` stops the script on the first failed job (`uniad_read.sh:211`, `uniad_caption.sh:57`). | pass |
| c11 | Last layer at UniAD sites (record after the tag), and m03 on the window mean | `uniad_read.sh:117-129` takes the highest `bev_encoder.*` and `track_decoder.*` index and runs m03. The claim that 50 frames are 12.5 s (5 steps per frame) rests on the script's comment and cannot be checked without data. | pass; cannot-check (frame rate) |

## Tests added

`tests/test_final_read_rules.py` has 8 tests: 7 pass and 1 is a strict xfail (b7). Each test of `view_score.py` was
checked by reverting the behaviour it pins (the restrict fix, N1 and the reported-only filter): each such test fails.
Afterwards the file was restored with `git checkout`.

## Measured, and unverified

- Measured here: the 42-cell parse (a1); the unit-rule outcomes at the stated counts (b1-b3); the float boundary
  (b7); the SimLingo rule units from local data (b9); the test-manifest structure (a19, b6, c9).
- Unverified (cannot be checked from main): every number in the final section as such (`uniad-test-final-*` and
  `caption/` JSONs are on Savio); 837 failing; Wall's counts and the named class; whether any other type was
  admitted; the pairwise intervals behind a5, a8 and a14's row reading; the commit that job 41948480 ran.

## Commands

```bash
cd /Users/yanzihao/autoresearch-local/wt/20261128-002431-18247
git log --oneline | head -20; git show 47f26b4
cat -n docs/prereg-views.md docs/research/comparison-table.md
cat -n docs/research/experiments/f2d-unpooled/{view_score.py,units_rule.py,uniad_read.sh,uniad_caption.sh,table.sh}
# manifest structure, missing ids, per-type denominators (inline python over configs/rollout/f2d-test-simlingo.manifest.json)
PYTHONPATH=src /opt/miniconda3/bin/python docs/research/experiments/f2d-unpooled/units_rule.py \
  configs/rollout/f2d-test-simlingo.manifest.json results/savio/f2d-test-simlingo/routes.jsonl --model simlingo
/opt/miniconda3/bin/python -c "for t in range(1,31):
  for s in range(5,31):
    if 2*s==3*t: print(s, t, s/30 >= 1.5*(t/30))"
# 42-cell bold/interval parse of comparison-table.md lines 12-18 (inline python)
PYTHONPATH=src /opt/miniconda3/bin/python -m pytest -q tests/test_final_read_rules.py tests/test_view_score.py tests/test_view_score_order.py
# mutation checks: revert action="extend"; replace score() by a run-paired median; drop the reported-only filter;
# run the matching test each time, then git checkout the file
PYTHONPATH=src /opt/miniconda3/bin/python -m pytest -q
/opt/miniconda3/bin/python scripts/check_sealed_imports.py
```
