# Research log

Decision timeline for the planted-gap recovery goal. Newest entry at the bottom. Times are Pacific.

## 2026-10-31 22:40 — bootstrap

**Goal (from Jerry):** prove the discovery SDK finds failures we planted in CARLA, explain how, keep an extensive
log, end with an explainer video; 6,000 SU allowed.

**Where we start (measured earlier today):** three planted camera faults pass their full pilots: P4 occlusion
(43/60 slice failures vs 12/60), P7 freeze (53/56 vs 15/60), P8 latency (58/58 vs 12/60). Shards with layer means
exist for all of them and for 384 background rollouts.

**Why the earlier attempt failed:** the first dev evaluation (2026-10-15) had P4 as 70% of failures, so an axis of
every failure scored 0.70 and no method could beat that. With P7, P8 and both background waves pooled, each planted
gap is roughly a fifth of the failures, so a catch-all scores about 0.2 and real recovery can show.

**Decision:** lock H1's protocol before touching data (`experiments/h1-planted-gap-recovery/protocol.md`), then
build the mechanical code the 2026-10-22 spec listed as missing. Savio's login dropped at about 22:30, so the run
waits for the user; code and tests go first.

## 2026-10-31 22:55 — code and the Tier 2 corpus, while Savio is down

- **Protocol locked** in `10b02ce` before any data was opened.
- **Evaluation code** delegated to a Sonnet subagent (single module, clear spec): `src/discovery/dev_eval.py` gets
  layer-mean input, M2 probe-residual, B3, the 0.5 cap, per-gap best Jaccard with a slice-vs-neighbourhood audit,
  and a per-gap base-route bootstrap.
- **Tier 2 corpus prepared** (`cf268d3`): background wave 3, 200 routes with per-token capture at layers 10 and
  11, so the per-token SAE can read background and pilots alike. `dev_routes.py` gained a `background_role`
  option because the background-only path hard-coded wave 2's id offset (a third wave would have reused its ids).
  Expected cost about 820 SU at 4.1 SU per route (unmeasured for this wave). Submit when Savio is back.
