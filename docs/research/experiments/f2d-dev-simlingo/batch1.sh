#!/usr/bin/env bash
# Sprint batch 1 on SimLingo (VARIANTS.md): the cache methods, then one scoring run against the rivals.
#   CMD='bash docs/research/experiments/f2d-dev-simlingo/batch1.sh m03 m04 m07' bash scripts/submit.sh cpu ... cpu.sbatch
# Scored under amendment A2 (prereg §8) since 2026-11-16; earlier batches used A1's B3-behaviour file.
# Each argument is a method run: a preset name below, or cache_methods.py options. MORE adds method files already
# written (pool_axes.py, b7_error_aware.py); CACHE replaces the cache. TRIED is the methods-tried count after this batch.
set -euo pipefail
E=docs/research/experiments/f2d-dev-simlingo
S=results/savio/f2d-dev/simlingo
V=$S/v1/plain/directives-ms20
OUT=$S/sprint/${BATCH:-batch1}
mkdir -p "$OUT"
declare -A PRESET=(
  [m03]="--method m03"
  [m04]="--method m04"
  [m07]="--method m07"
  [m06-m03]="--method m06 --base m03"
  [m06-m04]="--method m06 --base m04"
)
METHODS=()
for RUN in "$@"; do
  read -r -a OPTS <<< "${PRESET[$RUN]:-$RUN}"
  NAME=${RUN// /_}; NAME=${NAME//--/}
  python "$E/cache_methods.py" "${CACHE:-$S/cache.npz}" "${OPTS[@]}" ${EXTRA:-} --name "$NAME" --output "$OUT/$NAME.json"
  METHODS+=(--method "$OUT/$NAME.json")
done
for SPEC in ${MORE:-}; do
  METHODS+=(--method "$SPEC")
done
python "$E/sprint_score.py" "${METHODS[@]}" \
  --rival B3_behaviour="$S/sprint/a2/b3_behaviour.json" --rival B7_pool="$V:B7_pool:L10_k64_s0" \
  --reported-rival B3_infraction="$S/sprint/b3_infraction.json" ${RIVALS:-} \
  --manifest configs/rollout/f2d-test-simlingo.manifest.json --routes results/savio/f2d-test-simlingo/routes.jsonl \
  --gaps F2D_PedestriansOnRoad F2D_FullyBlocked F2D_BadParking \
  --decoys F2D_Animals F2D_ConstructionPermutations F2D_ImageOnObject F2D_ObscuredStop F2D_PassableObstacles F2D_RightOfWay \
  --tried "${TRIED:?}" --output "$OUT/report.json"
