# Describability gate and B8, design

**Status: drafted 2026-10-15; model pins and sign-off pending (Chris).** `PRD.md`
§9.2 defines the gate; C25 (pending) makes B8, a log-based VLM failure taxonomy,
a required baseline and requires the two to use **different** vision models. Both
read the same keyframes and the same logged-observation summaries, so they are
specified together. No code until the models are pinned (§16.8).

## Shared inputs

- **Keyframes.** The agent's own JPEG, which the capture stores every 10th step
  and which regenerates the exact model input (`PRD.md` §12.1). For a failing
  rollout: the frames in its failure window (3 s before the first collision, else
  the last 3 s), the same window every method uses.
- **Structured summary of a rollout**, built only from logged observations
  (`world_state.py` per-step state and actors): ego speed profile; nearest lead,
  pedestrian and other actors with class, distance and relative speed;
  time-to-junction; traffic-light state; occlusion flag; collision events with
  the other actor's class. **Never** scenario type, parameters, weather preset,
  town, or route id: those would hand a text model the factor list.

## The gate (PRD §9.2), per axis

1. **Groups.** A = the axis's top failure keyframes (its highest-activation
   supporting episodes, one keyframe each, at most 8). B = matched contrast
   frames: success frames matched on ego speed (±2 m/s) and road type (junction
   or not, from `junction_distance`), never on scenario labels.
2. **Description.** The pinned VLM answers one fixed prompt: what is present in
   group A and absent in group B. Output capped at 60 words.
3. **Prediction.** A separate **text-only** model sees only that description and
   the structured summaries of held-out rollouts and scores each 0–1 for "this
   rollout belongs to the axis". Held-out rollouts come from **base routes not
   used to find the axis** (C27c).
4. **Pass** if AUROC ≥ 0.70 against the axis's held-out membership.
5. **Controls**, reported for every method: random axes of matched size, and the
   description-shuffle control (each axis scored with another axis's
   description). The shuffle pass rate **is** the gate's false-positive rate.
   Also report each axis's firing rate on clean routes (C27c).
6. The policy's own chain-of-thought is never ground truth.

## B8: failure taxonomy from logs (C25)

1. For each failing rollout, the B8 VLM writes one structured explanation from its
   failure-window keyframes plus its structured summary (fixed prompt: what
   happened, what the ego did, what it should have done; ≤ 80 words).
2. Explanations are embedded with a pinned text-embedding model, clustered
   (k-means, k = M, seed 0), and clusters rank by size into axes under the
   shared budget M.
3. VLM calls only; no rollouts, no activations.

## Model candidates (to pin; licences from model-card tags, recheck before use)

| Role | Candidate | Licence (tag) | Note |
|---|---|---|---|
| Gate VLM | `Qwen/Qwen3-VL-8B-Instruct` | Apache-2.0 | Fits one A40 in bfloat16 |
| B8 VLM | `OpenGVLab/InternVL3_5-8B` | Apache-2.0 | **Shares InternViT lineage with SimLingo's encoder** — maybe a confound for B8; a third family (e.g. Mistral's Pixtral) avoids it, licence unchecked |
| Gate text model | a different family from the gate VLM's language model | — | Both candidates above use Qwen-family LLMs |
| B8 embedder | a pinned sentence-embedding model | — | — |

Rules from C25 and §16.8: gate VLM ≠ B8 VLM; exact model IDs and revisions are
logged; a closed API is only an optional comparison.

## Decisions needed (Chris)

1. Pin the gate VLM, the gate text model, the B8 VLM, the B8 embedder.
2. Accept the matching rule for contrast frames (±2 m/s, junction or not).
3. Accept "≤ 8 keyframes per group" and the word caps.

## Cost

Gate: about 2 VLM calls per axis plus one text call per held-out rollout per axis,
times (methods × M + controls). B8: one VLM call per failing rollout. All on one
A40, a few GPU-hours per full run, no simulator.
