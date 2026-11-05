# H17: a dev rehearsal of the causal check, on P4's axis

**Locked 2026-11-04 before submission.** Dev only (PRD §9.2). **This is a dev rehearsal and it is not Step 9's verdict.** Whatever it finds, every axis card keeps `causal: untested`.

Every number is tagged: measured, simulated, estimate, read from the code, or guess. None of the limits or predictions is a result.

## Why

No axis has ever had a causal test. `src/discovery/contrastive.py` writes `causal={"verdict": "untested"}` on every card, and `docs/research/dev-report.md` lists Step 9's verdict as never run. PRD §9.2 asks for projection removal against random directions of matched norm. H17 runs that operator once on one axis, offline, so the code, the controls and the rule have been exercised before Step 9 needs them.

## What this cannot show

Read this before the numbers.

- **Replay has no closed loop.** Each frame is replayed alone. A changed plan never moves the car, so H17 cannot say a crash would be avoided or caused, and it cannot see effects that build up over several seconds. Step 4's Part C is the warning: a knock-out with a median open-loop shift of 3.0 cm on route and 25.5 cm on speed (layer 11's driving queries) gave 11 failures of 40 against 9 intact, within run-to-run noise. One with 94.5 cm on route and 4.05 m on speed (all tokens at layer 0) gave 31 of 40 (all measured, `docs/steps/04-ablation/partB-summary.json`).
- **A shift has no sign here.** A bigger shift is not a safer plan. H17 reports how far the waypoints move and does not judge the new plan.
- **P4's cause is in the camera.** Removing a direction cannot show the car what a black patch hid. If the axis clears the rule, the plan reads this direction. That does not make the direction a cause of the failure.
- **The clean twin has no patch.** A difference between failing frames and their twins may come from the patch and not from failing. The 13 slice rollouts that kept the patch and did not fail (measured) are not replayed.
- **A null is weak.** H17 edits one layer. Layers 11 onward can read the same fact again from the image tokens, and Step 4 found that no single middle layer is needed to drive (measured). So a result that does not clear does not show that the policy ignores the fact.
- **The edit may not silence the axis's latents.** The dictionary's encoder and decoder are separate parameters, so removing the decoder span does not guarantee that the axis's latents stop firing when the edited frame mean is re-encoded. H17 does not measure this. If they keep firing, that is one more explanation for a result where no clear shift is shown.
- **Random directions may mislead.** They point away from where activations usually lie, so an equal-size edit may move the plan more or less for reasons unrelated to the axis. Twenty non-failure latents are reported beside them for this reason.
- **Rounding sets a floor.** CUDA replays in bfloat16 (a 16-bit number format) sit a median 1 to 3 cm from the log on route waypoints and 6 cm on speed waypoints (measured, `docs/WHAT_BROKE.md` 2026-10-09). Replay against replay is exact, so these offsets set the scale of rounding and are not noise in the shift itself.
- **The frames show route markers.** Every frame has `--debug 2` markers in its camera (`docs/WHAT_BROKE.md`). Their effect is unmeasured.

## The axis

Read from `docs/research/data/h12_layer10_plain.json` (measured, dev data). **The best axis is chosen using the key.**

| Field | Value |
|---|---|
| Method and dictionary | M1 raw, `results/savio/h12/sae/L10_k32_s3` |
| Axis | `contrastive-a6` |
| Rollouts | 27, of which 24 are in P4's key of 46 and all 27 are pilot slices |
| Jaccard | 0.490, best of 18 dictionaries. The median is 0.387. |
| Claim A | Misses by 0.010, so this axis does not count as a recovery on this pool |

H3's 0.557 axis is not used. Its dictionary sat in a scratch folder on this Mac that no longer exists (checked), so H12's is the one that can be rebuilt.

The stored file names the axis and its counts but not its latents. `select` rebuilds the axis from H12's four shard folders and this dictionary with `ContrastiveConfig()`, and refuses to continue unless its size and its count in the key match the stored file.

## The frames

| Part | Definition | Size |
|---|---|---|
| Pool | P4-confirm, array 40716226 (`results/savio/step5-confirm-p4/summary.json`) | 120 routes, 118 with an outcome (measured) |
| Pairs | A failing P4 slice whose same-base neighbourhood rollout did not fail. `select` refuses if the count differs from `efficacy.json`. | 37 (measured from `efficacy.json`, and recomputed from `routes.jsonl` and the manifest) |
| Failing frames | Saved inputs (every 10th step) inside contrastive's own window, the 3 s before first infraction | Up to 6 per rollout (read from the code) |
| Control frames | For each failing frame, the twin's saved input at the nearest ego position, within 5 m, one copy of each. A pair with no match is dropped. | Up to 6 per rollout |

So at most 444 frames (estimate). Pairs run in a seeded order, so a job cut short leaves whole pairs chosen without regard to outcome. These frames are in the pool the axis was read from. The axis was chosen on which rollouts it holds and never on waypoints, so this is in-sample but not selected on the outcome.

## The edit

Each edit acts on the 30 driving-query tokens at the output of decoder layer 10, the site the axis was read from, in bfloat16 as logged. Q is an orthonormal basis of the axis's decoder columns. The columns are centred first, because the SAE's inputs are centred.

| Condition | Count | Edit to each token y | Purpose |
|---|---:|---|---|
| none | 1 | Nothing | Must give zero shift |
| zero | 1 | y' = 0 | Must give a large shift, which shows the path is live |
| axis | 1 | y' = y − QQᵀy | The test. With one latent this is PRD 12.2's y − (yᵀv)v |
| founder | 1 | The same, on the founding latent alone | Reported only. Step 9 has to choose between span and founder |
| random | 100 | y' = y − ‖Qᵀy‖ r, for a fixed random unit vector r | The controls in the rule |
| latent | 20 | The same, with r a non-failure latent's decoder column | PRD 9.2's other control, reported beside the rule |

**Equal norm means an equal edit on each token.** Plain removal along a random unit vector has the same vector norm, but in 896 dimensions it removes almost nothing, so any real direction would beat it. Giving the control the axis's own edit length, frame by frame, also means a frame where the axis projects strongly gets a strong control.

**Equal per token is not equal on the frame mean.** A control pushes all 30 tokens along one r, so its frame-mean edit equals its per-token edit. The axis's edit differs by token and partly cancels, so its frame-mean edit is at most its per-token edit (read from the code). The axis was read on frame means, so `effects.npz` holds a fourth column with each condition's frame-mean edit length, and `result.json` reports axis against random per arm. If the plan reads the frame mean, this bias makes the axis harder to show above random. A control that keeps token dependence, such as y' = y − ‖Qᵀy‖ (RRᵀy)/‖Rᵀy‖ with R a random basis of the same rank, was not chosen and the lock keeps the chosen control.

Non-failure latents are drawn with seed 17 from latents with support of at least 20 failing rollouts that do not pass contrastive's test (q below 0.05 and a positive effect).

## The measure

For each frame and condition, as Step 4 Part B does, the mean distance between intact and edited route waypoints and speed waypoints, in metres. Values are averaged within each rollout first, so one value per route enters the rule.

## Checks

If any check fails the run is **untested** and no shift is read. All but the first are evaluated after 25 frames, and a failure there stops the job.

| Check | Limit | Basis |
|---|---|---|
| Whole pairs read | At least 20 | Guess |
| Intact rerun, 90th percentile | At most 1 mm | Step 4 measured exactly 0 |
| Zeroed tokens, larger median of route and speed | At least 0.1 m | Guess. The wiring check below gave 0.9 to 7.8 m |
| Live frame mean against the shard's, median relative error | At most 2% | Guess, and unmeasured on the A40. On one local float32 capture the next logged frame differs by 4.8%, layers 9 and 11 by 34 to 35%, and bfloat16 rounding by 0.16% (measured). CUDA bfloat16 replay is known to miss the live log, with every layer mean different, at a size the repo does not record (`docs/WHAT_BROKE.md` 2026-10-09) |
| Each random direction's mean edit against the axis's | Within 10% | Read after rounding to bfloat16, which can erase small edits |

A failure of the site-error check after 25 frames stops the job, costs about 15 minutes (estimate), and leaves `effects.npz` holding the measured errors. H17 is then untested. Those errors are the first A40 measurement, so the limit may be changed only by a dated amendment here before a rerun, and only if the median stays under the 4.8% neighbouring-frame gap (measured on the Mac, so recheck it on the A40 shards).

## The rule, fixed before any result

For one outcome (route or speed), let A be the axis's mean shift over routes on failing frames, and T the 95th percentile, across the 100 random directions, of each direction's mean shift over the same routes. **Excess** is A − T, PRD 9.2's line against random directions only. PRD 9.2 also names non-failure latents as controls in that line. H17 reports them beside the rule, and its random control is an equal-length translation and not a removal along a random direction. **Difference** is the excess on failing frames minus the excess on control frames.

The interval comes from 5000 bootstrap draws of base routes, seed 17, with T recomputed in every draw and the same draw applied to both arms. Two outcomes are read, so each interval runs from 1.25% to 98.75%.

- An outcome **clears** when A is at least its floor and the excess interval's lower bound is above 0. The floor is the median replay-to-log offset: 3 cm on route (the top of the 1 to 3 cm range) and 6 cm on speed (measured, `docs/WHAT_BROKE.md` 2026-10-09).
- An outcome **is specific** when it clears and the difference interval's lower bound is above 0.

| Result | Condition | Fixed sentence |
|---|---|---|
| `untested` | A check failed | "H17 is untested: a check failed, so no shift is read." |
| `not_shown_above_random` | No outcome clears | "In replay, H17 could not show that removing the axis moves the plan more than random edits of equal size." |
| `above_random_failing_not_shown_larger` | An outcome clears and none is specific | "In replay, removing the axis moves the plan more than random edits of equal size. H17 could not show that it moves the plan more on failing frames than on their clean twins." |
| `above_random_larger_on_failing` | An outcome is specific | "In replay, removing the axis moves the plan more than random edits of equal size, and more on failing frames than on their clean twins." |

A `not_shown_above_random` reading also states, for each outcome, which gate stopped it (floor or interval), with A, the floor, T and the interval. An axis well above random with a wide interval and an axis inside the controls get the same label, and these numbers tell them apart. Neither is evidence that the plan ignores the axis.

If an above-random result has no clearing outcome whose A also beats the non-failure latents' 95th percentile, the report adds: "Its mean shift does not exceed the 95th percentile of other latents of the same dictionary at that size."

No result may be written as `causal` or `correlational_only`, the words Step 9 uses, and the report carries the label "Dev rehearsal in offline replay. Not Step 9's verdict." Reported beside the rule, with no bearing on it: the founder's shift, the axis's edit length per arm, the frame-mean edit lengths, and failing-frame shift for pairs whose rollout is or is not in the axis.

`selection.json` and `result.json` record the commit and the SHA-256 hashes of `causal_replay.py` and this file. `result.json` also holds every constant of the rule and flags any change between `select` and `report`. The sbatch prints `git rev-parse HEAD` to its log. Code and protocol must be committed together before submitting.

## Cost

The cap is **142 SU**. One A40 job at about 29 SU per hour.

| Item | Figure | Tag |
|---|---|---|
| Rate | 0.129 s per forward pass: 8232.2 s for 848 frames at 75 passes each, Step 4 Part B (`docs/steps/04-layer-site-ablation.md`, `docs/steps/04-ablation/partB-summary.json`) | Measured, before the disk slowed |
| Passes | 444 frames at 125 passes each, 55,500 | Estimate, an upper bound on frames |
| Replay | 2.0 hours, 58 SU | Estimate |
| Unpacking, loading, rebuilding the axis | 30 minutes, 15 SU | Guess |
| Expected total | About 73 SU | Estimate |
| Hard limit | The sbatch's 4 h 30 limit, about 131 SU | Estimate. The time limit enforces the cap |

If the disk doubles the rate, the limit cuts the job short and `report` reads the whole pairs done. About 4700 of 10000 SU remain, as given when this was drafted and not rechecked.

## Local checks already run

- `tests/test_causal_replay.py`: edits, pairing, windows, rule and labels, on toy inputs. 33 pass (measured).
- Wiring on the real SimLingo model (measured, 2 frames of `results/replay-bf16/0-route-26956`, float32 on the Mac's GPU as those frames were logged, with toy random directions as the "axis"). The live mean matched layer 10's log to 4e-8, `none` gave 0, `zero` gave 0.86 and 2.29 m on route and 2.8 and 7.8 m on speed, and the axis and random edits had equal lengths. These numbers describe the wiring only.
- **Not run locally:** the frame-mean column on the real model (the wiring check above predates it, and the toy hook test covers it), and bfloat16 on CUDA. A bfloat16 forward pass on the Mac's CPU takes 430 s (measured, stored `replay-cpu-bfloat16.json`). The first 25 frames on Savio are the first test of that path, and the early stop limits a failure to about 15 minutes (estimate).

## Before submitting

**Two things only the lead can do.** `docs/research/data/h12_layer10_plain.json` is git-ignored (`.gitignore:25`, checked) and `--stored` needs it on Savio, where code arrives by `git merge --ff-only`. So the commit must include `git add -f docs/research/data/h12_layer10_plain.json`. `tests/test_causal_replay.py` also reads it. `results/savio/h12/plain.json` may hold the same record, but that file is not on this Mac, so its method key is unconfirmed. Second, H17's excess differs from PRD 9.2's line as described in the rule, so the lead adds a short `CONFLICTS.md` note or states why a dev rehearsal needs none.

The axis's dictionary and P4-confirm's saved inputs are on Savio only, so nothing local can confirm them. A person must log in first, as `CLAUDE.md` describes. Then the lead runs this exact check.

```bash
ssh savio 'cd /global/scratch/users/imhaohao/HondaResearchInstitute && \
  ls -l docs/research/data/h12_layer10_plain.json results/savio/h12/sae/L10_k32_s3/sae.pt \
    results/savio/step5-confirm-p4/efficacy.json && \
  for d in step5-background-wave3 step5-confirm-p4 step5-confirm-p7 step5-pilot-p19-main; do \
    echo "$d $(ls results/savio/$d/shards/*.json | wc -l)"; done && \
  grep -m1 "\"source\"" results/savio/step5-confirm-p4/shards/212735.json && \
  n=0; for d in results/savio/40716226/route-*; do \
    [ -n "$(ls -A "$d/capture/inputs" 2>/dev/null)" ] && n=$((n+1)); done; echo "routes with inputs: $n" && \
  tar -tf /global/scratch/users/imhaohao/policy-venv.tar | grep -m1 "sklearn/__init__.py"'
```

Expect the stored axis file and `sae.pt` to exist, each shard folder to be non-empty, `source` to name `results/savio/40716226/route-212735`, about 120 routes with inputs, and the tar to hold scikit-learn, which `select` imports.

- **Inputs missing:** H17 is untested, so do not submit. Wave 3 (40715498) has inputs but no P4 frames. P4's first pilot (array 39921545) ran in mid-October, and shards from before 2026-10-19 have no ego position (read from `src/harness/failure_time.py`), so its twins could not be matched by position. Using it needs an amendment here first.
- **Dictionary missing:** H17 is untested. Retraining changes the dictionary, so it would be a different axis.

## Commands

The code must be on Savio first: `git fetch origin main && git merge --ff-only origin/main` (Savio's checkout tracks another branch, `docs/WHAT_BROKE.md`).

```bash
POLICY_VENV_LOCAL_TAR=/global/scratch/users/imhaohao/policy-venv.tar \
  bash scripts/submit.sh gpu_a40 docs/research/experiments/h17-causal-rehearsal/run.sbatch
```

Output goes to `results/savio/h17-causal-rehearsal/`: `selection.json`, `directions.pt`, `effects.npz` and `result.json`. If `select` refuses, the job ends within minutes and H17 is untested until the reason is understood. `select` does not read any P20 folder.

## What Step 9 still needs

Steering on success frames, every top axis and not one, a test pool, closed-loop runs with more than 40 routes per arm (Step 4's advice), a choice between span and founder, and a decision on how to write the card's `causal` block. H17 supplies none of these.

## Predictions (guesses)

A check fails or `select` refuses, 20%. `not_shown_above_random`, 40%. `above_random_failing_not_shown_larger`, 25%. `above_random_larger_on_failing`, 15%. The speed outcome moves more than the route outcome, 85%, as in Step 4.

## Result, 2026-11-04

Job 40906512, 49 SU (measured). `above_random_failing_not_shown_larger`, with the added sentence on other latents. `docs/research/data/h17_result.json`, read in `docs/research/dev-report.md`. Dev rehearsal in offline replay. Not Step 9's verdict. The control departs from PRD 9.2's line as stated in "The rule": a dev rehearsal decides nothing, so it needs no `CONFLICTS.md` entry. Step 9 must settle that control itself.
