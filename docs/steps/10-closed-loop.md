# Step 10 — Closed loop

**Status: drafted 2026-10-16 (Chris's lane, sign-off pending). Runs only on a
"go" at Step 9.** `PRD.md` §9.4, §12.3, C10, C11, C14, C19.

**Done when** one full cycle has run with the no-degradation check reported,
every authored scenario passes solvability, and no Fail2Drive asset was trained on.

## SimLingo's own recipe (read from the repo, 2026-10-16)

`simlingo_training/config/experiment/simlingo_seed1.yaml` at
`github.com/RenzKa/simlingo` (main): InternVL2-1B for vision and language;
**LoRA on the language model with r = 32, α = 64, dropout 0.1** (matches
§9.4); lr 3e-5; batch 6 per GPU on 8 GPUs; 15 epochs; Hydra configs; Weights &
Biases logging on by default (`train_simlingo_seed1.sh`, 8 GPUs, 3-day limit).
The released data is `datasets/RenzKa/simlingo` on Hugging Face: 1,158 GB of
driving data plus language labels (checked via the HF API, 2026-10-16).

## Cycle, per targeted axis

1. **Reproduction test** (C10). Parameterize a scenario family along the axis;
   run 50 sampled scenarios. The axis reproduces if its failure rate is ≥ 2× the
   class's nominal rate and ≥ 30%. Otherwise no fine-tune; a reproducing axis
   that matches no gap is a validated natural axis (§9.4).
2. **Solvability.** PDM-Lite (the expert SimLingo's data was collected with)
   completes every authored scenario. Scenarios it cannot solve are dropped.
3. **Targeted data.** PDM-Lite drives the authored scenarios with SimLingo's
   sensor setup and label format (the repo's data-collection path), producing
   driving labels. Language labels (commentary, VQA, dreamer) are **not**
   generated for targeted data in v1, so their loss terms see replay data only;
   recorded as a deviation.
4. **Fine-tune** from the released checkpoint: LoRA as above on the language
   model, **vision encoder frozen** (C19, our deviation; an unfrozen arm if it
   underfits), 1:1 targeted : replay per batch, hyperparameters fixed before any
   targeted data exists and identical across all arms.
5. **Controls at matched frames and GPU-hours** (C11): no fine-tune; random
   scenarios; LLM-proposed hazards from a generic list; B4's worst factor
   levels; B3's clusters; B8-targeted (if C25 is accepted); oracle from the true
   key predicates (upper bound).
6. **Evaluation.** Failure rate on held-out gap-slice routes (separate locations
   and seeds); failure rate on the *other* gaps (targeted vs generic repair);
   Bench2Drive-220 over three seeds, non-inferior if the lower one-sided 95%
   bound on ΔDS ≥ −2.

**Targets must be gaps we authored** (§4.7, C14). Fail2Drive-derived gaps
(P5, P6-style) can be discovered and evaluated but never trained on.

## Infrastructure to build (in order, each only when the previous works)

1. SimLingo's training code running on Savio on the released checkpoint with a
   tiny replay-only schedule: proves the environment, measures A40 step time and
   memory. Weights & Biases logging on (the repo's default).
2. PDM-Lite data collection on one authored route on Savio.
3. The 1:1 mixed data module and the frozen-encoder option.
4. One arm end to end; then the matched-budget control arms.

## Unknowns to measure before costing

- A40 step time and memory for LoRA fine-tuning (the paper used 8 GPUs; Savio
  A40 nodes may need multi-node or fewer GPUs with gradient accumulation).
- Replay data needed: the 1:1 mix needs as many replay frames as targeted
  frames, so a subset of the 1.16 TB suffices if chosen by a seeded draw.
- How many repair steps: RoboART used 20K steps at lr 5e-6 with an 80/20 mix
  (§12.3); a starting point to adapt, with the deviation stated.

## Open for Chris

1. Language labels for targeted data: skip in v1 (above) or generate?
2. Download the full training set (also serves B7 variant A), or a seeded subset?
3. W&B project and account to log to.
