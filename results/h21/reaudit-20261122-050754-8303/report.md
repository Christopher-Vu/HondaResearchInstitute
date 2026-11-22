# Re-audit: the fixed UniAD read against `views-prereg-v1`, before the final read

Auditor: laptop worker 20261122-050754-8303, independent. Code at `dbbe685`. No UniAD file, UniAD result folder,
`adapters/uniad/` or `gaps/sealed/` was opened. The other worker's re-audit was not looked for.

References:
- "tag L*n*" is a line of `git show views-prereg-v1:docs/prereg-views.md`; "prereg L*n*" is a line of the current
  `docs/prereg-views.md` (the 2026-11-22 rulings are prereg L46–54).
- `read.sh` is `docs/research/experiments/f2d-unpooled/uniad_read.sh`, `cap.sh` is `uniad_caption.sh` and `vs.py` is
  `view_score.py`, all in that folder.

## The six items of the first audit

| # | Item | Verdict | Evidence |
|---|---|---|---|
| 1 | Row-vs-row paired intervals | **fixed** | `vs.py:142-144` stores A−B for every pair of rows on the same draws; `vs.py:145-148` builds `ranks_above` from the rank-averaged interval, reading the key both ways. Both branches are right: `n - m` with lower end > 0, or `m - n` with upper end < 0 (the same condition, since a percentile interval of −x is the negated, flipped interval of x). Checked on dev data below and pinned by `tests/test_view_score_order.py` |
| 2 | `--select` never passed | **fixed** | `read.sh:175,187` pass `--select best_new img-mean query-mean --select-vs B3_behaviour m23`; `cap.sh:32,36` add `caption`. Members are the new views only: `vit-mean` and the two reported-only rows are left out. The member is re-picked per draw by highest rank-averaged score (`vs.py:154-155`) and compared with B3-behaviour (the primary rival) and m23 (the primary finalist) on the same draw (`vs.py:163-165`). But see new findings N2 and N3 |
| 3 | Caption row not scored by the read | **fixed for UniAD alone; partly fixed for the pooled ranking** | `cap.sh` is a second command, which is needed because captioning runs off Savio. It builds axes (`cap.sh:18`), keeps every passing route and every failing route with frames (`cap.sh:21-31`), rescores every row on those routes (`--restrict`, `cap.sh:39`; `vs.py:79-80,99-100`), and scores `caption` as the median over runs within every draw (`vs.py:114-115`; tag L96). The pooled caption ranking runs only when a TF++ caption folder is passed (`cap.sh:45`), and its run pairing across models is arbitrary (N1) |
| 4 | SimLingo `img-mean` site | **fixed** | The primary `img-mean` row is `$REF/f2d-unpooled/simlingo-score/rows/llm10-mean.json` (`read.sh:144,168`), the unpooled experiment's 512-image-token row at LLM layer 10 (`f2d-unpooled/protocol.md:27`), as ruled at prereg L49–50. The whole-sequence layer-10 mean is a separate row named `img-mean-allseq` (`read.sh:145,172`), pooled only. The old `SIMLINGO_IMG=vit` switch and the stale `$V/simlingo/img-mean.json` are gone from the code |
| 5 | TF++ `query-mean` site | **fixed** | The primary `query-mean` row is `all_tokens` at the last layer (`read.sh:148,169`). That site is `layer_mean`, the mean over every query of every `join` call (`adapters/tfpp/tfpp_agent.py:8-9,192`), as ruled at prereg L51. The last join call alone (`driving_queries` = `layer_driving_mean`, `tfpp_agent.py:10,194`) is a separate row named `query-mean-lastjoin` (`read.sh:149,173`), pooled only. Both write new file names, so no stale cache is reused |
| 6 | Silent exit at the job loop | **fixed** | `read.sh:45` uses `if … then … fi`, which returns 0 when the last job folder is missing. `read.sh:46` stops with a message when no folder exists. Reproduced in bash: the old form exits 1 with no message, the new form continues, and the guard prints its message |

## New findings

Ranked by how much they can change what the final read says.

**N1. The pooled caption score depends on how run numbers line up across models** (needs a ruling).
`vs.py:105` builds run r of the pooled row from run r of every model, and `vs.py:114-115` takes the median of those
pooled runs. Tag L93–96 makes the 6 grouping runs independent per model, so "run 2 of SimLingo goes with run 2 of
UniAD" means nothing. A different numbering gives a different score. Measured on dev data (pooled smoke, second model's
runs rotated by 3, everything else the same): caption top-10 best match 0.2026 → 0.1957, rank-averaged 0.1545 →
0.1540, interval against B3-behaviour [−0.0144, +0.0621] → [−0.0105, +0.0595], and its share of the best-new-view
pick 0.0985 → 0.1115. UniAD alone is not affected (one model).
Proposed fix: score each model's caption row as the median over that model's own runs, in every draw, then pool with
the fixed mean over units. This needs no pairing. The other choice is to rule that the run index is the pairing and
record it.

**N2. The best-new-view interval can clear the fleet when no new view does** (a reading issue, not a code bug).
The code follows tag L169 ("re-selected in every draw"). But a per-draw maximum is biased upward: in draws where the
point choice is low, another member is high, so the lower end rises. Measured on dev data with stand-ins: `best_new`
against B3-behaviour [+0.0057, +0.1017], while its point choice (m40) alone is [−0.0018, +0.1017] and no member's own
interval clears 0. Tag L166 lets a *row* rank above the fleet; `best_new` is not a row.
Proposed: report `best_new` under its own label beside each member's own interval, and do not write "the best new
view ranks above the fleet" from it alone. If Chris wants a selection-adjusted claim, it needs a ruling on which
statistic carries it.

**N3. `read.sh`'s `best_new` leaves out `caption`** (nit). `read.sh:175` selects over `img-mean` and `query-mean`
only, under the same key name `best_new` that `cap.sh:32` uses for all three new views. A number quoted from
`read.sh`'s JSON as "the best of the new views" would be the wrong one. Proposed: rename it in `read.sh` (for example
`best_new_without_caption`) or drop it there.

**N4. The reported-only rows enter the pooled partial order without a flag** (nit). `img-mean-allseq` and
`query-mean-lastjoin` are passed as ordinary rows (`read.sh:203-205`; `cap.sh:47` through `ROWS_P`, `read.sh:194`), so
they appear in `pairwise` and `ranks_above` like ranked rows. Prereg L50–52 says they are "reported beside" the
primary. Their names are distinct, so nothing is mislabelled. Proposed: add a reported-only list to the report JSON,
or leave them out of `ranks_above`.

**N5. A crashed scoring job still ends the read with exit 0** (carried over, now in two scripts). `read.sh:186-187`
and `cap.sh:36-37` run `view_score.py` in the background, and a bare `wait` (`read.sh:206`, `cap.sh:53`) returns 0
whatever they returned (reproduced in bash). The traceback shows only in the tailed logs, and the JSON is missing.
Proposed: collect each `$!` and `wait` on each PID, so that `set -e` stops the script.

**N6. A failing site lookup is not caught where it happens** (nit). `read.sh:115-122` uses
`read -r IMG TRK B7L <<<"$(python …)"`. Under `set -euo pipefail` a failing python leaves all three empty and the
script goes on (reproduced). `sites.txt` then records empty layers, and the next `cache_methods.py` call fails with an
argparse error that does not name the cause. Proposed: `SITES=$(python …)` first (a bare assignment does stop on
failure), then `read … <<<"$SITES"`.

**N7. The cutoff is right, but it has three loose ends.**
- Correct: `CUTOFF="2026-11-21 09:00 PST"` parses to 1795280400 = 17:00 UTC (measured with GNU `date`). PST is right
  for that date (daylight time ended 1 Nov 2026). The file is the chosen attempt's `result.json` (`read.sh:55`), which is
  the leaderboard checkpoint. The attempt is chosen before the filter, as the first valid attempt in job-id order
  (`adapters/simlingo/score_routes.py:37,55-56,104`). A wrong zone string (`PT`, `PDT`) fails loudly (measured).
- Loose end 1: nothing stops `CUTOFF` being set on the final read. A leftover exported variable would quietly cut
  the final pool. Proposed: refuse `CUTOFF` when `READ=final`.
- Loose end 2: `read.sh:47` prints the merge summary before the cutoff is applied, and `merge/res` and `merge.log` keep
  every route. The printed driving score is therefore not the interim pool's. Proposed: print `cutoff.txt` last.
- Loose end 3 (could not check): file time is only right if no `result.json` was copied or touched after its drive,
  and if job-id order matches time order for any route with two valid attempts.

**N8. Run records do not carry the token cap** (nit, `210ba5d`). The grouping cap moved from 16,000 to 32,000
(`api.py` `GROUP_TOKENS`). The prompts are unchanged, so the prereg text is met. `f2d-views-caption/protocol.md`
records that UniAD's interim runs 2 and 4 were cut off at 16,000 and sent again at 32,000, while runs 0, 1, 3 and 5
ran at 16,000. `requests-group.json` (`api.py:96-97`) records model, effort and prompt but not `max_tokens`, so the
machine record cannot show which run had which cap. SimLingo's grouping ran at 16,000. Proposed: write `max_tokens`
into both request records.

**N9. Smaller points.**
- The per-unit table of a multi-run row comes from the lower-middle run (`vs.py:117-120`). With 6 runs, the row score
  is the mean of the 3rd and 4th (`np.median`, `vs.py:115`), so the per-unit numbers do not average to the row score.
  Label the per-unit columns.
- `cap.sh` does not write the commit it ran at; `read.sh:42` does.
- `cap.sh` scores the caption-restricted pool on the full read's units (`score.env`, `read.sh:195-197`). It does not
  rerun the units rule. This fits prereg "rescored on the same routes beside it" (tag L127). A unit's gap set shrinks
  if some of its failing routes have no frames.

**Checked and matching:** M = 10 (`sprint_score.py:31`; `vs.py:39,45`; `distinct` cuts at M). 2,000 draws
(`vs.py:68`; neither script passes `--replicates`, checked by grep). Primary units are the rule units without Wall,
removed by name (`read.sh:156,199,203`; `cap.sh` through `score.env`). The pair bootstrap resamples manifest pairs,
with all of a pair's routes and models together (`vs.py:126-128`). The tag gate is unchanged (`read.sh:34`). The
caption median is taken inside every draw (`vs.py:130` calls `score`, which takes the median).

## Dry run (scoring stage only; dev data, never evidence)

Input: the H21b three-seed SimLingo pool (`results/h21/h21b/`), with the `-sNN` suffix stripped from `pair` into
`manifest-pairfix.json`. That gives 100 pairs; the unstripped manifest has 300. `view_score.py` was called as
`read.sh:183-187` and `cap.sh:33-37` call it: bash word splitting, the `nowall` filter, `--primary-rival
B3_behaviour`, and a `--select … --select-vs B3_behaviour m23` entry. Stand-ins: m40 and j09 play `img-mean` and
`query-mean`. `caption` is a `runs:` row built from six H21b method files (m15-source, m39-source, route-L20, route-L8,
j09, b3_infraction) read as six runs. It tests the code path only.

Rule units (`units_rule.py`): Animals, BadParking, CustomObstacles, FullyBlocked, PedestriansOnRoad,
RightConstruction, Wall. Primary without Wall: 6 units with 12, 12, 28, 11, 9 and 8 failing routes; 593 routes.

Measured, rule units without Wall (rank-averaged, top-10; rank-averaged Δ against B3-behaviour with its interval):

| Row | rabm | top-10 | Δ vs B3-behaviour [95%] | ranks above |
|---|---|---|---|---|
| B3_behaviour | 0.133 | 0.166 | — | — |
| B3_infraction | 0.214 | 0.258 | +0.081 [+0.036, +0.121] | B3_behaviour, caption, j09 |
| m23 | 0.190 | 0.238 | +0.057 [−0.004, +0.135] | — |
| m40 | 0.168 | 0.224 | +0.035 [−0.002, +0.102] | — |
| j09 | 0.133 | 0.165 | +0.000 [−0.039, +0.059] | — |
| caption (stand-in) | 0.154 | 0.203 | +0.021 [−0.014, +0.062] | — |

`best_new` (m40, j09, caption): point choice m40; per-draw share 0.733 / 0.1685 / 0.0985; against B3-behaviour
+0.035 [+0.0057, +0.1017]; against m23 −0.022 [−0.069, +0.042].

Checks (`check.py`, measured):
- **Antisymmetry.** With the rows listed in reverse order, every B−A equals −(A−B): 15 pairs × 2 metrics, largest
  error over deltas and interval ends 2.4e-16.
- **`ranks_above` against a hand computation from `pairwise`.** It agrees in both row orders and is identical across
  them. B3_infraction is on both sides of a key across the two orders, so both branches of `vs.py:146-147` were
  exercised.
- **`vs_primary` against the pairwise entry.** It is identical for every row (0 mismatches).
- **Caption median by hand.** Per-run rank-averaged scores are 0.1888, 0.1757, 0.0905, 0.1192, 0.1332 and 0.2142. Their
  median is 0.154463, which equals the reported 0.154463.
- **Pooled path.** A second model name over the same pool, with caption runs aligned: 1,186 routes, 100 pairs, and
  every number identical to the single-model run, so pairs are resampled jointly. With the runs rotated, see N1.

Test added: `tests/test_view_score_order.py`, 2 tests on a synthetic pool. It checks that `ranks_above` matches the
pairwise intervals whichever way a key is written, that it does not depend on row order, and that A−B and B−A are
exact negatives. Result: 2 passed.

## What I could not check

- Whether `$REF/f2d-unpooled/simlingo-score/rows/llm10-mean.json` covers the same routes as
  `$REF/f2d-test-simlingo/routes.jsonl` (1,188 replayed in `f2d-unpooled/protocol.md:14`, against 1,185 scored in tag
  L39). A route refused by the replay check would be missing from SimLingo's `img-mean` axes without any error. Both
  files are on Savio.
- What `TFPP_CAPTION_DIR/routes.txt` lists (`cap.sh:8-9`). If it holds only the failing re-driven routes, TF++'s
  passing routes leave the pooled caption pool. That changes the pair weights, unlike UniAD's list, which keeps
  passing routes (`cap.sh:27`).
- UniAD's layer names (`read.sh:115-122`), the final `JOBS` list, and whether any `result.json` time was changed after
  its drive (N7). These need UniAD files or Savio.
- Stages 1–3 of `read.sh` (merge, shards, caches, row building), and `cap.sh`'s `to_axes.py` and restrict step on real
  caption output.
- The try count and the separate SimLingo-alone and TF++-alone reports (tag L170) are still not produced by either
  script. The first audit noted this, and it was not re-litigated here.

## Commands

```bash
/opt/miniconda3/bin/python results/h21/reaudit-20261122-050754-8303/setup.py   # pair-fixed manifest, stand-in caption runs
PYTHONPATH=src /opt/miniconda3/bin/python docs/research/experiments/f2d-unpooled/units_rule.py \
  results/h21/reaudit-20261122-050754-8303/manifest-pairfix.json results/h21/h21b/routes.jsonl --model simlingo \
  > results/h21/reaudit-20261122-050754-8303/units-h21b.txt
bash results/h21/reaudit-20261122-050754-8303/dryrun.sh
PYTHONPATH=src /opt/miniconda3/bin/python results/h21/reaudit-20261122-050754-8303/check.py
PYTHONPATH=src /opt/miniconda3/bin/python -m pytest -q tests/test_view_score_order.py   # 2 passed
PYTHONPATH=src /opt/miniconda3/bin/python -m pytest -q        # 834 passed, 24 failed, 43 skipped (failures as in the first audit)
PYTHONPATH=src /opt/miniconda3/bin/python scripts/check_sealed_imports.py                 # clean
gdate -d '2026-11-21 09:00 PST' +%s                                                      # 1795280400
```
