# Step 1 — Smallest possible SimLingo rollout on Savio

**Owner:** both. Jerry drives the cluster and container, Chris drives the agent
and config.
**Depends on:** Step 0 Track B item 3 — both of us have run a GPU job on Savio.
**Blocks:** Step 2 (reproduction) and, through the throughput number, §16.2.

**The goal is one route. Not the benchmark.** One route, one seed, commentary and
chain-of-thought off, in a container, from a versioned config, with wall-clock
and VRAM measured.

**Why so small.** SimLingo runs at roughly 0.045–0.065× real time and both source
planning documents independently say bring-up is where projects of this shape
die. The point of Step 1 is to find out *which* of five things is broken while
each failure is still cheap to attribute. Running 220 routes first means a
12-hour job that fails for an unknown reason.

---

## The five things that have to work, in dependency order

Do them in this order and stop at the first failure. Each stage has its own
failure mode and its own fallback, and a stage that fails tells you something
specific.

### 1.1 · Container with CARLA 0.9.15

- [ ] Determine the container runtime. **Savio almost certainly requires
      Singularity/Apptainer, not Docker** — HPC sites disallow Docker because it
      needs root. If a CARLA 0.9.15 image exists for Fail2Drive or Bench2Drive,
      convert it rather than building from scratch.
- [ ] Record the exact CARLA build. Fail2Drive ships a custom build; Bench2Drive
      expects 0.9.15. If these differ, note it now — it will matter at Step 10.
- [ ] CARLA server starts inside the container and accepts a client connection.

**Fallback if Docker→Singularity conversion fights you:** build from the CARLA
release tarball directly. Do not spend more than a day here.

### 1.2 · Off-screen rendering · **the most likely blocker**

- [ ] CARLA renders off-screen on a Savio GPU node, with no display attached.
      Try `-RenderOffScreen` first; `-opengl` and a virtual framebuffer
      (`xvfb-run`) are the usual fallbacks.
- [ ] A client can read a camera image and it is not black. **Check the pixels,
      not just the array shape.** A silently black camera feed will produce a
      policy that drives badly for reasons you will spend a week misattributing.

**If this fails after honest effort: stop and raise it.** This is a replan, not
a debugging session, and NRP becomes a serious candidate for rollouts rather
than just the describability model (`PRD.md` §17.4). Flagged as a known risk in
both source documents.

### 1.3 · SimLingo checkpoint loads

- [ ] Pull `RenzKa/simlingo` from Hugging Face. Record the **checkpoint SHA256** —
      every rollout record carries it (`PRD.md` §12.1).
- [ ] Model instantiates and does one forward pass on a dummy batch.
- [ ] **Read the architecture off the loaded config and write it down.** This
      closes `PRD.md` §16.11 and three downstream estimates depend on it:
      - `d` (hidden size). The handoff says 896; the SimLingo paper does not
        state it. **Every storage estimate in §12.1 and the SAE dictionary size
        in §12.2 scale with this number.**
      - number of decoder layers (handoff says 24);
      - the waypoint query token tensors `q_p` and `q_w`, and the MLP that reads
        them — this is the primary hook site at Step 3, so find it now while you
        are already in the model.
- [ ] Note which Bench2Drive version the repo targets (`PRD.md` §16.11). v0.0.3
      and v0.0.4 numbers are not comparable, and Step 2's pass/fail depends on
      knowing which one we are measuring against.

### 1.4 · One route, closed loop

- [ ] Pick one short Bench2Drive route. Prefer a dull one — a route whose
      scenario is not in the known-weak ability list (`PRD.md` §10.1) — so that a
      failure is informative rather than expected.
- [ ] **Commentary and CoT off** (`PRD.md` §10.1, D4).
- [ ] The agent completes the route and Bench2Drive writes its result JSON.
- [ ] Record: wall-clock, simulated seconds, peak VRAM for the whole
      container including the CARLA server, and the infraction list.

### 1.5 · Measure, and fix the budget

- [ ] Compute the **real-time factor** = simulated seconds / wall-clock seconds.
      Expect something near 0.045–0.065 based on third-party reports; a value far
      from that means something is wrong or something is much better than
      expected, and either is worth knowing.
- [ ] Extrapolate to the numbers the plan actually needs, and write them into
      `PRD.md` §17.3:
      - 220 routes × 3 seeds (Step 2 and every regression check);
      - a 600–1,000-rollout dev pool (Step 4);
      - a 1,500–2,500-rollout test pool (Step 8);
      - efficacy pilots at ~60 rollouts per candidate tried (Step 5);
      - B4's factor × level × run matrix (Step 6).
- [ ] **Close `PRD.md` §16.2 — the gap portfolio size.** It is budget-bound, and
      this measurement plus the SU rate from Step 0 Track B is the budget. If the
      arithmetic says 4–6 gaps plus 2 decoys does not fit, the portfolio shrinks
      now, before Step 5 writes predicates.

---

## Done condition

1. One rollout completes on a Savio GPU node, in the container, from a config
   committed under `configs/`.
2. Wall-clock, real-time factor and peak VRAM are recorded.
3. `d`, the layer count, the query-token location and the Bench2Drive version are
   written into `PRD.md`, replacing the §16.11 placeholders.
4. §17.3's budget estimates are replaced with measured extrapolations, and §16.2
   is closed.
5. The config is versioned and the run is reproducible by whichever of us did not
   set it up.

## Explicitly not in this step

No hooks and no activation capture — that is Step 3, and it needs the query-token
location this step finds. No benchmark run; that is Step 2. No Ray; one route does
not need orchestration, and introducing it here would confuse two failure modes.
No gap predicates, no SAE, no adapter interface.

## Notes

- **Log the real-time factor even if everything else fails.** It is the single
  number that determines whether the November-equivalent closed loop runs twice,
  once, or never, and it is the input to every budget decision downstream.
- If the measured throughput is much worse than the third-party reports, check
  whether inference is running every frame. The 0.08× figure in the literature
  comes from a fork running the VLM every 5th frame and reusing controls in
  between — which is *not* the released configuration and is not what we want for
  activation capture, since we need per-step internals.
- Expect the route to be imperfect. A single route's result says almost nothing
  about policy quality; it says the plumbing works. Resist reading DS off one
  route.
- Put anything surprising in `docs/WHAT_BROKE.md` as it happens.
