# Transfer spec: running a SimLingo-dev method on TransFuser++ and UniAD

**Status: draft, written 2026-11-16, before any method has read either held-out pool.** It becomes binding when the
freeze tag (prereg amendment A1, "Held-out confirmation") names it. Chris picks the finalists at that tag; this file
says how any finalist, and each rival, is run on a model it was not developed on.

**What has been read of the held-out pools so far:**
- one TransFuser++ test shard's array names, shapes and step spacing;
- UniAD's adapter code (`adapters/uniad/uniad_agent.py`).

No activation values and no outcomes have been read.

## Why a spec is needed

The dev methods are written in SimLingo's terms, for example "`driving_queries` layer 8, last 50 frames, PCA 32". The
held-out models have different stacks:

| model | `driving_queries` (the query the controller follows) | depth × width | `all_tokens` | `vision_bridge` | frame spacing |
|---|---|---|---|---|---|
| SimLingo | the driving query tokens of the language model | 24 × 896 | same 24 layers, every token | 896 | 5 sim steps |
| TransFuser++ | the decoder's checkpoint query (last `join` call) | 6 × 256 (measured, one shard) | same 6 layers, every query | 1512 | 5 sim steps (measured) |
| UniAD | the planning head's ego query | planning layers × 256 (depth read at the smoke export) | every hooked stage, 256 wide | 256 | 5 sim steps (adapter's export stride) |

All three write the same shard layout (`export_activations.py`), so `cache_pool.py` and `frames_pool.py` read them
unchanged.

## The mapping, fixed now

1. **Site.** `driving_queries` on every model. It is the representation the controller acts on in each, and every dev
   lead uses it.
2. **Layer.** By relative depth within the site:
   - SimLingo layer L is the fraction f = L / 23.
   - On a site of depth D, the layer is floor(f × (D − 1) + 0.5), via `cache_methods.depth_layers` and
     `--layer-fraction`.
   - On SimLingo it gives back L exactly; that is tested.
   - On TransFuser++ (D = 6), L5, L7, L8, L9 and L10 all map to layer 1 or 2 (L5 to 1, the rest to 2), and L20 maps
     to 4.
   - `frames_pool.py`'s default fractions (5/23, 8/23, 10/23, 20/23) follow the same rule. They differ only at an
     exact .5 tie, which none of the fractions here produces at D = 6.
3. **Window.** The same number of frames before the failure step (6, 20, 50 or 100). Frame spacing is 5 simulation
   steps on all three models, so a window covers the same driving time on each. A route with fewer frames uses all
   it has (`cache_pool.summaries`).
4. **Everything else unchanged.** PCA widths, clustering, cuts, mixture settings, pooling order and A2's
   distinct-axis rule stay as frozen. Each step is fit on the held-out model's own pool, with pass/fail as the only
   outcome read, as on dev. PCA widths up to 64 fit inside 256.
5. **Rivals, per model:**
   - **B3-behaviour:** `b3_behaviour.py` unchanged. TransFuser++ shards carry `ego_speed`, `step` and the infraction
     counts (measured); UniAD's are checked at its export.
   - **B3-infraction:** `b3_infractions.py` unchanged. Reported, with no pass bar (A2).
   - **B7-pool:** one dictionary per held-out model, trained on its `driving_queries` at fraction 10/23 (SimLingo
     L10), k = 64, seed 0, expansion ratio 1, the plain preparation. Then B7-pool's directive, as `L10_k64_s0` on
     SimLingo. One dictionary only, so the rival is not the best of a grid (A1).
   - **B1** (chance) as on dev. **B2** (with labels) as a ceiling only.
6. **Caches.**
   - `cache_pool.py` (windows 6 and 50, plus any window a finalist names) and `frames_pool.py` run on each held-out
     pool's shards only after the freeze tag.
   - They are mechanical and blind to the gaps. Their outputs are read only by the frozen methods and then the
     scorer.
7. **Gaps.**
   - TransFuser++: FullyBlocked and PedestriansOnRoad, as classified by the prereg rule (§1 and §2).
   - UniAD: gaps classified by the same rule on its own pool, before any method reads it.
   - Scoring as in A1 and A2: the headline is the pooled bootstrap across the two models, with gaps weighted equally;
     per-model and per-gap results are always shown beside it.

## What this means for the leads

- A lead that depends on one SimLingo layer moving by one step (m23 at whole-route L9, m41 at L19 or m12 L9; see
  "Lead robustness" in `VARIANTS.md`) cannot keep that precision on a 6-layer stack.
- On TransFuser++, layers 7 to 10 become one layer, so "layer 8 versus layer 9" is not a choice there.
- Leads whose neighbours score within 0.05 of them are the ones whose definition survives this mapping.
