# H16: B7 variant A, the rollout-free statistics

**Draft, lead locks before submitting.** Dev only (PRD §9.2). Nothing has been scored and no job has run. A local test of the input path wrote 195 training frames' means to a scratchpad; only their shape and finiteness were read, and they were then deleted. Every B7 number stored so far is variant B, "B7-pool". This protocol runs variant A, which `docs/steps/b7-gap-signal.md` says is B7 and is what Step 6's stop condition is about. It does not edit that spec's frozen sections, and it adds no gap candidate and no new signal. It does add readings the spec's stop sentence does not have: see "Departures from the spec" under the rule.

## Decision needed before any job runs

**B7-pool already reads T2 `fires` under this rule, on stored data, before any H16 job.** The real `gap_reading` and `stop_condition` on `docs/research/data/h12_layer10_plain.json` give these numbers (measured):

| Gap | B7-pool best / median | B7-pool recovers | M1 best / median | Reading |
|---|---|---|---|---|
| P19 | 0.500 / 0.372 | 1 of 18 dictionaries | 0.705 / 0.375 | `matches`, whichever way Claim B goes, because the median margin is 0.003 |
| P4 | 0.091 / 0.037 | 0 of 18 | 0.490 / 0.387 | `no_recovery` |
| P7 | 0.339 / 0.065 | 0 of 18 | 0.275 / 0.231 | `no_recovery`, with B7-pool above M1 |

The rule says any class firing under either variant is enough to stop, so its stop outcome is already set unless `score.py` fails to reproduce these numbers. The 340 to 420 SU (estimate) can only add variant A's reading to it. `tests/test_h16_variant_a.py` pins this result.

The firing depends on three unsettled things: a Jaccard of exactly 0.5 on one dictionary, the median clause from C34 (pending Chris's review), and P19's T2 label (Chris's decision is pending). P19 also fails Step 5's single-factor condition.

**Jerry and Chris decide, before step 1 of the Order:** does this stop Step 8 now, and is variant A still worth its SU? Nobody has decided either. After the jobs run, this reading is not a new H16 finding.

## Question

Do statistics of SimLingo's activations on its own training frames point at the planted gaps as well as our methods do? `PRD.md` §13, Step 6: if they do, stop and re-plan before building the rollout corpus.

## Episodes

| Item | Value | Tag |
|---|---|---|
| Route list | `configs/baselines/b7_training_routes_v1.txt`, 1,000 route directories from 6 of the 37 training chunks | committed 2026-10-15 |
| Chunk draw | `random.Random(0).sample` over the sorted 37 names gives the same 6 | measured 2026-11-04 |
| Source | `datasets/RenzKa/simlingo` at revision `796abab62acaddb6183d0d01c9b43a622c5c58c8` | read from the HF API |
| Frames | every `rgb/*.jpg` with its `measurements/*.json.gz`; a route that does not pair up is lost whole, with no replacement | "every frame" is spec step 2; losing the whole route is our reading |
| Rate | stored frames at 4 Hz (one per 5 ticks at 20 Hz); pool shards keep every 5th step, so also 4 Hz | read from code |

**Readings the spec is silent on, for Chris to confirm.** `rgb_augmented/` is not used, because that camera is shifted for training augmentation and the policy never drives from it. Routes are not filtered by the training loader's quality rules, because the spec says every frame they store.

Three gates in this file are not in the spec. They were chosen before any training activation was read, and each can turn a reading into `untested`, which is not a stop:

- A dictionary must reach explained variance 0.8 on training frames to count for variant A. H1's token-trained dictionaries scored about -0.5 on frame means (dev report), and the guess under Predictions gives about 20% against reaching this.
- Variant A needs at least 950 routes and 9 dictionaries.
- A route that does not pair up is lost whole. The spec says only "every frame they store".

## Input path

`capture_training.py` feeds each stored JPEG through the agent's crop and tiling, with the prompt built from the frame's stored speed and two target points. It stores the layer-10 driving-query mean in float16, which is what a rollout shard stores for that site.

Checked on the Mac (measured, float32 on MPS, route 26956 and the first route of the smallest chunk):

- Rebuilt inputs equal the agent's saved inputs exactly on 8 of 8 frames: image tiles, token ids, target points, speed, intrinsics, extrinsics.
- Stopping inside layer 10 equals a full forward pass exactly on 8 of 8 frames, and matches the logged mean to a relative error of 7e-8.
- On 8 training frames the route head sits 0.01 to 0.06 m from the stored route. Flipping the target points' sign moves a bend frame to 6.2 m, and leaves straight frames at about 0.03 m, so this check catches wrong inputs only on bends.

## Dictionaries

**All 18 of H12's: `results/savio/h12/sae/L10_k{32,48,64}_s{0..5}`.** Layer 10, `driving_queries` frame means, not residualized.

- Spec step 1 forbids B7 its own dictionary: it must read the same latents as the SAE method. H12 is the newest locked run of that method, and its pool is the only one holding P19.
- C34 requires best and median across dictionaries, and H12 is why (M1 on P19: best 0.705, median 0.375, measured). So no single dictionary is chosen, which also means none can be chosen to suit B7.
- H12's M1 and B7-pool numbers are stored (`docs/research/data/h12_layer10_plain.json`). `score.py` recomputes them and writes `reproduces_stored`. `read_rule.py` refuses to write a reading if nothing was compared or the worst difference is over 0.01 (guess), and that refusal stops the Order.

A dictionary counts for M1 and B7-pool when its explained variance on the pool is at least 0.8, as in `dev_eval.py`. For variant A it must also reach 0.8 on the training frames. When variant A reads `untested`, `stop-condition.json` gives each dictionary's training explained variance and the routes read.

## Pool and gaps

Variant A takes its statistics from training frames. Merging (spec step 7) and members (step 8) still read a test pool, here H12's 536 rollouts (229 failures, measured).

| Gap | Class (tier in the gap files) | Pool |
|---|---|---|
| P4 | T0 control | H12's |
| P7 | T0 control | H12's |
| P19 | T2 interactional | H12's |
| P8 | T0 control | H12's plus `step5-pilot-p8-main`, 120 rollouts, ids disjoint (checked) |

H12's dictionaries never saw P8's frames, and M1 and B7 both carry that handicap on P8. H1b's dictionaries saw them, but `h1b_layer10.json` records them under a Mac scratchpad path and that folder is gone from this Mac (checked), so they are not used. P20 is not read: `score.sbatch` names its folders and never globs.

## Frozen-input signal

H2's stale-frame latent stays **post hoc**. It was designed after H2's diagnostic had opened P7's activations, and it is not in the frozen spec. `score.py --stale-latent` runs it for P7 and writes `post-hoc-frozen-input.json`, labelled post hoc and holding no stop-rule evidence. `read_rule.py` refuses that file. It can neither fire nor clear the condition, and the report shows it beside the plain reading, never inside it. Training frames with a stopped car may switch this latent on often, so its variant A reading may differ from H3's 0.889 for reasons unrelated to P7.

## The rule

The rule is applied to both variants, because the spec fires on either, and the two arms have different standing:

- **Variant A: stated before its data.** No variant A number exists yet. The rule is fixed only once it is locked (Order, step 2).
- **B7-pool: post hoc.** The B7-pool numbers already exist and the author of this rule had seen their table in `docs/research/dev-report.md`, so every choice below was made after those activations were opened. The spec says such a change is labelled post hoc wherever B7 is reported.

`read_rule.py` writes these labels, the unsettled decisions and the lock commit into `stop-condition.json`, so they travel with the result.

**Departures from the spec.** The spec and PRD Step 6 have one condition: either variant recovers the practice gaps as well as our methods do. This rule adds a split by gap class, an all-gaps-in-class test, a `partial` reading that does not stop, a `no_recovery` class reading, the median margin, and Claim B with B7 as the only rival. Chris confirms the class split and `partial`.

For each gap and variant, over the dictionaries that count, on plain latents only. "Our methods" means M1 raw and capped, taking the better of the two per dictionary. M2 is not rerun, because it scores 0 on every gap in H1b, H3 and H12 (measured).

| Term | Test |
|---|---|
| B7 recovers | a dictionary gives B7 an axis with Jaccard ≥ 0.5 holding at most 50% of failures (Claim A's test) |
| Our methods stay ahead | Claim B's test with this B7 variant as the only rival: best margin ≥ 0.15, over the catch-all too, base-route bootstrap interval above 0, at least 4 of 6 seeds, not a catch-all; **and** median margin ≥ 0.15 |

The median margin is there because C34 says a best score picks its axis using the key, and a user without a key gets something nearer the median.

| Gap reading | When |
|---|---|
| `matches` | B7 recovers, and our methods do not stay ahead |
| `below` | B7 does not recover and our methods do, or B7 recovers and our methods stay ahead |
| `no_recovery` | neither recovers |

| Class reading | When | What follows |
|---|---|---|
| `fires` | every gap of the class is `matches` | Step 8's rollout corpus waits until Jerry and Chris have re-planned |
| `partial` | some are | Reported gap by gap. No stop |
| `no_recovery` | every gap of the class is `no_recovery` | Not a clear: the rule has no evidence either way. No stop |
| `clear` | none is `matches`, and at least one is `below` | No stop. A gap that reads `no_recovery` is named, and the clear does not cover it |
| `untested` | floors not met | Not a clear. Jerry and Chris decide |

**Floors for variant A:** at least 950 of 1,000 routes captured and at least 9 of 18 dictionaries counting. Below either, variant A is `untested`.

**A score under 0.5 cannot fire this rule.** `below` has no margin test when B7 does not recover, so 0.49 against 0.50 reads `below`, and B7 can outscore our methods and still read `no_recovery`. On H12's P7, B7-pool scores 0.339 against M1's 0.275 (measured), and on H1b's P8, 0.444 against 0.276 (dev report). So `stop-condition.json` gives B7's and our methods' best and median beside every reading.

Any class firing under either variant is enough to stop. Coded in `src/baselines/b7_variant_a.py`, tested in `tests/test_h16_variant_a.py`.

**Stopwatch audit.** The output gives the best N longest failing rollouts per gap, as in H3. H3 did not count a recovery near that number. Here it annotates the reading and does not change it, so that an escape clause cannot quiet a stop.

### Wording, by outcome

No branch of PRD 13.1 is claimed under any of these (C34). Best and median go beside every number, with "the best axis is chosen using the key".

- **T0 `fires`:** "B7 variant A recovers the camera-fault gaps as well as our methods do, on dev data."
- **T2 `fires`:** "B7 variant A matches our methods on P19, on dev data. P19 passes 9.1 and fails Step 5's single-factor condition, so this says nothing about interactional gaps that meet Step 5, of which there are none."
- **B7-pool T2 `fires`, the reading already set on stored data:** "On numbers stored from H12, before any H16 job, B7-pool reads `fires` on P19, under a rule written after its author had seen those numbers. B7-pool recovers P19 on 1 of 18 dictionaries, at Jaccard 0.5, and M1's median lead is 0.003. This depends on C34's median clause and P19's T2 label, both unsettled. P19 fails Step 5's single-factor condition, so this says nothing about interactional gaps that meet Step 5, of which there are none."
- **T2 `clear`:** the same caveat, with "B7 variant A falls below our methods on P19". It does not show that rollouts are justified for interactional gaps in general.
- **`clear`, every class:** "B7 variant A does not match our methods on the public gaps [named, those reading `below`]", plus the first weakness below.
- **`no_recovery`, gap or class:** "Neither B7 nor our methods reach Jaccard 0.5 on this gap, so the rule has no reading here", with the scores. If B7 scores higher, add "B7 scores above our methods here".
- **`below` with B7 under 0.5:** "B7 does not reach Jaccard 0.5 on this gap and our methods do", with the scores. It is not a claim about the size of the lead.

## Known weaknesses, stated before the data

1. **Variant A is rollout-free only in its ranking.** The dictionaries were fitted on the pool, which holds the planted frames, and merging and members read the pool. The spec requires this. A win means "training-frame statistics rank these latents well", not "this needs no rollouts". A dictionary fitted on training frames alone would be a change to spec step 1 and would need Chris; it is not run here.
2. **A planted gap is absent from training data under Mode B.** A latent that exists for that gap may fire in under 3 training episodes and be dropped at step 5. That is a large part of why this may read `below` (guess), and it is why the spec also runs B7-pool.
3. **Route markers.** Pool frames carry them and training frames probably do not (C35, `docs/WHAT_BROKE.md`). A latent reading markers would look absent on training frames.
4. **Chunk clustering.** 166 of the routes (17%) come from one scenario family, as the spec already records.
5. **One interactional gap.** T2's reading rests on P19 alone.

## Predictions (guesses)

These cover variant A only, because the B7-pool reading is already known. Variant A's best Jaccard stays under 0.5 on P4, about 80%; on P7, about 85%; on P19, about 65%. No class fires for variant A, about 75%. Training-frame explained variance reaches 0.8 on at least 9 dictionaries, about 80%.

## Scale

| Quantity | Earlier figure | This file's figure | Tag |
|---|---|---|---|
| Download | about 107 GB, derived here as 1,158 GB × 6/65 (not in the spec) | **86.86 GB** | measured from the HF API; the 6 chunks were drawn from the 37 training chunks, and these are smaller than average |
| Frames | about 200,000 (spec step 2) | **about 300,000**, range 250,000 to 350,000 | estimate from the first 80 MB of 3 chunks; first routes hold 35 to 553 frames |
| GPU hours | "a few GPU-hours" (spec step 2); about 8 at this file's earlier rate | **about 8 to 11** | estimate: 0.13 s a forward pass (journal, A40 shared with other routes), times the frames, less 14 to 23% for stopping early (measured in two noisy Mac runs on MPS; unmeasured on A40, and the check job reads it) |

### What reduces it without touching the spec

Built in:

- **Stream, filter, delete.** Each task pipes its chunk through `tar` straight to node-local disk, keeping only `rgb/` and `measurements/`. The 86.86 GB never sit on disk. Peak on `/tmp` is about 10 GB per task (estimate), and the job refuses to start under 30 GB free. That check runs once, so two tasks on one node can both pass it. A full disk then fails the task through `pipefail`, which is safe but wastes billed time.
- **Keep one layer.** Scratch ends with about 0.5 GB of float16 means (300,000 × 896 × 2 bytes, estimate), and any dictionary can be re-read from them with no GPU.
- **Stop inside layer 10.** Nothing later can change that layer's output, and the check job proves equality on real frames.
- **Parallel preparation.** Loader workers on the 8 CPUs handle JPEG decoding and tiling, so the GPU does not wait on them (0.05 s a frame, journal).
- **Node-local Python.** `POLICY_VENV_LOCAL_TAR` avoids scratch's slow metadata (20 ms a lookup, measured).

Not built: batching frames. It should not change the spec, but the model's driving-query slots and padding assume batch 1, and SU is not binding here.

**Needs Chris's sign-off, so kept as written:** N below 1,000, fewer chunks, or striding frames. Each changes what the spec signed off on 2026-10-16. The unplanted background array 40715498 is also no substitute: those are the policy's own rollouts, not training data, so statistics on them are B7-pool. It serves only as the input check's reference.

### SU, disk and the cap

| Job | Limit | Hard cap | Expected (estimate) |
|---|---|---|---|
| `capture.sbatch check` | 0:30 on one A40 | 15 SU | 5 to 10 SU |
| `capture.sbatch capture`, array `0-5%2` | 3:30 per task | 609 SU | 300 to 350 SU |
| `score.sbatch` | 2:00 on one A40 | 58 SU | 30 to 58 SU; H12's whole job cost about 16 SU (from the spend figures in `docs/STATUS.md`) |
| **Total** | | **682 SU** | **about 340 to 420 SU** |

**Recheck the balance on Savio before step 1.** The earlier figure of about 4,700 SU left predates Chris's figure of about 6,000 SU on sealed work (issue #8). Both users share one allowance in `configs/cluster/savio.yaml`, and whether Jerry's 10,000 budget includes Chris's spend is unresolved (guess).

A40 at about 29 SU an hour. Finished routes are never redone, so a task that hits its limit is resubmitted by index. **The capture stops at 609 SU in all, resubmissions included.** Past that, the lead asks Jerry before spending more; routes not yet captured then count against the 950 floor.

`job_guard.py` enforces this at the start of every job and refuses:

- a job name other than the mode's (`h16-check`, `h16-capture`, `h16-score`), since the ledger counts by name;
- a time limit over the table's. Each sbatch file also carries a default limit, and capture's default is 0:30, so a forgotten `--time` fails short;
- `sacct` totals over the hard cap, counting a finished job's elapsed time and a running job's whole limit. This can refuse with SU left, and a shorter `--time` then fits. A second `score` or `check` run is refused after almost any first run. Past a cap, the lead raises it in `job_guard.py` only after Jerry says yes;
- `results/savio/h16/training` over 2 GB (guess, four times the 0.5 GB estimate). This is read at job start, so a task can pass it once and then add its own output.

Limits on this guard: the ledger sees only the submitting user's jobs, and no job bounds `/tmp` after its first check.

## Order

Stop if a step fails, and tell Jerry. Nothing here runs until Jerry and Chris have answered the decision at the top of this file and the SU balance is rechecked.

1. `POLICY_VENV_LOCAL_TAR=/global/scratch/users/imhaohao/policy-venv.tar bash scripts/submit.sh gpu_a40 --time=0-00:30:00 --job-name=h16-check docs/research/experiments/h16-b7-rollout-free/capture.sbatch check`
   Gates, on rollouts of array 40715498 and one training route, in bfloat16 on an A40: inputs equal exactly; early stop equals full; relative mean error at most 1e-2 (guess, 7e-8 on the Mac in float32, where the rollout's own dtype was float32 too); worst route-head error at most 1.0 m (guess, from the figures above); and at least one checked frame whose stored route goes 2 m or more sideways within 20 m (guess), since the route head tests nothing without a bend. The check adds the sharpest frame among the routes on disk. It also proves a compute node can reach Hugging Face. If it cannot, the six tars go to scratch from a login node and `CHUNK_DIR` points at them, which adds 87 GB on scratch until step 6 deletes them.
2. The lead reads `results/savio/h16/check.json`, then locks the rule. The lock is the commit of `protocol.md`, `read_rule.py`, `score.py` and `src/baselines/b7_variant_a.py`. Write that commit's hash to `rule-lock.txt` here and commit that file too, because this file cannot hold its own commit's hash. `score.sbatch` and `read_rule.py` refuse to run without the lock, or if git shows any of those four files differing from it, and the hash goes into `stop-condition.json`. `score.py` is locked beside the three other files because it computes what the rule reads. Savio's checkout tracks another branch, so merge the lock there first (`docs/WHAT_BROKE.md`).
3. `POLICY_VENV_LOCAL_TAR=/global/scratch/users/imhaohao/policy-venv.tar bash scripts/submit.sh gpu_a40 --time=0-03:30:00 --array=0-5%2 docs/research/experiments/h16-b7-rollout-free/capture.sbatch capture`
4. `POLICY_VENV_LOCAL_TAR=/global/scratch/users/imhaohao/policy-venv.tar bash scripts/submit.sh gpu_a40 --time=0-02:00:00 --dependency=afterok:<array> docs/research/experiments/h16-b7-rollout-free/score.sbatch`
5. Read `results/savio/h16/stop-condition.json` first, then `plain.json`, `plain-p8.json`, and last `post-hoc-frozen-input.json`.
6. If `CHUNK_DIR` was used, the lead deletes it once `stop-condition.json` exists: `rm -rf "$CHUNK_DIR"`. No job does this.

## Guard

`tests/test_b7_signal_frozen.py` fails if the signal moves: the spec's frozen sections and the route list by hash, the parameters, golden scores and axes that also reproduce on the code as signed off (`f1dd409`), and an independent reading of the spec's formula. Mutating τ_on, a κ weight, the hysteresis, the run-length term, the onset term, the ceiling or the merge threshold each failed it (measured). The spec's Step 6 hash commit with the other baselines has not been made, and the lock in step 2 does not replace it.
