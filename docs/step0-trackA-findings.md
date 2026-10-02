# Step 0 · Track A findings — paper facts

Verified 2026-10-01 against the PDFs: Dr. VLA arXiv 2603.19183v2, Fail2Drive 2604.08535v1,
SimLingo 2503.09594v1, RoboART 2502.06575v1, SAFE 2506.09937v2, RESample 2510.17640v4.
**Not yet read: Event-grounded SAEs (2605.17204). A5 stays open.**

**For the agent applying this:** treat every ✅ line as ground truth. Strike the matching
**Unverified** block in `PRD.md` and add the cited reference. Make each ⚠️ correction exactly as
written. 🔶 items are design consequences for the PRD owners. Do not apply those without sign-off.
Status key: ✅ confirmed · ⚠️ correction · 🔶 design consequence · ❓ not resolvable from the paper.

---

## Headline: five things that change the plan

1. **D1 is closed. The expansion ratio is 1, and the brief was right.** Dr. VLA App. B.1, Table 6, Fig. 4:
   *"larger expansion ratios lead to substantially more dead features while providing similar
   interpretability in our setting… likely due to the much smaller scale datasets sizes… in
   robotics."* Rewrite PRD §12.2 to ER = 1, with 8× to 32× only as an ablation, and close §16.1.
2. **The Dr. VLA code is out.** `github.com/swannaiden/drvla` (last commit 2026-09-29) has SAE
   training, generality metrics, the classifier, a feature index, and a Streamlit dashboard. It
   does **not** include steering or ablation code, and it has **no LICENSE file**. Hooks are
   π0.5/openpi-specific. Step 7 drops from "build an SAE stack" to "configure one", but the causal
   check is still ours to write. Ask the authors about a license before vendoring any code.
3. **The memorization filter will probably delete our gap features.** 🔶 See Dr. VLA App. C.5.
   The classifier labels a feature as memorized when it fires once per episode (ō ≈ 1) across a
   coherent but small subset of the data. That describes a planted gap exactly: one cut-in per
   route, in 4–8% of the pool. The classifier was also fit on 30 hand-labeled manipulation features,
   so it does not transfer to driving. **Proposal:** make "apply the memorization filter before
   ranking" (§9.2) an ablation rather than the default. If we keep it, relabel ~30 driving features
   and refit.
4. **SimLingo does not freeze the vision encoder.** ⚠️ Paper §4.2: *"We fully finetune all
   components besides the LLM for which we use LoRA."* PRD §9.4 and §12.3 describe a frozen vision
   encoder as "SimLingo's own recipe", which is wrong. Freezing it is still a defensible choice for
   our repair step, but it must be labeled as our deviation.
5. **RoboART does use a VLM critic, so CONFLICTS A5 over-corrected.** ⚠️ RoboART §4.1: four edits
   are generated per input, and Gemini Pro 1.5 judges them and picks the best or discards all. The
   brief's description was right. Put it back in PRD §4.1.

---

## A1 · Dr. VLA (CoRL 2026, confirmed on the project page and in the repo README)

| Item | Finding | Ref |
|---|---|---|
| Expansion ratio | ✅ **1** (OpenVLA used 0.5 to keep the dictionary at ~2048). Larger ratios give more dead features with similar interpretability. | B.1, Table 6, Fig. 4 |
| k | ✅ k = 100 at d = 2048 (PaliGemma); **k = 64 at d = 1024** (action expert). No scaling rule is stated. 🔶 For d = 896, sweep k ∈ {32, 48, 64}. | B.1 |
| Optimizer etc. | ✅ Adam (0.9, 0.999), lr 1e-4, batch 4096, 100 epochs, k_aux 512, aux coefficient 1/32. Pre-bias initialized to the geometric median of 10k samples. Per-sample mean-subtraction and ℓ2 normalization. Unit-norm decoder with tangent-projected gradients. Grad clip 1.0. No encoder or decoder bias. | B.1, Table 6 |
| Dead-latent threshold | ✅ No activation in the last 500 steps | B.1 |
| Seeds | ✅ Six | B.2, Fig. 5 |
| Generality metric | ✅ Four per-feature stats: episode coverage c, mean onset count ō (τ_on = 0.1), mean peak activation ā, relative run length ℓ̄_r. A logistic regression on these gives P(general). | §3.2–3.3, C.1–C.3 |
| Classifier validation | ✅ 30 hand-labeled features per dataset (15 general, 15 memorized). LOO accuracy is 100% on LIBERO and 96.7% on DROID. | C.3 |
| % general | ✅ π0.5/LIBERO 2.62%, π0.5/DROID 10.81%, OpenVLA/LIBERO-Goal 0.45%. "Most features are memorized" holds. | Table 1 |
| Interpretable fraction | ✅ 95/120 SAE features (79.2%) vs **6/20** FFN neurons (30.0%). The baseline n is 20, not 120. | §4.1 |
| Ablation | ✅ Unsteered 39/40; random memorized 37/40; random general 26/40; **top-4 most general 0/40**. Real-world DROID, sponge and towel tasks. | §5.2, Table 2 |
| Mean-pooling | ✅ Mean-pooled per timestep by default. Per-token SAEs were "promising but currently less interpretable". | A.3, §7, App. G |
| Ablation operator | ✅ y′ = y − (yᵀv)v, applied at every token and every denoising step | §3.4, F.2 |
| Limitation we cite | ✅ "Meaningful top activations of a feature does not imply reliable steerability" | §7 |
| §3.3 "why now" claim | ✅ Dr. VLA §6 proposes that episode-specific features could diagnose fine-tuning brittleness and that feature metrics could act as a training-time proxy for generalization. This is untested in the paper. | §6 |

🔶 **B7 needs our own definition.** Dr. VLA never uses memorized-feature concentration as a gap
signal. That is the PRD's construction, so §9.3 B7 must specify it before Step 6. Note the irony
in item 3 above: the features the classifier calls "memorized" are the ones most likely to be gap
features. B7 may therefore be stronger than we would like.

## A2 · Fail2Drive (IROS 2026)

| Item | Finding | Ref |
|---|---|---|
| Case study | ✅ **Verbatim:** PedestriansOnRoad. *"SimLingo performs particularly poorly, dropping from 98.50 to 19.68 HM with collisions in 87% of cases. Its language-action module often hallucinates a nonexistent car or cyclist to follow (Fig. 6), showing overfitting to the language used during training."* | §4.2, Fig. 6 |
| Mechanism wording | ⚠️ The paper says "car or cyclist", not "vehicle-shaped lead actor". The mechanism is the authors' own claim, so cite it as theirs. Strike the §3.2 Unverified block. | §4.2 |
| SimLingo, Table 1 | ✅ B2D DS 85.1. In-distribution: DS 82.6, SR 79.3, **HM 80.9**. Generalization: DS 71.7 (−13.2%), SR 55.0 (−30.6%), **HM 62.2 (−23.1%)**. | Table 1 |
| Categories | ✅ Visual-lon 71.1 (−9.0%), Visual-lat 45.9 (−32.2%), **Behavior 31.2 (−64.2%)**, Robustness 86.8 (−5.9%) | Supp. Table 2 |
| No-training rule | ✅ Quote: *"Models must not use the routes, scenario definitions, or assets introduced in Fail2Drive for training or fine-tuning. The benchmark serves strictly as a held-out test set."* Pretraining on external data or foundation models is allowed. | §3.2 |
| Seeds | ✅ Three evaluation seeds, averaged | §4.1 |
| PDM-Lite | ✅ PDMLite-F2D is offered as a solvability check for new scenarios (gen HM 94.6). ❓ Whether it runs standalone is a repo question. | §5 |
| Toolbox | ✅ Scenario, asset, and behavior authoring; 17 animal assets; customizable obstacles. ❓ API surface is a repo question. | §5, Supp. A |

🔶 **Framing caution for §3.2.** PedestriansOnRoad is an authored scenario class, and any factor
list could name "pedestrians walking in the ego lane". Use it as evidence that SimLingo's behavior
rests on cue-specific priors. Do **not** present it as an unlistable conjunction. The paper's own
summary supports that reading: *"vehicle-following cues do not generalize to non-vehicle agents."*

## A3 · SimLingo (CVPR 2025)

| Item | Finding | Ref |
|---|---|---|
| Architecture | ✅ InternVL2-1B = InternViT-300M-448px + **Qwen2-0.5B-Instruct**. ❓ Layer count and hidden size are not in the paper; take them from the loaded config at Step 1. | §3.3 |
| Waypoint queries | ✅ Learnable query tokens q_p (path) and q_w (waypoints). An MLP on their output features [o_p, o_w] predicts waypoint *differences*, which are cumulatively summed. Inference is one forward pass, not autoregressive. | §3.3, Fig. 2 |
| LoRA | ✅ r = 32, α = 64, dropout 0.1, on all LLM linear layers | §4.2, App. Table |
| Frozen parts | ⚠️ **None besides LoRA on the LLM.** *"We fully finetune all components besides the LLM."* The vision encoder is trained. | §4.2 |
| Loss | ✅ SmoothL1, changed from L2 because of training instability | §4.2 |
| CoT on/off | ✅ w/o CoT DS 84.41 ± 1.76, SR 64.84 ± 2.42; with CoT 85.07 ± 0.95, SR 67.27 ± 2.11 | Table 10 |
| Abilities | ✅ Merging 54.01, Overtaking 57.04, Emergency Brake 88.33, Give Way 53.33, Traffic Sign 82.45, mean 67.03 | Table 8 |
| Training cost | ✅ 14 epochs on 8×A100-80GB, 24 h (≈192 A100-h). Batch 12 in the text and 96 in the hyperparameter table, i.e. 12/GPU × 8. AdamW, lr 3e-5, wd 0.1, cosine schedule, 5% warmup. | §4.2, App. Table |
| Buckets | ✅ Five accel/decel buckets; two steering; three vehicle-hazard (by direction); one each for stop sign, red light, and walker hazard; one swerving; one "old towns" (Town01–10); one uniform. 650k samples per epoch. ❓ Weights are not given. ❓ The claim that withholding means filtering route directories is not in the paper; check the repo. | §3.2, App. B.2 |
| B2D version | ❓ Not stated in the paper. Record it from the repo at Step 2. | — |

## A4 · RoboART (CoRL 2025)

| Item | Finding | Ref |
|---|---|---|
| 12 conditions | ✅ **Levels of 5 factors:** lighting (red, green, blue), table background (red, green, blue), 4 distractor objects (black trash can, white trash can, laptop, candle), 1 person near the table, 1 table-height change | §5 |
| Anomaly detector | ✅ Mean k-NN cosine distance in policy embedding space to S_nom (first-timestep training observations). k = 5 with \|S_nom\| = 3000 (π_hyb); k = 10 with \|S_nom\| = 500 (π_dfn). Conformal threshold. 100 edited observations per factor. | §4.2, §5.1 |
| Metrics | ✅ Spearman ρ 0.8 (π_hyb) and 0.7 (π_dfn). Average absolute prediction error 0.10 and 0.19. Truth comes from 20+ hardware episodes per factor. | Table 1 |
| VLM critic | ⚠️ **Present.** 4 edits per input; Gemini Pro 1.5 picks the best or discards all. Restore in PRD §4.1 and fix CONFLICTS A5. | §4.1, Fig. 4 |
| Co-finetune | ✅ ~100 trajectories (~1 h) for each of the 3 worst factors. 80/20 old/new per mini-batch, lr 5e-6, 20K steps. **2–7×** on the collected conditions, 2–5× cross-domain on the uncollected ones. | §5.2, Fig. 6 |
| §3.3 claim | ✅ Their limitations name both halves of our contribution: "Hidden environmental factors" (needs visual change) and "Multi-round predictive red teaming" (single fixed factor set). Also useful: they score only **first-timestep** observations, which strengthens our temporal argument. | §6 |

## SAFE (NeurIPS 2025): §4.2 spot check

✅ The aggregation ablation covers First, Last, Mean, and First&Last. The real-world setting is pre-logits with Mean aggregation (App. B.8).
✅ Training takes "less than one minute" on an A100-40GB (App. B.7). The MLP and LSTM heads have 1–2 layers, with a functional conformal threshold.

## RESample

✅ arXiv 2510.17640v4 lists no venue. This matches PRD §4.5.

---

## Still open after Track A

- **A5 Event-grounded SAEs (2605.17204):** PDF not yet supplied.
- ❓ Items that need a repo or a loaded model, not a paper: Qwen layer count and hidden size, bucket weights,
  the route-directory withholding claim, the B2D version, PDMLite-F2D standalone use, and the Fail2Drive toolbox API.
- Dr. VLA license: ask the authors.
- Unrelated typo: CONFLICTS.md calls the brief `prod.md`, but the PRD calls it `prd.md`.
