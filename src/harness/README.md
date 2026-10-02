# src/harness

Config schema, scoring, metrics, and (later) the Ray runner and results DB.

`PREREGISTRATION.md` and `KEY_COMMITMENT.txt` live here too, next to the code
that reads them.

## Contents

- `PREREGISTRATION.md` — frozen before the test pool is generated. The go/no-go
  rule (`PRD.md` §13.1) and every pre-registered threshold live here. Once
  tagged, it is not edited; a change is a new version and gets reported as one.
- `KEY_COMMITMENT.txt` — `sha256(key || salt)`, committed before the test pool
  exists. This is what makes the blind claim checkable (`PRD.md` §9.1).

## Rules

- Every experiment is a YAML config under `configs/`. Results are keyed by
  config content hash.
- Nothing here imports from `gaps/sealed/`. CI enforces it.
