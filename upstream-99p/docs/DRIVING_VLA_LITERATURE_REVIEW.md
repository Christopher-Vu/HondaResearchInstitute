# Driving VLAs, Action Tokenization and Closed-Loop Evaluation: A Verified Literature Review

> **What this is.** A corrected and verified version of the literature review *"Failure Axis Discovery and Architectural Paradigms in Autonomous Driving Vision-Language-Action (VLA) Models"*. The team received that review from a notebook tool. Most of it paraphrases **AutoVLA** (Zhou et al., NeurIPS 2025, arXiv:2506.13757; `zhou2025autovla`) and **Bench2Drive** (Jia et al., NeurIPS 2024 D&B; `jia2024bench2drive`).
> **Verification date:** 2026-09-28. Evidence per claim: [`CITATION_AUDIT.md`](CITATION_AUDIT.md).
> **How it is used:** [`MASTER_HANDOFF.md`](MASTER_HANDOFF.md) §7 turns this review into design decisions.
>
> **Legend:** [verified] · [corrected] (the source text was wrong or imprecise; the corrected value is shown) · [removed] (fabricated or unsupported) · [unverified] (plausible, not confirmed; do not quote without checking the PDF).

---

## 0. Summary of Corrections to the Source Review

| # | Source claim | Status | Correct statement |
| :-- | :-- | :-- | :-- |
| 1 | "Input images are resized to 28 × 28 × 128 pixels" | [corrected] | 28 × 28 × 128 = 100,352 is a **total pixel budget per frame** (Qwen2.5-VL `min_pixels = max_pixels`), not an image size. Aspect ratio is kept, and each 28 × 28-pixel block becomes one visual token, so ≈ 128 tokens per frame slice. The released configs use 28 × 28 × 140. |
| 2 | An "Adaptive Router" chooses fast or slow thinking | [removed] | There is no router module. The single model picks its mode through the first text it generates ("This is a straightforward scenario…" vs "This is a complex scenario…"). Both modes share one system prompt. |
| 3 | Ego input includes "historical coordinate trajectories" | [corrected] | The released prompt contains only scalar speed, scalar acceleration magnitude and a driving command. History is visual only (4 frames). |
| 4 | GRPO with clipping ε = 0.2 and group size G = 6 | [corrected] | The paper does **one policy update per step "without the need for clipping"** and gives no value for ε. Group sizes 2 / 4 / 8 are compared in Fig. 5(b), and 8 gives the highest reward. In the released code G = number of GPUs (default 2). β = 0.04 [verified]. |
| 5 | RFT runtime "10.518 s → 3.49 s (−66.8%)" | [corrected] | **3.95 s → 1.31 s (−66.8%)**; PDMS 80.54 → 89.11 (+10.6%). 10.518 s is the forced-slow-thinking *average*. "3.49 s" appears in no source; it is 10.518 × (1 − 0.668). |
| 6 | Data-scaling **table** (10k / 50k / 100k / 185k with PDMS 68.20 … 80.54) | [removed] | The paper has **no scaling table**, only Fig. 4. Only 2 of the 32 numbers match it. §4.2 gives the real values printed on the figure. |
| 7 | "50k inflection point" | [corrected] | On nuPlan, CoT supervision trails action-only at 50k and overtakes it by 100k, so the crossover is between 50k and 100k. On nuScenes, action-only is better at **every** scale. |
| 8 | AD-MLP open-loop L2 "0.70 m to 0.89 m" | [removed] | AD-MLP averages **0.29 m** L2 on nuScenes (ST-P3 metric; Zhai et al. 2023). Li et al.'s Ego-MLP averages 0.35 m. AD-MLP's open-loop L2 on Bench2Drive is 3.64 m. The 0.70 / 0.89 values are AutoVLA's own numbers. |
| 9 | "~75% of nuScenes frames are straight driving" | [corrected] | The primary figure is **73.9%** (Li et al., CVPR 2024). Bench2Drive rounds it to "approximately 75%". |
| 10 | "#1 overall on the Waymo Challenge Spotlight metric (6.9436)" | [corrected] | #1 on **RFS Spotlight** (6.9436), but **#5 on RFS Overall** (7.5566), the official ranking metric. The ablation table has no Spotlight column. |
| 11 | "Reducing runtime latency by 48.4%" (text waypoints vs action tokens) | [corrected] | This is arithmetic on v2 numbers, (7.65 − 3.95) / 7.65, not a quote. arXiv v1 reported 59.24 PDMS / 9.31 s for text waypoints. |
| 12 | Phase 5: "Verify DS ≥ 78, SR ≥ 57% … safety deployment criteria prior to onboard real-vehicle testing" | [removed] | These are simply AutoVLA's own Bench2Drive numbers (78.84 / 57.73). They come from a **separate CARLA-specific model** (single front camera, CARLA-Garage codebook, SFT only), and **no CARLA code is released**. They are not safety criteria, and the paper has no real-vehicle testing. |
| 13 | "2.0-second temporal history" | [corrected] (nuance) | The paper says "2 seconds of history". The four frames at 2 Hz actually span t − 1.5 s … t. |
| 14 | "MergeIntoSlowTraffic" | [corrected] | CARLA / Bench2Drive's class is **`MergerIntoSlowTraffic`** (sic). |
| 15 | "K-disk (Ours)" | [corrected] | "Ours" was copied from the AutoVLA paper. K-disk tokenization is **AutoVLA's**, not this project's. |

---

## 1. Architectural Foundations of Driving VLAs

End-to-end driving replaces modular perception → prediction → planning pipelines with a single learned mapping. This removes cascading interface errors, but it tends to be brittle in the long tail. Vision-Language-Action (VLA) models put a pretrained vision-language backbone inside the control loop.

The source review describes three ways such models **output actions**:

1. **Text waypoints:** numbers generated as language. This is slow and imprecise. AutoVLA's ablation (§3.2) confirms it performs worse and runs slower. [verified]
2. **Meta-actions** ("yield", "turn left"): these need a downstream planner, which breaks end-to-end gradient flow. [verified] (conceptual)
3. **Physical action tokens:** trajectory segments are discretized into the VLM's vocabulary. AutoVLA does this. [verified]

SimLingo, the primary policy for this project, uses a fourth pattern: **learned query tokens decoded by an MLP into waypoints** (`Renz2025cvpr`). It predicts 1 m-spaced **path** waypoints and 0.25 s-spaced **speed** waypoints in a single forward pass.

### 1.1 AutoVLA architecture and "dual thinking"

| Component | Verified description |
| :-- | :-- |
| Backbone | [verified] Qwen2.5-VL-3B (Instruct) |
| Cameras | [verified] 3 forward cameras (front, front-left, front-right), each passed as a 4-frame "video" at 2 Hz |
| Visual budget | [corrected] 28 × 28 × 128 = 100,352 px per frame (≈ 128 tokens per frame slice; temporal patch size 2 → ≈ 256 tokens per camera, ≈ 768 in total). Released configs use 28 × 28 × 140. |
| Ego and route input | [corrected] Scalar speed and scalar acceleration magnitude (3 decimals each), plus a lowercased driving command. No past trajectory. |
| Action output | [verified] 10 action tokens × 0.5 s = 5 s plan. Tokens `<action_0>` … `<action_2047>` are added to the vocabulary starting at id 151665. |
| Mode selection | [removed] "Adaptive Router". [verified] The **model itself** writes "This is a straightforward scenario…" (fast: straight to the action tokens) or "This is a complex scenario requiring additional reasoning…" (slow: chain of thought, then action tokens). |

**Runtime (AutoVLA Table 2 in a later arXiv version, v3 Nov 2025, "Runtime Analysis of Fast & Slow Thinking Modes"; in arXiv v1, Table 2 is the Bench2Drive table).** [verified] All six values appear in a student reproduction repo that cites the table, and an independent survey gives the same two averages. The primary text was not read. The GPU is unconfirmed: the survey says the table names no device, while the reproduction repo says A100.

| Mode | Min (s) | Max (s) | Avg (s) |
| :-- | --: | --: | --: |
| Fast thinking | 0.997 | 1.116 | 1.072 |
| Slow thinking | 7.607 | 13.706 | 10.518 |

One student reproduction on a V100 measured very different numbers. Latency depends on hardware and on CoT length, so **measure it on your own GPUs**.

**Release status (as of 2026-09-28).** [verified]
- Code (annotation, SFT, GRPO RFT) was released 2026-02; a merged checkpoint (HF `Zewei-Zhou/AutoVLA`) 2026-05.
- UCLA **Academic Software License**: non-commercial, no transfer of derivatives.
- The **CoT dataset is not released**.
- There is **no CARLA/Bench2Drive agent, data or checkpoint**.

**Open GitHub issues** report:
- a reproduction gap (83.69 vs 89.11 PDMS);
- the released checkpoint always picking fast mode;
- a teacher/student camera mismatch (the teacher saw 4 cameras, the student 3).

### 1.2 Physical action tokenization (K-disk)

[verified] **Tokens.** Trajectories are split into 0.5 s segments (Δx, Δy, Δθ).

[verified] **Codebook.** Built by **K-disk clustering** with **K = 2048** and an average-contour tolerance **δ = 0.05 m**, using a 4.8 m × 2.0 m box. The paper cites WOMD + CARLA-Garage data; the released script clusters nuPlan trajectories by default and ships a prebuilt codebook.

[verified] **Tokenization ablation** (AutoVLA main-paper table; numbers confirmed from the authors' NeurIPS rebuttal). ADE / FDE are in metres; movement coverage (MC) and codebook usage (CU) are reported for K-disk only.

| K | RT-1 (action bins) ADE / FDE | FAST (DCT) ADE / FDE | K-disk ADE / FDE | K-disk MC | K-disk CU |
| --: | :-- | :-- | :-- | --: | --: |
| 256 | 0.1440 / 0.2942 | 0.1708 / 0.2137 | 0.0687 / 0.1034 | 86.47% | 100.0% |
| 1024 | 0.1052 / 0.1883 | 0.0522 / 0.0588 | 0.0253 / 0.0282 | 97.41% | 100.0% |
| 2048 | 0.1014 / 0.1775 | 0.0281 / 0.0309 | 0.0182 / 0.0203 | 99.42% | 100.0% |
| 4096 | 0.1001 / 0.1739 | 0.0149 / 0.0161 | 0.0141 / 0.0155 | 100.0% | 91.46% |

**Interpretation (authors' own).**
- **RT-1 binning** discretizes acceleration and steering rate, then reconstructs trajectories through a kinematic model. It has the highest error because controls must be *inferred* from trajectory-level data.
- **FAST** produces variable-length token sequences (typically 1–25 tokens), which complicates fixed-horizon prediction.

The review's stronger phrasing ("errors compound exponentially", "breaks alignment") is its own gloss.

### 1.3 Training: SFT and reinforcement fine-tuning

**SFT.** [verified]
- Loss: `L_SFT,i = w_i · (L_LM,i + λ_a · L_action,i)`, with `w_i = λ_cot = 40` when the ground truth contains CoT, else 1. λ_a is effectively 1.
- Code nuance: for CoT samples the released code computes `40·L_LM + L_action`, so the ×40 does not scale the action term.
- The vision encoder is **frozen in SFT as well** [corrected], and SFT is **full language-model fine-tuning**, not LoRA.
- Setup: FSDP full-shard, bf16, 8 × NVIDIA L40S, 5 epochs, effective batch 32.

**RFT (GRPO; `shao2024deepseekmath`).**
- [verified] KL weight β = 0.04 against the SFT reference; advantage `A_i = (r_i − mean) / std` over the group.
- [corrected] A single on-policy update per step, so clipping is unused and no ε value is given.
- [corrected] Group sizes 2 / 4 / 8 compared (8 best); the code ties G to the GPU count.
- [verified] LoRA r = 8, α = 8, dropout 0.1 on attention projections; frozen vision encoder; learning rate 3e-5.

**Reward.** `r = r_Driving − λ_r · r_CoT` with λ_r = 0.3. [verified]
- **nuPlan / NAVSIM:** `r_Driving = PDMS = NC × DAC × (5·TTC + 5·EP + 2·C) / 12`. This is the standard NAVSIM v1 score. [verified]
- **Waymo E2E:** `r_Driving = (δ − ADE) / κ` with δ = 2 m and κ = 10 (paper Appendix D). [verified]
- **CoT length penalty:** `r_CoT = sigmoid((L − 400) · 0.002)`. [verified]
  - It applies **only to slow-thinking outputs** (the code checks for "complex scenario").
  - In the released code, L is measured in **characters**.

---

## 2. Open-Loop vs Closed-Loop Evaluation

### 2.1 Why open-loop metrics mislead

1. **Covariate shift and causal confusion.** In log replay the policy's actions never affect its future inputs. [verified] (standard argument)
2. **Imbalanced validation data.** [corrected] 73.9% of nuScenes involves straight driving (Li et al., CVPR 2024; `li2024egostatus`); Bench2Drive rounds this to ≈ 75%.
3. **Ego-status shortcuts.**
   - [corrected] AD-MLP (Zhai et al. 2023; `zhai2023admlp`), which uses only ego history, reaches **0.29 m average L2** under the ST-P3 metric.
   - Li et al.'s Ego-MLP averages 0.35 m, and a trivial "go straight" baseline 0.83 m.
   - Always state the L2 protocol: the numbers differ by about 2× between protocols.
4. **Closed-loop collapse.** [verified] AD-MLP scores **0.00% SR** on Bench2Drive (DS 18.05). Under Bench2Drive v0.0.4 it is DS 35.39, still SR 0.00.

### 2.2 Bench2Drive

[verified] Bench2Drive (Jia, Yang, Li, Zhang, Yan; SJTU) uses CARLA 0.9.15 ("CARLA v2").

**Training data.**
- About 2M annotated frames, 44 scenario types, 23 weathers, 12 towns.
- [corrected] The clip count is **13,638** in the arXiv abstract (Full set plus supplementary) and 10,000 in the NeurIPS abstract (Full split).
- Splits: mini (10 clips, ≈ 4 GB), base (1,000 clips, ≈ 400 GB), full (≈ 4 TB).
- Licence: **CC-BY-NC-ND**.

**Evaluation.**
- **220 routes** (44 scenarios × 5), each about 150 m long and isolating one scenario.
- **5 abilities.** Scenario counts: Merging 16, Overtaking 9, Emergency Brake 12, Give Way **2**, Traffic Sign 18. A scenario may count toward several abilities. Give Way has only 2 scenario types, so its numbers are noisy.

**Metrics.** [verified]
- **SR:** share of routes completed with no infraction and no timeout.
- **DS:** mean over routes of route completion × ∏ infraction penalties.
- **Efficiency:** mean of ego speed / average speed of nearby vehicles, checked at 20 checkpoints (every 5% of the route); values above 1000% are dropped.
- **Comfortness:** share of smooth 20-frame segments, using nuPlan's bounds:

| Signal | Bound |
| :-- | :-- |
| Longitudinal acceleration | [−4.05, 2.40] m/s² |
| Lateral acceleration | ±4.89 m/s² |
| Yaw rate | ±0.95 rad/s |
| Yaw acceleration | ±1.93 rad/s² |
| Longitudinal jerk | ±4.13 m/s³ |
| Jerk magnitude | ±8.37 m/s³ |

**Why short routes.** [verified] On the official CARLA Leaderboard 2.0 (routes of 7–10 km with multiplicative penalties), "participating methods score below 10 out of 100 points". SimLingo-BASE (CarLLaVA) won the 2024 CARLA Challenge with **6.87 DS** on the sensor track. [corrected] Since March 2025, **Leaderboard 2.1** uses linear penalties, so LB2.0 and LB2.1 scores are not comparable.

### 2.3 Bench2Drive results

All rows below use Bench2Drive v0.0.3 as reported in the papers. **Always state the benchmark version**: v0.0.4 (Aug 2026) re-evaluated many methods, e.g. SimLingo 86.55 / 70.45.

| Model | Open-loop avg L2 (m) | DS ↑ | SR % ↑ | Efficiency ↑ | Comfortness ↑ | Status |
| :-- | --: | --: | --: | --: | --: | :-- |
| AD-MLP | 3.64 | 18.05 | 0.00 | 48.45 | 22.63 | [verified] |
| UniAD-Base | 0.73 | 45.81 | 16.36 | 129.21 | 43.58 | [verified] |
| VAD | 0.91 | 42.35 | 15.00 | 157.94 | 46.01 | [verified] |
| TCP-traj* (expert-feature distillation) | 1.70 | 59.90 | 30.00 | 76.54 | 18.08 | [verified] |
| TCP-traj w/o distillation | — | 49.30 | 20.45 | 78.78 | 22.96 | [verified] (SimLingo Table 2) |
| DriveAdapter* | 1.01 | 64.22 | 33.08 | 70.22 | 16.01 | [verified] |
| ORION (generative VLM planner) | **0.68** [corrected] (the review showed "—") | 77.74 | 54.62 | 151.48 | 17.38 | [verified] |
| AutoVLA (CARLA-specific model; see note) | — | 78.84 | 57.73 | 146.93 | 39.33 | [verified] |
| **SimLingo-BASE** (= CarLLaVA) | — | **85.94** | **66.82** | 244.18 | 25.49 | [verified] added |
| **SimLingo** (3 seeds) | — | **85.07 ± 0.95** | **67.27 ± 2.11** | 259.23 | 33.67 | [verified] added |
| SimLingo without CoT at inference | — | 84.41 ± 1.76 | 64.84 ± 2.42 | — | — | [verified] added (paper Table 10) |
| Think2Drive (privileged RL expert, not a sensor policy) | — | 91.85 | 85.41 | 269.14 | 25.97 | [verified] added, for context only |

**Notes on the table.**
- The L2 column comes from the Bench2Drive paper (Table 3) and was merged into AutoVLA's table by the source review. ORION's 0.68 m was added in this correction from the ORION README, which reports it next to the same UniAD-Base (0.73) and VAD (0.91) values.
- AutoVLA's Bench2Drive row comes from a separate model: single front camera, CARLA-Garage codebook, trained on CARLA-Garage + DriveLM-CARLA, SFT only, replanning at 2 Hz.
- Training data differs across rows: the baselines use Think2Drive-collected data, SimLingo uses PDM-Lite. The comparison is therefore not controlled.

**SimLingo multi-ability success rates** (paper Table 8) [verified]. These matter for this project because they set the **natural failure background** (see [`MASTER_HANDOFF.md`](MASTER_HANDOFF.md) §4.2).

| Merging | Overtaking | Emergency Brake | Give Way | Traffic Sign | Mean |
| --: | --: | --: | --: | --: | --: |
| 54.01 ± 2.63 | 57.04 ± 3.40 | 88.33 ± 3.34 | 53.33 ± 5.77 | 82.45 ± 4.73 | 67.03 ± 2.12 |

---

## 3. Chain-of-Thought, Probing and Failure Detection

### 3.1 CoT structure and distillation

[verified] **The four reasoning steps** (the teacher's annotation format):
1. scene description;
2. critical-object identification;
3. intention reasoning about surrounding agents;
4. decision / meta-action (one lateral plus one longitudinal action).

The student's system prompt numbers **five** steps, with object behaviour prediction split out.

[verified] **How the CoT data was made.**
- Teacher: Qwen2.5-VL-72B; the released annotation config uses the AWQ-quantized variant.
- The teacher is **given the ground-truth best driving action as a hint**.
- Human audit: 3,000 samples, **88.8%** accuracy.
- A secondary source reports ≈ 45.6k nuPlan and 7.2k Waymo CoT annotations. [unverified]

**Caveat for this project.** CoT written with the answer in view is **post-hoc rationalization**. The 88.8% measures annotation quality, not whether the student's reasoning is faithful. **Never treat a policy's CoT as ground truth for describing failures.**

### 3.2 Text waypoints vs action tokens

[verified] AutoVLA v2 / NeurIPS camera-ready, "Influence of Physical Action Tokenization". Both variants were trained on the same nuPlan + nuScenes mix. PDMS is measured on NAVSIM navtest; L2 and collision are open-loop metrics.

| Output | PDMS ↑ | Avg L2 (m) ↓ | Avg collision (%) ↓ | Runtime (s) ↓ |
| :-- | --: | --: | --: | --: |
| Text waypoints | 71.31 | 0.89 | 0.36 | 7.65 |
| FAST (DCT) tokens | 67.63 | — | — | — |
| Physical action tokens (K-disk, K = 2048) | 80.54 | 0.70 | 0.31 | 3.95 |

[corrected] **Version dependence:** arXiv v1 reported text waypoints at 59.24 / 1.29 / 0.98% / 9.31 s against action tokens at 80.54 / 0.86 / 0.35% / 3.95 s. The text baseline was re-tuned after a GitHub issue. The "48.4% faster" figure is computed from v2's numbers.

### 3.3 Qualitative failure cases

[unverified] The source review lists three illustrative failure cases:
- stop-sign dithering (a perception error vs a decision loop);
- construction-zone detours;
- lane-level traffic-light misassignment.

These are plausible and useful as **hypotheses for failure axes**, but they were not confirmed as specific AutoVLA findings. Treat them as motivation, not evidence.

---

## 4. Red-Teaming, Interactive Scenarios and Data Scaling

### 4.1 Interactive long-tail scenarios

**The game-theoretic argument** is the review's own motivation, not an empirical result from the cited papers. Imitation policies treat other agents as open-loop background, so in negotiated interactions they either stall or force their way through.

**Interactive scenario families.** [corrected] Names checked against the CARLA / Bench2Drive scenario classes; each maps to a real class:
- unsignalized turn conflicts: `InvadingTurn`, `OppositeVehicleTakingPriority`;
- cut-ins and merges: `ParkingCutIn`, `MergerIntoSlowTraffic`;
- blocked roads: `ConstructionObstacleTwoWays`, `ParkedObstacleTwoWays`;
- occluded pedestrians: `PedestrianCrossing`, `ParkingCrossingPedestrian`;
- highway interaction: `HighwayCutIn`, `InterurbanActorFlow`;
- intersections and emergency vehicles: `BlockedIntersection`, `YieldToEmergencyVehicle`.

**"Standard imitation models succeed < 20% on these scenarios."** [unverified] The overall Bench2Drive success rates of UniAD and VAD are 15–16%, which is consistent with the claim, but no per-family figure was checked. Do not quote it as a statistic.

### 4.2 Data scaling (AutoVLA Fig. 4) — corrected

[removed] **The source's scaling "table" is contradicted by the paper** (audit 2nd pass; 1st pass: likely fabricated). The paper shows scaling only as Fig. 4, with nuPlan + nuScenes training mixtures of 10k / 50k / 100k / 185k samples. The values below are the **data labels printed on Fig. 4**, read from the figure through a mirror of arXiv v1. Each cell is action-only / CoT.

| Samples | nuPlan PDMS ↑ | nuPlan no-at-fault collision ↑ | nuScenes L2 (m) ↓ | nuScenes collision (%) ↓ |
| --: | :-- | :-- | :-- | :-- |
| 10k | 51.17 / 44.06 | 84.44 / 80.30 | 0.93 / 1.47 | 0.68 / 0.84 |
| 50k | 65.19 / 61.38 | 92.33 / 86.23 | 0.82 / 1.16 | 0.41 / 0.45 |
| 100k | 71.79 / 73.62 | 93.26 / 94.18 | 0.76 / 1.04 | 0.39 / 0.40 |
| 185k | 74.97 / 80.54 | 95.19 / 96.89 | 0.70 / 0.86 | 0.31 / 0.35 |

**Findings.**
- More data consistently helps (paper text).
- On nuPlan, the text says CoT does not beat action-only "when using fewer than 50k training samples". The Fig. 4 labels show it is still behind at 50k (61.38 vs 65.19 PDMS) and ahead at 100k (73.62 vs 71.79).
- On nuScenes, action-only is better at every scale (Fig. 4; the text says action-only gives better L2 and collision rate).

**Implication for us.** The amount of targeted repair data matters. The handoff pre-registers 20k frames as the primary volume and sweeps 5k / 50k for the targeted condition.

### 4.3 Waymo end-to-end results

[corrected] **AutoVLA Table S4** (ablation on the Waymo E2E test set) has only two metrics, RFS Overall and ADE @ 5 s. [verified] The values match the source:

| Camera | Pretraining | Supervision | RFS Overall ↑ | ADE @ 5 s (m) ↓ |
| :-- | :-- | :-- | --: | --: |
| Front | none | action-only | 6.938 | 3.595 |
| Front | none | CoT | 7.127 | 3.188 |
| Multi | none | action-only | 7.239 | 3.243 |
| Multi | none | CoT | 7.283 | 3.182 |
| Multi | nuX | action-only | 7.406 | 3.116 |
| Multi | nuX | CoT | 7.447 | 3.115 |
| Multi | nuX | Post-RFT | 7.557 | 2.958 |

**Leaderboard claim.** [corrected] The RFS **Spotlight** score of 6.9436 comes from the challenge-leaderboard snapshot (Table S3), where AutoVLA is **#1 on Spotlight but #5 on RFS Overall** (7.5566).

---

## 5. Diagnostic Protocols and the "Build Plan"

### 5.1 Diagnostic metric suite

[verified] These are all reasonable and standard:
- horizon-specific ADE / FDE;
- PDMS sub-metrics (NC, DAC, TTC, EP, C) to separate collisions, rule violations, stalling and discomfort;
- RFS Overall vs Spotlight;
- per-scenario-slice success rates.

**This project uses** Bench2Drive's closed-loop DS / SR, per-ability success, and CARLA infraction types to type failures. PDMS is open-loop and non-reactive; use it only in NAVSIM-side analyses.

### 5.2 Runtime vs planning quality

- [corrected] RFT (GRPO with the CoT length penalty) moves the policy toward fast thinking in easy scenes: runtime **3.95 s → 1.31 s (−66.8%, averaged over 500 NAVSIM test samples)**, PDMS **80.54 → 89.11 (+10.6%)**.
- [verified] Best-of-N (an oracle over 6 samples) reaches 92.12 PDMS.
- [corrected] With the released checkpoint, one user reproduces **≈ 83.7 PDMS**.

### 5.3 The source's five-phase "engineering build plan"

This plan **re-describes how AutoVLA was trained**. It is **not** a plan this project should follow. We probe and repair an *existing* policy (SimLingo) rather than train a new VLA.

| Phase | Correct version |
| :-- | :-- |
| 1 · Data | 3 cameras × 4 frames at 2 Hz; [corrected] 28 × 28 × 128 is a pixel budget; K = 2048 codebook with δ = 0.05 m [verified] |
| 2 · CoT distillation | [verified] 72B teacher with ground-truth hints. 88.8% is a *measured* audit result, not a target. The CoT data itself is unreleased. |
| 3 · SFT | [verified] Qwen2.5-VL-3B, FSDP, bf16; [corrected] vision encoder frozen, full-LM fine-tuning, λ_cot = 40 |
| 4 · RFT | [verified] LoRA r = 8, α = 8, dropout 0.1, frozen ViT, β = 0.04; [corrected] no clipping, and G is not 6 as a verified value |
| 5 · Closed-loop validation | [removed] "DS ≥ 78, SR ≥ 57% as safety deployment criteria before real-vehicle testing" is unsupported. These are AutoVLA's own Bench2Drive numbers from a separate CARLA model, and there is no released CARLA code. |

---

## 6. What This Means for the Project

[`MASTER_HANDOFF.md`](MASTER_HANDOFF.md) §7 turns these points into decisions:
- closed-loop-only evaluation;
- Bench2Drive's per-scenario design as the taxonomy baseline;
- hooking at the action bottleneck;
- CoT as a confound;
- latency-aware rollout budgets;
- infraction-based failure typing;
- interactive scenario families as candidate planted gaps;
- a targeted-data volume sweep;
- RFT as a stretch repair baseline;
- rejecting the "Phase 5 safety criteria".

**Why AutoVLA is background here, not the policy we study.** It has no released CARLA agent, its CoT data is unreleased, its licence is academic-only, and slow-mode latency is about 10 s per step. **SimLingo** is the primary policy and **Drive-π0** (DriveMoE) the secondary (`MASTER_HANDOFF.md` §2).
