# Step 0 — Ground the facts

**Owner:** both. Split as marked.
**Blocks:** Step 1, and therefore everything.
**Why this is a step and not a chore:** the plan currently rests on numbers
nobody on this team has read out of a paper. Two of them (the SAE expansion ratio,
the motivating case study) would change what we build or what we claim. The rest
are cheap to confirm while we are in the papers anyway. Doing this first costs a
day and prevents building on sand.

Nothing here needs a GPU. Both tracks can run in parallel.

---

## Track A — Paper facts (Chris)

Four papers. For each item: confirm, correct, or strike, and write the page or
section where you found it. Edit `PRD.md` in place and strike the unverified
blocks as they resolve.

### A1 · Dr. VLA — `arXiv 2603.19183`

Code was announced for release 1 Oct 2026 at `github.com/swannaiden/drvla`;
check whether it landed, since it would save us the SAE stack and the
memorization filter.

**The one that matters:**

- [ ] **Expansion ratio.** `PRD.md` §12.2 / `CONFLICTS.md` D1. The brief says
      ratio 1, claiming larger ratios give more dead features at robotics scale
      with no interpretability gain. The handoff says 8×–32×. Find what the paper
      actually used and whether that finding exists. **If the brief is right, the
      warning not to "fix" it stands and we use ratio 1.** Write the answer into
      §12.2 and close §16.1.

Also confirm, lower stakes:

- [ ] `k` and how it scales with `d` (brief: k=100 at d=2048 → we are at d=896).
- [ ] Optimizer, lr, batch, epochs, pre-bias method, dead-latent threshold.
- [ ] Number of seeds (brief says six).
- [ ] The generality / memorization metric: what the components are and how they
      are combined. We need this twice — as a filter in §9.2 and as baseline B7.
- [ ] Describability protocol as actually run, and the interpretable fraction
      against the neuron baseline (brief: 79.2% vs 30%, over 120 sampled).
- [ ] The ablation result (brief: removing top general features → 0/40 success).
- [ ] Mean-pooling over tokens, and their report that per-token was less
      interpretable.

### A2 · Fail2Drive — `arXiv 2604.08535`, IROS 2026

- [ ] **The motivating case study.** `PRD.md` §3.2. Does the pedestrian-in-ego-lane
      result exist (brief: 98.50 → 19.68, collisions in 87% of episodes)? Is the
      mechanism — language-action module following a hallucinated vehicle-shaped
      lead actor — stated in the paper or was it inferred? **If it is not in the
      paper, the §3.2 unverified block gets struck and the aggregate framing
      stands.** Do not cite a mechanism the authors did not claim.
- [ ] SimLingo's in-distribution and generalization DS/SR/HM, and the four
      category figures (brief: Behavior −64.2%, Visual-lateral −32.2%,
      Visual-longitudinal −9.0%, Robustness −5.9%).
- [ ] The exact wording of the no-training rule, so `PRD.md` §4.7 quotes rather
      than paraphrases it.
- [ ] What the authoring toolbox actually exposes, and whether PDM-Lite ships
      usable as a standalone solvability checker.
- [ ] Their seed protocol.

### A3 · SimLingo — `arXiv 2503.09594`, CVPR 2025 · PDF is at `upstream-99p/papers/`

- [ ] Qwen2-0.5B layer count and hidden size, **from the loaded config, not the
      paper.** Everything in §12.1's storage arithmetic keys off `d = 896`.
- [ ] Where the waypoint query tokens are and what reads them — this is the
      action-bottleneck hook site in §9.2.
- [ ] LoRA r/α and which components are frozen (handoff: r=32, α=64, vision
      frozen, waypoint heads trainable).
- [ ] CoT-off vs CoT-on numbers (handoff: 84.41 ± 1.76 vs 85.07 ± 0.95, Table 10).
- [ ] Multi-ability success rates (handoff Table 8: Merging 54.0, Overtaking 57.0,
      Emergency Brake 88.3, Give Way 53.3, Traffic Sign 82.5) — these set the
      background failure rate our gaps must stand out against.
- [ ] The interestingness-bucket sampler: bucket names and weights, and confirm
      the audit's claim that withholding means filtering route directories rather
      than zeroing weights. Mode A only, but record it now while you are here.
- [ ] Training cost (handoff: 14 epochs, 8×A100-80GB, ~24h ≈ 190 A100-h) and the
      released config's batch size, which reportedly differs from the paper's.

### A4 · RoboART — `arXiv 2502.06575`, CoRL 2025

- [ ] The 12 conditions, and confirm they are levels of a few factors rather than
      12 independent factors. `PRD.md` §4.1 says so; it changes how we write B4's
      factor list.
- [ ] The anomaly detector: kNN in policy embedding space, k, and the conformal
      calibration.
- [ ] Spearman ρ and mean absolute prediction error, so our §10.2 metric matches
      theirs exactly.
- [ ] The co-finetuning recipe (handoff: 80/20 mixture, lr 5e-6, ~20K steps) and
      the 2–7× claim's exact scope.

### A5 · Event-grounded SAEs — `arXiv 2605.17204`

New since the brief, and the closest method precedent. Read enough to:

- [ ] State in one paragraph how we differ, for the related-work section.
- [ ] Extract their residual-preserving zero-out procedure — `PRD.md` §9.2 names
      it as the causal-check template.
- [ ] Check for released code.

---

## Track B — Savio access (Jerry primary, Chris confirms)

`PRD.md` §17. Chris's account is already registered under `ic_cdss170fall`.

- [ ] **Jerry: complete the per-user steps.** Sign the cluster access agreement on
      first login; join the project under "My BRC Cluster Projects" in MyBRC; set
      up one-time-password auth. Login is a PIN plus a 6-digit code. **This is not
      instant and it blocks Step 1.**
- [ ] Both: SSH to `hpc.brc.berkeley.edu` successfully.
- [ ] Both: submit one trivial GPU job — `nvidia-smi` in a batch script is enough
      — and get output back. This is the actual done-condition. Everything else in
      Step 1 assumes it.
- [ ] Record what GPU you landed on and under which partition.

### B2 · The four unknowns · ask, do not infer

Email the program contact at <https://datadisco.cdss.berkeley.edu/support>. Do
not infer these from general Research IT docs — allowance terms are set per
agreement, and we inherited cost estimates sized for different hardware.

Ask for:

1. GPU partition names available to `ic_cdss170fall`.
2. The Service Unit charging rate for GPU jobs on those partitions.
3. Maximum wall time.
4. Storage quota, and where large datasets should live. We need ~150 GB for
   activations at three layers, more if Mode A ever runs.

Also worth asking, since it shapes Step 4's fan-out: whether `savio_lowprio` is
available to an `ic_` allowance, and whether job arrays have a width cap.

**Send this today even if the papers take longer.** The reply time is outside our
control and §16.2 cannot close without it.

### B3 · Environment reconnaissance

- [ ] Does a CARLA 0.9.15 container exist on Savio, or do we build one? Check
      whether Singularity/Apptainer is the required runtime — most HPC sites
      disallow Docker.
- [ ] Can CARLA render off-screen on a Savio GPU node? The handoff flagged this as
      a live risk on NRP and it is the most likely Step 1 blocker.
- [ ] Where do the SimLingo checkpoint and dataset go, given the quota answer?
- [ ] Note the module system's CUDA and Python versions.

---

## Done condition

1. Every **unverified** flag in `PRD.md` is confirmed with a reference or struck.
2. `CONFLICTS.md` D1 is closed — the SAE expansion ratio has one answer.
3. Both of us have run a GPU job on Savio and know what hardware we got.
4. The support email is sent.
5. `docs/WHAT_BROKE.md` exists and has its first entry, even if the entry is
   "nothing broke yet."

## What we are explicitly not doing yet

No hooks, no SAE code, no gap predicates, no adapter interface. Step 1 is *one
route*, not the benchmark, and that is deliberate — the policy runs 15–20× slower
than real time and bring-up is the most likely place this project dies.

## Notes for whoever runs this

- If the Dr. VLA code did land on 1 Oct, say so loudly. It changes Step 7's scope
  from "build an SAE stack" to "configure one."
- If CARLA cannot render off-screen on Savio, stop and raise it. That is a
  replan, not a debugging session, and NRP becomes a serious option for rollouts
  rather than just the describability model.
- Log anything that surprises you in `docs/WHAT_BROKE.md` as you go. Reconstructing
  it later never works, and `PRD.md` §6 commits us to publishing it.
