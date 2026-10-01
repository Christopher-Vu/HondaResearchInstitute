# Working conventions

## Commits

- **Commit frequently.** Small, scoped commits over large ones. Commit as work
  lands, not at the end of a session.
- **Curt, concise messages.** One line, imperative mood, lowercase. A body only
  when the *why* is not obvious from the diff.
- **No attribution lines.** No `Co-Authored-By`, no "Generated with" footer.

Good: `add ray for rollout fan-out`, `fix d=896 storage arithmetic`,
`strike unverified dr.vla figures`

Bad: multi-paragraph rationale, trailing attribution, past tense.

## Documents

- `PRD.md` is the grounding document. Design decisions trace to the original
  brief (`docs/source/project-brief-original.md`), verifiable facts to the 99p
  handoff (`upstream-99p/docs/MASTER_HANDOFF.md`).
- Any divergence between those two sources gets an entry in `CONFLICTS.md` with
  reasoning. Reversing a prior decision means updating its entry, not deleting
  it.
- Never state a target as a result. Mark unverified claims as unverified.
- Log surprises in `docs/WHAT_BROKE.md` as they happen.

## Filesystem

Windows, case-insensitive. Filenames differing only in case are the same file —
`prd.md` and `PRD.md` collide. Check before writing a file whose name differs
from an existing one only by case.
