# Conflicts sheet: defaults, and what accepts each one

Draft of 2026-11-04, read from `CONFLICTS.md`. Nobody has approved any of this.

**The date is 2026-11-18.** The rows marked "Needs Chris's yes" (C23, C29, C34 and P19) take effect only on an explicit yes from Chris, and silence never accepts them. If no yes comes they stay pending, and C23's own text keeps PRD 9.1's rule in force. Every other row takes effect if nobody has objected by that date. An objection stops that row alone. C35 stays pending under its own review. Acting on a row means updating its CONFLICTS entry, not deleting it.

## Pending, C20 to C34

| Entry | Default | Reason |
|---|---|---|
| C20 CARLA from the tarball | Accept. | Steps 1 and 2 and every pilot ran on the checksummed tarball, and no working container recipe for 0.9.15 was found. |
| C21 dev pool and practice gaps | Accept. | The pool has already grown past 190 in three waves, and practice gaps never enter the key, so they need efficacy and not absence from training. |
| C22 replay condition | Accept replay against replay. | Three replays agree to 0.0 m (measured), and causal checks only ever compare replays. |
| C23 efficacy sizing and pairing | **Needs Chris's yes.** Adopt the paired rule for test-pool re-confirmation: McNemar p < 0.01, uplift at least 20, ratio at least 2, at least 60 pairs from 30 bases. Locked dev protocols keep Fisher as their verdict, and both are reported. | Every pilot is already paired, and the passing ones show 31 to 46 slice-only failures against 0 (measured). C23 says PRD 9.1's rule stands until this is accepted, so this row changes the rule of record for test-pool re-confirmation. |
| C24 treatment check, shuffled order | Accept both, and a check counts only if it has been shown able to fail. | H5's check counted early braking as no hazard, and the 50 m clause passed 332 of 332 rows (`docs/WHAT_BROKE.md`). |
| C25 B8 log-based baseline | Accept as required, with a different vision model from the gate. Its targeted arm runs only if 13.1 reaches the closed loop. | It costs no rollouts, and it is a reviewer's first answer to "did you need the internals?" |
| C26 narrower novelty claim | Accept, and the paper never says "first". | SPHINX, Gupta et al. and Motzkus & Bernhard each published part of the old claim. |
| C27 three discovery checks | Accept all three, using the 2026-10-15 correction for the first. | They cost no rollouts, and the catch-all axis they guard against was measured. |
| C28 overnight choices | Accept for dev only. A pilot starts automatically only where a locked protocol names it. | P14's screen read 8 of 10 against 3 of 9, and its pilot read 30 of 58 against 21 of 58 (measured). |
| C29 B3 without expert error | **Needs Chris's yes.** Run B3 without expert error on dev and on the pool, and state the omission (`harness/PREREGISTRATION.md`, section 1). This default departs from C29's advice to add the expert block before the go/no-go read. | An expert run beside every rollout costs about another pool (estimate). A weaker B3 favours the activation methods, because condition 2 requires beating every baseline, so this has to be a decision and cannot pass by silence. |
| C32 blind-spot control | Do not adopt for the first pool, and leave the entry open. | It is unbuilt, 13.1 does not need it, and SU is short. |
| C33 CI off | Keep CI off until Step 8 starts, then restore `on: [push, pull_request]` before `key-v1`. | The entry itself says the guard matters from sealing onward. |
| C34 how the end is reported | **Needs Chris's yes.** Apply as written. | It was written before P20's screen was read, so the wording cannot follow the result. The agent wrote this entry, so it needs its reviewer's yes. |

## Already resolved

| Entry | State |
|---|---|
| C30 B4 factor list | Committed and tagged `b4-factors-v1`, and the entry is not marked pending. A change can only be a v2. |
| C31 decoy rule | Chris decided it and reversed part of it on 2026-10-23, so one rule covers all decoys. No code under `src/`, `scripts/` or `adapters/` applies it yet. |

## Decisions that sit outside a C entry

| Decision | Default | Reason |
|---|---|---|
| P7 at 56 pairs | Accept, with no replacement pairs, and report the count. | It passes 9.1: 53 of 56 against 15 of 60, p 2e-15 (measured). All four lost routes were slices and crashed twice, so the loss could bias the result. The worst case counts all four as non-failures: 53 of 60 against 15 of 60 gives uplift 63.3, ratio 3.53 and p 1e-12, which still passes (arithmetic). A new draw would change the seeded base list, and public gaps cannot enter the key. |
| P8 at 58 pairs | Accept on the same terms. | It passes 9.1: 58 of 58 against 12 of 60, p 5e-22 (measured). Both lost routes were slices and crashed again on rerun. The worst case counts both as non-failures: 58 of 60 against 12 of 60 gives uplift 76.7, ratio 4.83 and p 3e-19, which still passes (arithmetic). |
| Bases 3048 and 3800 | Exclude from new draws, and leave existing draws alone. | These roads crash CARLA under a camera fault, while their twins finish: 304841, 380041 and 380048 completed with success true (measured, `routes.jsonl`). The slices 304831, 380031 and 380038 crashed at about the same point on both runs, which shows that the crash repeats and does not show that the road alone causes it. All six routes lost in P7 and P8 are slices, so the loss is a possible bias and not plain bad luck. |
| Is P19 enumerable? | **Needs Chris's yes.** Not interactional under Step 5, and it behaves as enumerable on this pool. Report it as "passes 9.1, fails Step 5's single-factor condition", and it never counts toward 13.1's two interactional gaps. | B2 scores 0.857 against the limit of 0.4 (measured, H12). PRD 9.1 defines enumerable as a single factor any reasonable list would name, and this evidence shows only that P19 fails Step 5's test. A single-family gap gets below 0.4 only if its family fails more often outside the pilot than the gap fails inside it (arithmetic, H13). So any single-family gap gets the same label, including PRD 9.1's illustrated interactional candidates, and a single-family sealed candidate would fail the same way. Being public, P19 is excluded from the key anyway. |

## Also pending, outside this range

C35 (route markers) is a draft pending Jerry and Chris. Its proposal is to keep `--debug 2` for running work until H14 reads and to run the blind pool at `--debug 0` under every verdict. The config key is `simulator.debug_level`. `harness/PREREGISTRATION.md` section 4 lists what that decision must settle first.
