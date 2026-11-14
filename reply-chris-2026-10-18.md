# Reply to updates (2026-10-18)

Thanks for the update.

## Updates

Got it, all good. My agent has them.

## Shards

Thanks for yours. Mine are up now, set up the way you suggested. You have read access, and the rest of my scratch stays closed:

| What | Path | Size |
|---|---|---|
| Dev pool, wave 1 | `/global/scratch/users/imhaohao/share/dev-pool-wave1-shards/` | 2.2 GB, 380 files |
| Dev pool, wave 2 | `/global/scratch/users/imhaohao/share/dev-pool-wave2-shards/` | 3.2 GB, 400 files |
| P4 main pilot | `/global/scratch/users/imhaohao/share/p4-main-shards/` | 4.5 GB, 240 files |
| SAE sweep (layers 10 and 14, k 32/48/64, six seeds) | `/global/scratch/users/imhaohao/share/sae-sweep/` | 222 MB, 73 files |

I also added a default rule, so anything I put in `share/` later is readable to you without another step.

## Split

Sounds good, including you leading the writing and the poster. Here's how I see the next stretch running in parallel:

| Jerry | Chris |
|---|---|
| An interactional practice gap that passes, built from `routes_validation.xml` (your item 8) | Harness, scoring and the preregistration |
| Dev evaluation on your Step 2 rerun shards, with B7 post-correction | B4 and the sealed gaps |
| Contrastive on raw activations as well as SAE latents, plus the hysteresis firing | B3, probe-residual, the describability gate and B8 |
| New rollout configs at `capture_token_layers: [10, 11]` | Step 8, Step 10, W&B and the results database |
| Review of 349d7ef and your specs before Step 8 | Left-crossing patch, ego x/y logging, the contrastive failure window |
| Dashboard | The SAE realistic-prevalence retrain, as an arm on my code |
| | Dr. VLA licence email, writing and the poster |

Where one of us needs the other's output: the dev evaluation waits on your shards, and your Step 6 and probe-residual runs wait on mine.

## Small notes from my agent's pass (no rush)

- Contrastive still fires at "> 0.1, same as B7". B7 now uses the hysteresis, so contrastive should switch too so the two match.
- The SAE retrain on dev and test activations can't happen before Step 8, because the test activations only exist once Step 8 creates them. It probably belongs inside Step 8, before scoring.
- In the actor logging, every spawned prop counts as an obstacle, including the vending machine in ordinary pedestrian-crossing routes. The `walker.animal.` prefix also still needs checking on a live server.
