# adapters/

One directory per policy. Each adapter exposes the same three things to the rest
of the system (`PRD.md` §8.2):

1. **Rollouts** — run the policy in its environment, return per-episode
   observation/action sequences.
2. **Activations** — per-timestep internal state at a specified hook point,
   mean-pooled over tokens by default.
3. **Success labels** — a per-episode binary or scalar outcome.

## Read this before writing an interface

**`PRD.md` §8.2 says explicitly not to design this interface up front.** Build it
by refactoring *after* SimLingo works. The reasoning, from the original brief:
designing the abstraction first means spending the early weeks on abstraction
rather than on a working system, and the interface you guess will be wrong in ways
you cannot see until one real policy runs end to end.

So: `adapters/simlingo/` should be concrete, specific, and slightly ugly. The
generalisation is Step 11, and it is a refactor, not a design.

## Current state

- `simlingo/` — **in progress.** See `docs/steps/adapter-simlingo-brief.md` for
  what is in scope right now and what is deliberately not.
- `stub/` — not started. Step 11. A deliberately minimal adapter proving the
  interface is implementable by someone who has not read our code; this is what
  makes the generality claim credible.

## Hard constraint

Adapters depend only on `harness/` interfaces, never on each other
(`PRD.md` §14). An adapter that imports from another adapter has made the
interface untestable.
