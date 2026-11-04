**Answered by Chris on 2026-11-04 in issue 8.** Kept as sent.

# Chris: four answers, counts only

Chris, this should take about 2 minutes. Jerry has asked to finish the study, and these counts decide which ending in `CONFLICTS.md` C34 it can reach. Please send numbers and yes or no only. Do not send a predicate, a scenario family or a parameter, because PRD 9.1 excludes anything written in a shared document from the sealed key.

Copy this, fill it in and send it back by 2026-11-18:

```text
1. Sealed candidates tried: __. Passed PRD 9.1: control __, enumerable __, interactional __.
   Of the interactional passes, expected B2 Jaccard under 0.4: __ (or "not checked").
2. Decoys that pass C31: visually novel __, kinematic __.
3. SU spent on the sealed work, roughly: __.
4. Does any sealed candidate's region contain or overlap:
   P19, oncoming traffic 1.2 m over the line on a bend, yes or no: __
   P20, oncoming traffic hidden by a camera patch, yes or no: __
```

Both definitions on line 4 are already public, so you do not need to open a file to answer. A yes removes that candidate only, so do not say which candidate it is. If line 4 has a yes, keep that candidate in "tried" on line 1 and leave it out of the "passed" counts, because PRD 9.1 reports every candidate tried.

| Line | What the answer unlocks |
|---|---|
| 1 | One control, one enumerable and two interactional gaps with expected B2 Jaccard under 0.4 keep the blind pool open (C34's ending B), and the pool gets sized for your real gap count. B2 is the list of scenario names. Step 5 and the preregistration's `key-v1` row bar an interactional gap that a single stratum scores at 0.4 or above, and P19 failed that test after passing 9.1. "Not checked" means that check comes before any pool work. With fewer than two such gaps, or with no control gap, PRD 13.1's first condition cannot hold unless more candidates pass, so we stop preparing a pool and write the dev-only report (ending A). The number tried goes beside every p value, as C34 requires. |
| 2 | One visually novel and one kinematic decoy complete Step 5's decoy requirement (PRD 9.1). A missing type needs its own decoy pilot before `key-v1`, and `docs/STATUS.md` still lists the kinematic decoy screen as needed from you. |
| 3 | Jerry can decide whether to fund the pool. At the logged rates of 2.63 to 7.85 SU a route, the smallest pool we can defend is estimated at 2,609 to 7,792 SU, and at 5,449 to 16,275 SU with B4's renders before any reuse (`harness/PREREGISTRATION.md`). B4 is a baseline that PRD 13.1's second condition must beat. His 10,000 SU budget has at most roughly 4,800 left. Neither range counts causal checks or re-screens. |
| 4 | Two noes mean the public P19 and P20 work has not touched your key. A yes takes that candidate out of the key under PRD 9.1 and tells us to stop public work on that region. |

If no answer comes by 2026-11-18, the study ends at ending A, and the report says that the PRD 13.1 test was not run.

**Route markers.** Every SimLingo route has run with `--debug 2` since 2026-10-02, which covers our pilots, the captured activations and any of your runs that went through `route_run.py`. The flag first appeared to date from 2026-10-05, when a later commit moved it. It draws route points and scenario trigger points into the world, and by our reading of the code and frames the policy camera films them. The effect on driving is unmeasured (`docs/WHAT_BROKE.md`), and running work still uses the same setting. H14 is a drafted paired test that has not run, at about 660 SU for its first 80 pairs (estimate), and C35 proposes keeping the flag for running work and running the blind pool at `--debug 0`. Both wait for your review and Jerry's.

Two more drafts are ready for you. `docs/research/conflicts-sheet.md` lists the default for each pending CONFLICTS entry. Its rows for C23, C29, C34 and P19 need an explicit yes from you, and they stay pending until you give it. Silence by 2026-11-18 accepts only the other rows. `harness/PREREGISTRATION.md` takes effect only when you and Jerry sign it and `prereg-v1` tags it.
