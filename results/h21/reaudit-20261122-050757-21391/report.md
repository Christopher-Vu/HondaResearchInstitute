# Re-audit: the fixed UniAD read pipeline against `views-prereg-v1`, before the final read

Auditor: LAPTOPWORKER 20261122-050757-21391, 2026-11-22, at HEAD `dbbe685`. Independent of the other re-audit.
No UniAD file, UniAD result folder or `gaps/sealed/` was opened. The interim numbers in `docs/STATUS.md` were seen as
text and are not used here.

References: `read.sh` = `docs/research/experiments/f2d-unpooled/uniad_read.sh`, `cap.sh` = `uniad_caption.sh`,
`vs.py` = `view_score.py` (same folder). "prereg L*n*" = current `docs/prereg-views.md`. The tag's text is unchanged
except for the post-tag records at prereg L28-54 (`2847aef` and later, `838070b` adds L46-54).

## The six earlier items

| # | Item | Verdict | Evidence |
|---|---|---|---|
| 1 | Row-vs-row paired intervals | fixed | `vs.py:141-144` builds every A - B interval on the same draws, both metrics; `vs.py:145-148` `ranks_above` (rabm); both written to the JSON (`vs.py:169`) and printed (`vs.py:174-177`). Sign logic checked by hand and by test (below). |
| 2 | `--select` never passed | fixed | `read.sh:175,187` passes `--select best_new img-mean query-mean --select-vs B3_behaviour m23`; `cap.sh:32,36` adds `caption` as a member. The pick is the per-draw rabm argmax (`vs.py:154-155`). |
| 3 | Caption row not scored by the read | partly fixed | `cap.sh` scores it with every other row rescored on its routes (`cap.sh:21-31,39-44`), median over runs (`vs.py:88-92,114-115`). It is a second command, which the laptop captioning step makes unavoidable. The pooled path is broken by new finding N1. |
| 4 | SimLingo `img-mean` site | fixed | Primary row is the unpooled `llm10-mean` row (`read.sh:144,168`), the 512 image tokens at layer 10 (`f2d-unpooled/protocol.md:27,30-31`), per ruling prereg L49-50. The whole-sequence mean is reported beside it as `img-mean-allseq` (`read.sh:145,172`), pooled only (`read.sh:203-205`), never under `img-mean`. The latent `SIMLINGO_IMG=vit` switch is gone. |
| 5 | TF++ `query-mean` site | fixed | Primary is `--site all_tokens --layer-fraction 1` (`read.sh:148,169`). `all_tokens` is `layer_mean`, every query token of every `join` call (`adapters/tfpp/tfpp_agent.py:8,192`; `export_activations.py:114`), last layer (`cache_methods.py` `depth_layers`). The last call alone is `query-mean-lastjoin` (`read.sh:149,173`; `tfpp_agent.py:10,194`). The cache file names changed, so the old cached `query-mean.json` and `img-mean.json` cannot be picked up. |
| 6 | Silent exit at the `DIRS` loop | fixed | `read.sh:45` uses `if ...; fi`, so the loop returns 0 when the last job is missing (reproduced in bash: the loop survives with an empty result); `read.sh:46` stops with a message when no job folder exists. |

## New findings

**N1 (important; changes the pooled caption read): `cap.sh` drops TF++'s route restriction.**
`vs.py:62` declares `--restrict` with `nargs="*"` and no `action="append"`, so a second `--restrict` replaces the
first. `cap.sh:46` builds `--restrict tfpp=$TC/routes.txt` followed by `$U`, which ends in
`--restrict uniad=$C/routes-uniad.txt` (`cap.sh:39`). TF++ is then scored on every route, not on the re-driven
routes whose failure reproduced (prereg L152), and its caption axes are scored against failing routes they could
never contain. Measured on dev data, with that exact argument shape: TF++'s failing count stays 174 of 174 and its
unit sizes stay 12/12/28/11/9/8. With TF++'s restriction alone it drops to 73, with unit sizes 2/6/10/4/0/2
(`restrict-shape.json` against `restrict-control.json`). UniAD alone is unaffected because it passes one
`--restrict`. Fix (text only): in `vs.py:62` use `action="extend"`, or in `cap.sh` pass one
`--restrict tfpp=... uniad=...`. A guard would also help: stop if a `--restrict` names a model that is not given.

**N2 (minor): the reported-only rows enter the partial order.** In the pooled calls, `img-mean-allseq` and
`query-mean-lastjoin` are ordinary rows, so `pairwise` and `ranks_above` include them (`vs.py:142-148`). Their names
are distinct and they are not `--select` members, which is correct. The write-up must still not quote a rank for
them (prereg L49-52: "reported beside it, labelled").

**N3 (needs a ruling; pooled caption only): which run is paired with which across models.** `vs.py:105` takes run
r of every model together, then the median over r of the pooled mean. The runs of different models are independent,
so this pairing is arbitrary. The per-model median, then the mean over units, gives a different number in general.
Prereg L123 says "the median of its 6 runs' scores" and does not settle the pooled case. UniAD alone is unaffected.

**N4 (minor; interim only): the label does not say "run late".** Ruling prereg L47-48 asks for that label. `read.sh:38`
TAG has `interim read at views-prereg-v1 (blind)`, and only `cutoff.txt` records the cutoff (`read.sh:59`). The
final read is not affected.

**N5 (cosmetic, from before): `wait` hides a failed scoring job.** `read.sh:206` and `cap.sh:53` run `view_score.py`
in the background, and a bare `wait` returns 0 (reproduced: `(exit 3) & wait` gives 0). A failure shows only in the
tailed log. Fix: keep the process ids and `wait` each one, so `set -e` stops the script.

**N6 (cosmetic): an empty pooled unit list is not caught.** `nowall` (`read.sh:156`) turns an empty list into one
space. The pattern `pooled-*:?*` (`read.sh:185`) accepts that, and `view_score.py` then fails on `--gaps` with no
value, in the background (N5). This cannot happen while SimLingo and TF++ have rule units.

**N7 (unclear): the caption call reuses the read's units.** `cap.sh` takes the units from `score.env`
(`read.sh:195-197`) and does not rerun `units_rule.py` (which has `--restrict`) on the caption routes. The gaps do
shrink with the restriction (`vs.py:79-87`). Prereg L154 ("rescored on the same routes") and L206-207 ("the units
rule runs ... on that read's routes") allow both readings. It changes nothing when every failing route has frames.

**N8 (minor): the caption pool keeps framed routes, not described ones.** `cap.sh:26-27` keeps a failing route if it
has frames in the mapping. A framed route whose description never came back stays in the pool and can only lower the
caption row. The prereg covers only "a failing route with none [frames]" (L117).

**N9 (checked, correct): the cutoff.** `read.sh:49-58` drops a route when its chosen attempt's `result.json` has an
mtime after `date -d "$CUTOFF"`. That matches "by file time" (prereg L47-48). The cutoff string yields epoch
1795280400 = 2026-11-21 09:00 -08:00. GNU date returns that under `TZ=UTC` and `TZ=Asia/Tokyo` too, because
of the `PST` suffix. 2026-11-21 falls after the end of daylight time on 2026-11-01, so PST is the right offset. The
filter runs before `dirs.txt`, so shards, units and rows use only the kept routes (`read.sh:61-71`). A failing `date`
leaves an empty argument, and `float("")` then stops the pipe under `pipefail`, so it is not silent. Risks: an mtime
reset by a copy without `-p`, and `date -d` is GNU-only (fine on Savio). The final read leaves `CUTOFF` unset.

**N10 (minor, from before): the tag gate checks only that the tag exists** (`read.sh:34`). It does not record the
tag's commit. Proposed: append `git rev-parse views-prereg-v1^{commit}` to `commit.txt`.

**N11 (cosmetic, from before): the try count is still not reported** (prereg L197).

Checked and matching the prereg:
- **`ranks_above`.** Keys exist only for `names[i] - names[j]` with i < j (`vs.py:144`). For n before m the code tests
  `n - m` lower bound > 0. For n after m it tests `m - n` upper bound < 0, which is the same event. The missing key's
  default (`[0]` or `[0, 0]`) is never true. This is correct in both orders.
- **Selection.** Members are exactly the new views. `vit-mean` and the two reported-only rows are left out. The
  comparators are B3-behaviour, the primary rival, and m23, the primary finalist. The pick is taken per draw on the
  primary metric. In `read.sh` the selection covers two of the three new views, and `cap.sh` covers all three. Only
  `cap.sh`'s selection is "the best new view" of prereg L196.
- **Fixed settings.** M = 10 (`sprint_score.py:31`, `to_axes.py:17`). There are 2,000 draws (`vs.py:68`, not
  overridden). The bootstrap resamples manifest `pair`s, all models jointly (`vs.py:81,107,127-128`). The primary
  units are the rule units without Wall, removed by name (`read.sh:156,199,203`). The caption row is the median over
  6 runs within every draw (`vs.py:114-115,130`).

## Dry run (dev data only: SimLingo H21b, seeds 24-26, never evidence)

The script is `dryrun.sh` in this folder. The pair field was stripped of `-sNN` into `manifest-stripped.json`, which
gives 100 pairs. The model is named `uniad`, so the read's filters run unchanged. Stand-ins:
- `img-mean` is `route-L20` and `query-mean` is `j09`.
- `caption` is a synthetic 6-run file built from six existing rows' axes, which tests the mechanics only.

Measured:
- **Units** (`units_rule.py`): Animals, BadParking, CustomObstacles, FullyBlocked, PedestriansOnRoad,
  RightConstruction and Wall. Without Wall, 6 units over 593 routes, 100 pairs and 174 failing.
- **Rank-averaged best match** (rule units without Wall), with the contrast to B3-behaviour:

  | Row | Score | Minus B3-behaviour |
  |---|---|---|
  | B3-behaviour | 0.133 | |
  | B3-infraction | 0.214 | +0.081 [0.036, 0.121] |
  | m23 | 0.190 | +0.057 [-0.004, 0.135] |
  | m40 | 0.168 | +0.035 [-0.002, 0.102] |
  | `img-mean` stand-in | 0.091 | -0.042 [-0.084, 0.013] |
  | `query-mean` stand-in | 0.133 | +0.000 [-0.039, 0.059] |

- **`ranks_above`:** B3-infraction ranks above B3-behaviour, `img-mean` and `query-mean`; m23 and m40 rank above
  `img-mean`; every other pair ties. A hand computation from the 15 pairwise intervals gives the same lists. Each
  row's `vs_primary` interval equals its pairwise interval against B3-behaviour to 4 decimals.
- **Antisymmetry:** the same call with the row order reversed turns every A - B key into B - A. Over 30 intervals
  (15 pairs × 2 metrics), the largest |lo(A-B) + hi(B-A)| is 1.4e-16. `ranks_above` is identical in both orders.
- **`--select` as `read.sh` passes it:** `query-mean` is the point choice, picked in 96.9% of draws. Against
  B3-behaviour it is +0.000 [-0.035, 0.059]; against m23 it is -0.057 [-0.130, 0.027].
- **`--select` with caption, as `cap.sh` passes it:** the caption stand-in scores 0.150 over 6 runs. That equals the
  mean of the 3rd and 4th run scores (0.133 and 0.168), so the median is taken correctly. It is picked in 68.4% of
  draws, and the best new view against B3-behaviour is +0.018 [-0.000, 0.054].
- **`--restrict` shape:** see N1.

Test added: `tests/test_view_score.py`. On a synthetic pool it checks three things in both row orders: `ranks_above`,
the mirror symmetry of A - B and B - A, and that a `runs:` row scores as its median run. 2 passed.

## Not checked

- Anything on Savio:
  - the content and route set of `$REF/f2d-unpooled/simlingo-score/rows/llm10-mean.json` (fit on 1,188 routes per
    `protocol.md:14`, against the views read's SimLingo routes file);
  - that the TF++ cache really has one `join` call per step (STATUS records all-join = last-join, max difference 0,
    which one call per step would explain);
  - the `result.json` mtimes;
  - that `JOBS` (`read.sh:37`) lists every job for the final read.
- UniAD's layer names (`read.sh:115-122`), because no UniAD file was opened.
- Stages 1-3 of `read.sh` (merge, shards, cache, row building), because they need the job folders.
- `api.py` (`210ba5d`): it only raises grouping's `max_tokens` to 32,000 (`GROUP_TOKENS`) and leaves the prompts
  alone. The diff was read but not run.

## Commands

```bash
git show views-prereg-v1:docs/prereg-views.md; git diff views-prereg-v1 HEAD -- docs/prereg-views.md
git show 1be49a1 210ba5d 838070b
bash results/h21/reaudit-20261122-050757-21391/dryrun.sh            # 41 s
# hand check of ranks_above, antisymmetry, vs_primary and selections: inline python over the JSON outputs here
gdate -d "2026-11-21 09:00 PST" +%s; TZ=UTC gdate -d ...; TZ=Asia/Tokyo gdate -d ...   # all 1795280400
bash -c 'set -euo pipefail; (exit 3) & wait; echo "wait returned $?"'                 # wait returned 0
PYTHONPATH=src /opt/miniconda3/bin/python -m pytest -q tests/test_view_score.py         # 2 passed
PYTHONPATH=src /opt/miniconda3/bin/python -m pytest -q   # 834 passed, 24 failed, 43 skipped
PYTHONPATH=src /opt/miniconda3/bin/python scripts/check_sealed_imports.py                # clean
```

The 24 full-suite failures are all in `test_submit.py`, `test_savio_runtime.py`, `test_slow_watchdog.py` and
`test_j10_hmmfisher.py`. They are the same 4 files the earlier audit listed, and they come from the laptop (no
hmmlearn, no Savio tools). A second run counted 25 failures in the same 4 files.
