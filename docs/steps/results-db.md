# Results database

`PRD.md` §6.2: no result that cannot be regenerated from a config hash.
`gpu-free-queue.md` item 7. Owner: Chris. Status: proposed 2026-10-15, no code
until signed off.

## What it is

A SQLite file **derived** from the result folders, never edited by hand. The
folders (`results/savio/<job>/`, each scorer's `summary.json`, `routes.jsonl`,
`efficacy.json`) stay the source of truth; one ingest script rebuilds the
database from them, so losing it costs one rerun of the script.

| Table | One row per | Columns |
|---|---|---|
| `configs` | config file version | content hash, path, git commit, YAML text |
| `runs` | Slurm job or array | job id, config hash, kind (routes, scoring, sweep, pilot), user, start, end, SU, node list, result path |
| `routes` | route attempt | run, route id, outcome, driving score, completion, infractions (JSON), simulated and wall seconds, node, chosen (the attempt the scorer used) |
| `metrics` | reported number | run, name, value, source file and key |

A paper number is a query over `metrics` joined to `configs`; its provenance is
the row's source file and the config's commit.

## Rules

- The ingest reads only what the scorers already write. It does not re-score.
- Sealed gaps: before the Step 8 reveal, the database holds test-pool outcomes
  but no predicates and no per-gap scores; the scoring code alone writes those,
  after the reveal.
- W&B is for Step 10 training curves. It is not a second results store.
- The node list in `runs` is there because of `docs/WHAT_BROKE.md`: three bad
  A40 nodes so far were found by reading logs by hand.

## Done when

Every measured number in `docs/STATUS.md` for Step 1, Step 2 and P4 comes back
from a query, matching the scorer's file exactly.

## Open

- Where it lives: built on Savio (the folders are there) and copied to laptops,
  or built on a laptop from synced summaries only.
- Whether `routes` also takes per-step state, or that stays in the shards.
