# Verifier B: final UniAD comparison table

Checked at commit 5786614 (main as cloned), 2026-11-28. Sources: `docs/research/comparison-table.md` ("Final UniAD
read", lines 3–39), `docs/prereg-views.md` (decision rule L197–203; record after the tag L28–60), the second
re-audit `results/h21/reaudit-20261122-050754-8303/report.md` (its N1 and N2), and the scripts in
`docs/research/experiments/f2d-unpooled/`. No raw UniAD data exists in this clone, and none was looked for;
`gaps/sealed/` was not read.

Rule used for (a). A cell is bold only if its interval vs B3-behaviour lies above 0 (prereg L199). Row A ranks
above row B only if the paired A − B interval lies above 0 (L200). A row ranks above anything only from its own
interval. The best new view re-selected per draw is not a row: it is reported beside the rows, and no rank claim
comes from it (prereg L59–60; re-audit N2).

## Summary

- **2 fails** in the table text:
  - L38 says B3-infraction is the only row above behaviour everywhere on UniAD. The caption row is too.
  - L34 makes a rank claim ("It does rank above m23") from a selection interval. N2 forbids that.
- **1 latent code bug:** `units_rule.py:44` drops a type that fails exactly 1.5× as often as its twins (for example
  9/30 vs 6/30). It does not change the three stated counts. Whether any other UniAD type sits exactly at 1.5×
  cannot be checked from main.
- Every bold cell matches its interval, and the stated unit counts give the stated units.
- The --restrict fix, the per-model median (N1), the reported-only exclusion and the cutoff refusal all behave as
  the prereg says. New tests pin each one.

## (a) Bold cells and ranking sentences

| # | Claim (table line) | Verdict | Evidence |
|---|---|---|---|
| a1 | caption bold in all 6 columns (L12) | pass | lower ends 0.010, 0.026, 0.031, 0.030, 0.033, 0.040 are all > 0 |
| a2 | `query-mean` bold nowhere (L13) | pass | lower ends −0.006, −0.011, −0.012, −0.019, −0.025, −0.026 |
| a3 | `img-mean` bold nowhere (L14) | pass | lower ends −0.019, −0.020, −0.027, −0.026, −0.030, −0.026 |
| a4 | m23 bold only pooled all rule (L15) | pass | +0.049 [0.017, 0.080]; others' lower ends are < 0. UniAD primary −0.009 [−0.025, −0.002] lies wholly below 0, so m23 ranks below behaviour there. The text does not say this |
| a5 | m40 bold only pooled all rule (L16) | pass | +0.048 [0.009, 0.083]; others' lower ends are < 0 |
| a6 | B3-infraction bold in 5 columns, not pooled named (L17) | pass | lower ends 0.002, 0.004, 0.004, 0.005, 0.005; pooled named [−0.001, 0.078] |
| a7 | B7-pool bold nowhere (L18) | pass | no lower end > 0. UniAD all rule, UniAD named, pooled primary and pooled all rule lie wholly below 0 |
| a8 | each point estimate sits inside its interval (L12–18) | pass | all 42 cells |
| a9 | caption ranks above the fleet on UniAD (primary, all rule, named) and pooled (L27–28) | pass | from its own intervals (a1) |
| a10 | pooled primary: caption ranks above `query-mean`, −0.055 [−0.096, −0.003] "the other way" (L28–29) | pass | the upper end is < 0, so caption − `query-mean` lies above 0. The point agrees with the table: 0.010 − 0.065 = −0.055 |
| a11 | pooled primary: caption ranks above m23 and "every other row" (L28–29) | cannot-check-from-main | the paired intervals of caption vs `img-mean`, m23, m40, B3-infraction and B7 are not in the table, and the caption JSON is on Savio only. The point differences are +0.070, +0.063, +0.065, +0.042 and +0.107, but a paired interval cannot be rebuilt from two marginal intervals |
| a12 | UniAD primary: caption ties `query-mean`, +0.001 [−0.082, 0.082] (L29–30) | pass (tie); nit on sign | the interval spans 0, so it is a tie. The number is `query-mean` − caption, not caption − `query-mean`. From the cells, caption − `query-mean` is in (−0.002, 0.000), because 0.048 ∈ [0.0475, 0.0485) and 0.049 ∈ [0.0485, 0.0495). So it cannot round to +0.001. The `view_score` key is `query-mean - caption`, because `uniad_caption.sh:44` adds caption last. The direction is unlabelled, while the pooled number in the same sentence is labelled "the other way" |
| a13 | UniAD primary: caption ties `img-mean` (L30) | cannot-check-from-main | the paired interval is not given; the point difference is +0.008 |
| a14 | per unit, caption 0.11 / 0.03 / 0.15 (L30) | pass (consistency) | these come from the lower-middle run, so they need not average to the score (`view_score.py:128-131`). The means 0.07, 0.097 and 0.13 sit near the scores 0.077, 0.101 and 0.135 |
| a15 | best new view per draw, UniAD primary: caption 51%, `img-mean` 31%, `query-mean` 17%; +0.049 [0.014, 0.165] (L31–32) | pass (consistency); no rank claim made | the shares sum to 99% (rounding). The point +0.049 is `query-mean`'s, because at the point estimate `query-mean` (0.078) > caption (0.077) > `img-mean` (0.069). Note: the lower end 0.014 > 0 comes only from the per-draw maximum; `query-mean`'s own interval spans 0. This is re-audit N2's case, and the text correctly makes no claim from it |
| a16 | pooled primary: caption 98%, +0.065 [0.032, 0.095] (L32) | pass (consistency) | caption is the point choice: 0.065 > 0.010 > −0.005 |
| a17 | no activation view ranks above behaviour on UniAD (L33) | pass | `query-mean`, `img-mean`, m23, m40 and B7 have no UniAD lower end > 0 (a2–a5, a7) |
| a18 | best new view without caption, `query-mean` 59%: +0.049 [−0.003, 0.163], "a tie" (L33–34) | pass | the interval spans 0. The point equals `query-mean`'s cell |
| a19 | **"It does rank above m23 (+0.058 [0.008, 0.173])"** (L34) | **fail** | `comparison-table.md:34`. "It" is the best new view re-selected per draw, which is a selection, not a row. N2 (prereg L59–60) says a rank claim comes only from a row's own interval. The +0.058 is `query-mean` − m23 at the point: 0.078 − 0.020. `query-mean`'s own paired interval vs m23 is not on main, so the claim cannot be repaired from main. Write "the best new view re-selected per draw is +0.058 [0.008, 0.173] above m23" without "ranks above", or quote `query-mean − m23` from its own paired interval |
| a20 | the interim lead did not hold: `query-mean` vs B3 went from +0.169 [0.047, 0.206] (bold) to +0.049 [−0.006, 0.138]; Ped 0.42 → 0.07 (L35–36) | pass | matches the interim table (L56, L97) and the final cells |
| a21 | per-unit final scores of `query-mean`, `img-mean`, B3-behaviour (L36–37) | pass (consistency) | single-run rows, so the unit means must match the scores. B3: (0.04+0.02)/2 = 0.03 vs 0.029; three-unit mean 0.043 vs 0.042; Ped+Wall 0.055 vs 0.052. `query-mean`: 0.08 vs 0.078; 0.07 vs 0.067; 0.06 vs 0.058. `img-mean`: 0.07 vs 0.069; 0.063 vs 0.062; 0.04 vs 0.037. All agree within rounding |
| a22 | **"The only row above behaviour everywhere on UniAD is B3-infraction"** (L38) | **fail** | `comparison-table.md:38`. The caption row is also bold in all three UniAD columns: +0.048 [0.010, 0.114], +0.059 [0.026, 0.114] and +0.083 [0.031, 0.163] (L12). The bullet was written in 1557df8 when the caption row was still pending ("Reading (activation rows; caption pending)"). It was not updated when 5786614 added the caption row. "Only activation-free rival" or "the only row besides caption" would be true |
| a23 | m23/m40 "lead" only with Wall in, pooled all rule (L39) | pass on intervals; nit on wording | they are bold only in pooled all rule (a4, a5). "Lead" overstates this: caption is higher there (+0.066 vs +0.049 and +0.048), and the paired caption − m23 interval is not on main. "Rank above behaviour" is what the table shows. The "as on dev and TF++" part matches the interim TF++ all-rule cells (L86–87); dev is not in the table |
| a24 | pooled columns put caption (TF++ restricted to reproduced pairs) beside activation rows (all TF++ routes) (L23–24) | note | the text discloses it. But one pooled column then mixes two route sets, and the B3-behaviour score shown (0.092 / 0.100 / 0.088) is not the baseline of the caption cell. Prereg "Coverage" (L160) wants the other rows rescored on the caption row's routes beside it. The pairwise numbers in the text come from the caption files, which is correct. A reader comparing cells down a pooled column is comparing different route sets |

## (b) Unit-admission rule

`units_rule.py:44`: a type is a unit if `sum(s) >= 5 and (rt == 0 or rs >= 1.5 * rt)`. This matches prereg L189–191.

| # | Claim | Verdict | Evidence |
|---|---|---|---|
| b1 | PedestriansOnRoad 16/30 vs 0/30 is admitted | pass | the twin rate is 0, so only ≥ 5 failing is needed. Reproduced by `tests/test_units_rule.py` |
| b2 | RightConstruction 11/30 vs 6/30 is admitted | pass | ratio 0.367/0.200 = 1.83 ≥ 1.5, with 11 ≥ 5 failing. Reproduced |
| b3 | FullyBlocked 30/30 vs 21/30 drops out, ratio 1.43 | pass | 1.000/0.700 = 1.4286, printed as 1.43, which is < 1.5. Reproduced |
| b4 | the denominators are 30 | pass | the test manifest (`f2d-test-simlingo.manifest.json`, which the UniAD config uses) has 30 slices and 30 twins for each of the three types. The two missing routes are slice routes of other types: 10301059 is RightOfWay (seed 103) and 10501067 is PedestrianCrowd (seed 105). So no stated denominator should drop to 29 |
| b5 | Wall is admitted | cannot-check-from-main | Wall's UniAD counts are not stated. Wall has 30 slices and 30 twins in the manifest |
| b6 | no other type is admitted, so 3 rule units and 2 primary | cannot-check-from-main | the other 14 types' UniAD counts are not on main (`units-uniad.txt` is on Savio). The table is self-consistent: it gives three per-unit numbers per row |
| b7 | the named class is PedestriansOnRoad + Wall | cannot-check-from-main | named comes from `harness.efficacy` (`uniad_read.sh:97-103`), not `units_rule.py`. Wall being "gap" and not "ceiling" means its UniAD slice rate is < 0.95 or its twin rate is > 0.20; there is no file on main to check this |
| b8 | **an exact 1.5× ratio is admitted ("at least 1.5×", prereg L190)** | **fail (latent)** | `units_rule.py:44` compares floats. `9/30 >= 1.5 * (6/30)` is False, because 1.5 × 0.2 = 0.30000000000000004. Measured, the same happens for 18/30 vs 12/30, 9/60 vs 6/60, 18/60 vs 12/60, 36/60 vs 24/60 and 27/29 vs 18/29. The script prints `"ratio": 1.5, "unit": false`. The three stated types are not on the boundary. Other UniAD types: cannot-check-from-main. SimLingo's test pool has no type at exactly 1.5× (measured, below). The integer form `2 * fail_slice * n_twin >= 3 * fail_twin * n_slice` avoids the problem. Pinned by a strict xfail test |
| b9 | `units_rule.py` on SimLingo's test pool gives the interim table's 7 primary units | pass | measured on `results/savio/f2d-test-simlingo/routes.jsonl`: 8 rule units, including Wall, so 7 primary. This matches "Units 7" (L65) |

## (c) Code audit at 5786614 against `docs/prereg-views.md`

None of `view_score.py`, `uniad_read.sh`, `uniad_caption.sh`, `units_rule.py` or the prereg has changed since
47f26b4 (`git log 47f26b4^..HEAD`). The final read folder is stamped 2026-11-22 17:44, which is after 47f26b4
(07:26). The commit each job actually ran (`commit.txt`) is on Savio only.

| # | Behaviour | Verdict | Evidence |
|---|---|---|---|
| c1 | repeated `--restrict` adds (47f26b4) | pass; new test | `view_score.py:62` uses `nargs="*", action="extend"`. `uniad_caption.sh:50` passes `--restrict tfpp=…` and then `$U` with `--restrict uniad=…`, and both now apply. `test_repeated_restrict_applies_every_model` fails on 47f26b4^ and passes at HEAD |
| c2 | N1: each model's median over its own runs, then the fixed mean over units | pass; new test | `view_score.py:117-126` takes, per model, the median over runs of the unit mean, weights it by unit count and divides by all units. Every unit weighs equally, and run r is never paired across models. It runs inside every draw (L141). `test_pooled_runs_row_is_each_models_own_median` gives 1.0, where pairing would give 0.5. It fails on 3e19141^ |
| c3 | single-run rows are unchanged by N1 | pass | the median of one run is that run's unit mean (covered by the existing tests' values) |
| c4 | per-unit numbers of a multi-run pooled row | nit | `view_score.py:128-131` picks the lower-middle run by `score1`, which averages run r across models. So pooled per-unit numbers do pair runs across models. This affects reporting only, not scores or intervals. The UniAD-alone per-unit numbers quoted (L30) are not affected |
| c5 | reported-only rows are scored but stay out of the partial order | pass; new test | `view_score.py:156-160`: `ranks_above` drops them as keys and as values. `rows` and `pairwise` keep them. `test_reported_only_rows_are_scored_but_not_ranked` fails on 3e19141^. Both scripts pass `--reported-only img-mean-allseq query-mean-lastjoin` (`uniad_read.sh:190`, `uniad_caption.sh:39`) and leave them out of `--select`. Nit: a misspelt name is ignored silently. On the UniAD-alone calls the names refer to rows that are not passed, which is harmless |
| c6 | a final read refuses CUTOFF | pass; new test | `uniad_read.sh:21` exits 2 before any write. Under `set -e`, a false `[ "$READ" = final ]` inside the `&&` list does not stop an interim read. `test_final_read_refuses_a_cutoff` runs the script in an empty folder and sees exit 2 with nothing written. Nit: `READ` is matched exactly, so `Final` or `final2` with CUTOFF set would run a cut read |
| c7 | the bootstrap resamples Fail2Drive pairs, every model's routes in a pair together | pass | `view_score.py:82,137-139`. The test manifest's `pair` has no seed suffix: there are 100 distinct pairs, so the 6 seeds of a pair move together |
| c8 | paired row-vs-row intervals and `ranks_above` read both key orders | pass | `view_score.py:153-160`; already tested (`test_view_score_order.py`) |
| c9 | the best new view is re-selected per draw, with members limited to new views | pass | `uniad_caption.sh:34` uses `img-mean query-mean caption`. `uniad_read.sh:178` is named `best_new_without_caption` (re-audit N3, fixed) |
| c10 | caption coverage: every passing route plus every failing route with frames, every row rescored on them | pass | `uniad_caption.sh:22-33,43`. On the final read all 837 failing routes have frames, so the caption files score the same UniAD routes as the read files. The table says the same (L23) |
| c11 | the units rule runs on the read's routes | pass for UniAD; note for pooled caption | UniAD units are computed on the merged final routes (`uniad_read.sh:156`). The caption run reuses them (`score.env`), which is exact here because no failing route lacks frames. In the pooled caption run, TF++ is restricted to reproduced pairs (`uniad_caption.sh:50`), but TF++'s units come from its full test pool (`uniad_read.sh:158`). A TF++ unit can then hold fewer than 5 failing routes in the scored set. Whether any does cannot be checked from main (TF++ routes are not in this clone) |
| c12 | a failed scoring job stops the read | pass | `wait $p` under `set -e` (`uniad_read.sh:211`, `uniad_caption.sh:57`) |
| c13 | the point estimate and the draws use the same Jaccard | pass | `weighted_jaccard` with every weight at 1 equals `jaccard`, including `jaccard(empty, empty) = 0` (`src/harness/bootstrap.py:31-35`, `src/harness/scoring.py:21-27`) |
| c14 | unit admission | see b8 | the float boundary in `units_rule.py:44` |

## What is unverified

- Every number in the table itself. The JSON reports, `units-uniad.txt`, `classes.txt` and `commit.txt` are on Savio
  only. Every check above is internal consistency against the prereg and the code.
- Paired intervals that the table does not print: a11, a13, a19's `query-mean − m23`, and a23's caption − m23.
- Wall's counts, the other UniAD types' counts, and the named-class verdict (b5–b7).
- Whether the final jobs ran at a commit at or after 47f26b4 (likely, from the timestamps, but not shown).

## Tests added

- `tests/test_units_rule.py`: the stated final counts give the stated units and ratios; the five-failing minimum when
  twins never fail; a strict xfail pinning the exact-1.5× float bug (b8).
- `tests/test_view_score_final.py`: repeated `--restrict` (c1), the per-model median (c2), reported-only rows (c5),
  and the final-read CUTOFF refusal (c6).
- Checked that the tests can fail: on 47f26b4^ the restrict test fails. On 3e19141^ the restrict, median and
  reported-only tests fail. The file was restored afterwards (`git checkout`).

## Commands run

```bash
PYTHONPATH=src /opt/miniconda3/bin/python docs/research/experiments/f2d-unpooled/units_rule.py \
  configs/rollout/f2d-test-simlingo.manifest.json results/savio/f2d-test-simlingo/routes.jsonl --model simlingo
/opt/miniconda3/bin/python -c "print(9/30 >= 1.5*(6/30))"        # False; boundary sweep over n = 29, 30, 60
/opt/miniconda3/bin/python -  # manifest counts per type, the two missing routes, distinct pairs (100)
git log --format='%h %ad %s' --date=iso 47f26b4^..HEAD -- <the four scripts> docs/prereg-views.md
git show 1557df8 -- docs/research/comparison-table.md   # L38 written while caption was pending
PYTHONPATH=src /opt/miniconda3/bin/python -m pytest -q tests/test_units_rule.py tests/test_view_score_final.py \
  tests/test_view_score.py tests/test_view_score_order.py   # 10 passed, 1 xfailed
for c in 47f26b4^ 3e19141^; do git show $c:docs/research/experiments/f2d-unpooled/view_score.py > \
  docs/research/experiments/f2d-unpooled/view_score.py; pytest -q tests/test_view_score_final.py; done; \
  git checkout -- docs/research/experiments/f2d-unpooled/view_score.py
```
