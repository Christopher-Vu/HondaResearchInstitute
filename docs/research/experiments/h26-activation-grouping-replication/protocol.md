# H26: does H24's activation grouping replicate on H3's pool?

**Locked by the commit tagged `h26-locked`, before any H26 data is read.** Jerry asked for this on 2026-11-13, after H24. Dev only and not blind: the categories are public practice gaps. No `PRD.md` 13.1 branch can be claimed (C34).

Every number is tagged: measured, estimate, or guess.

## Why

On H1's pool, H24's primary arm (`act`, a Gaussian mixture on layer-10 activations) beat B3 and random groups of the same sizes on all three camera faults. Its median lead was +0.109 Jaccard, with a route bootstrap of +0.017 to +0.143 (measured). It missed only the 0.15 margin. Scored on P4 and P7 alone, the two faults H3's pool has, the same H1 axes read `ahead`: median delta +0.155, route bootstrap +0.045 to +0.221, P4 +0.270, P7 +0.038, against random alone +0.190 (measured with `score_sets.py` unchanged; `docs/research/data/h24_h1_p4p7_report.json`). That two-fault reading is the reference here. It is the strongest activation reading in this study, and it came from one pool. H26 asks whether it holds on drives it has not seen.

## The pool

H3's pool, as `docs/research/experiments/h3-confirm-fresh-pilots/protocol.md` built it: `step5-background-wave3` (200 routes), `step5-confirm-p4` and `step5-confirm-p7` (60 pairs each). 435 routes have outcomes: 199, 118 and 118 (measured).

- **New:** every drive and every route id. No route id appears in H1's pool, and the pilots use different traffic seeds (11 and 12).
- **Not new:** the roads. 199 of the 200 background base roads, and 59 of the 60 base roads in each pilot, also appear somewhere in H1's pool (measured from the manifests). Only 14 of the 60 P4 base roads and 19 of the 60 P7 base roads carried the same fault in H1's pilots; the rest of the overlap is background or other-fault routes. So this replicates across drives and traffic, mostly not across places.
- **Categories:** `P4_camera_occlusion` and `P7_camera_freeze`, the slice routes that failed. There is no P8 here, so the check covers two faults.
- **B3:** a fresh run on this pool (`emit_directives`, seed 0). Its score is already known from H3's run with the same code on the same shards: P4 0.194, P7 0.367 (`docs/research/data/h3_layer10_plain.json`). On H1's pool B3 scored 0.176 on both. P7's bar is therefore much higher here than on H1, where H24_act's P7 median was 0.214. `read.py` reports whether the fresh B3 matches the known one.

## What runs

Nothing about the method changes. `export_features.py`, `mixture.py` and `score_sets.py` run exactly as tagged `h24-h25-locked`: the same 5 arms, 18 seeds, outcome weight 1, 10 components, B3's 3 s window, 50 matched random partitions and a 1,000-replicate route bootstrap. One CPU export job (`export.sbatch`), then the mixtures and scoring on a laptop.

## The reading, fixed before any result

`read.py` reads H24's primary arm, `H24_act`, from `score_sets.py`'s report.

| Result | Condition | Fixed sentence |
|---|---|---|
| `untested` | Fewer than 12 of 18 runs have an axis | "H26 is untested: H24_act produced fewer than 12 runs with an axis on H3's pool." |
| `replicates` | H24's full rule (`score_sets.py` reads `ahead`): median delta at least 0.15, both categories above 0, route bootstrap above 0. This is what the H1 reference shows on the same two faults | "On H3's pool, grouping routes by their activations recovers P4 and P7 better than B3 and random groups of the same sizes, by a median of at least 0.15 Jaccard on both faults, as it did on H1's pool." |
| `weaker` | Median delta above 0, both categories above 0, route bootstrap above 0, but under 0.15 | "On H3's pool, grouping routes by their activations beats B3 and random groups of the same sizes on both faults, but by a median under 0.15 Jaccard, less than on H1's pool." |
| `not_replicated` | Otherwise | "On H3's pool, grouping routes by their activations is not shown to beat B3 and random groups of the same sizes on both faults." |

Reported beside every outcome, with no bearing on it: H24_act's median score per fault and its lead over random groups alone, next to the H1 reference (P4 0.447, P7 0.214, +0.190), so a reader can tell whether the method fell or B3 rose.

The other four arms are reported beside it, with no bearing on the result.

## What this cannot show

- Many roads repeat (14 and 19 with the same fault), so a road-specific quirk could carry over from H1's pool.
- Two faults, not three. With P8 absent, the every-category condition is 2 of 2, and P7's lead on H1 was only +0.038.
- H3 has already read M1 on this pool (`docs/research/data/h3_layer10_plain.json`), but no choice in H24's method came from it.
- Every score picks the best axis using the answer, for every method and for the random control.

## Cost

About 2 SU for the export (estimate; H24's export of two larger pools took 1,042 s on 4 cores).

## Predictions (guesses)

`not_replicated` 60%, mostly because B3 is strong on P7 here (0.367); `replicates` 20%; `weaker` 15%; `untested` 5%.

## Review before the lock

Two reviewers and three skeptics per finding checked this protocol. All three findings held and are fixed: the reference is now H1's two-fault reading, which is `ahead`, not the three-fault `not_ahead`; B3's score here was already known and is now stated; and the road overlap is broken down by fault.

## Commands

```bash
bash scripts/submit.sh cpu --time=0-01:30:00 docs/research/experiments/h26-activation-grouping-replication/export.sbatch
```

Then, with `results/savio/h26/` copied back:

```bash
PYTHONPATH=src python docs/research/experiments/h24-error-aware-grouping/mixture.py results/savio/h26/h3-features.npz --output results/savio/h26/h26-axes.json
PYTHONPATH=src python docs/research/experiments/h24-error-aware-grouping/score_sets.py --axes results/savio/h26/h26-axes.json --manifests configs/rollout/step5-background-wave3.manifest.json configs/rollout/step5-confirm-p4.manifest.json configs/rollout/step5-confirm-p7.manifest.json --routes results/savio/h26/h3-routes.jsonl --categories P4_camera_occlusion P7_camera_freeze --b3 results/savio/h26/h3-b3.json --min-runs 12 --pool "H3's pool (P4, P7)" --label "H26 on H3's pool" --output results/savio/h26/h26-report.json
python docs/research/experiments/h26-activation-grouping-replication/read.py results/savio/h26/h26-report.json --output docs/research/data/h26_result.json
```
