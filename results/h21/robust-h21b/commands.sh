#!/usr/bin/env bash
# H21b robustness rescores (VARIANTS.md "H21b robustness"). Rescores, not tries: the count stays 219.
# Run from the repo root of a clean clone with the pooled H21b inputs in place:
#   POOL  = the pool builder's output dir (cache.npz, cache-w50.npz, frames.npz)
#   H21B  = results/h21/h21b (manifest.json, routes.jsonl, axes/ and report-*.json of the recorded run)
# Large subset archives go to WORK, outside the repo.
set -euo pipefail

PY=${PY:-/opt/miniconda3/bin/python}
POOL=${POOL:-results/savio/savio/f2d-h21b/pool}
H21B=${H21B:-results/h21/h21/h21b}
WORK=${WORK:-${TMPDIR:-/tmp}/robust-h21b}
OUT=results/h21/robust-h21b
D=docs/research/experiments/f2d-dev-simlingo
export PYTHONPATH=src
GAPS=(F2D_CustomObstacles F2D_Wall F2D_PedestriansOnRoad)
DECOYS=(F2D_Animals F2D_ConstructionPermutations F2D_ImageOnObject F2D_ObscuredStop F2D_PassableObstacles F2D_RightOfWay)

# build_axes INPUT_DIR AXES_DIR: every method refit on the rows of INPUT_DIR, settings as $H21B/commands.sh.
build_axes() {
  local in=$1 ax=$2
  mkdir -p "$ax"
  "$PY" $D/cache_methods.py "$in/cache-w50.npz" --method m03 --layer 8 --name m15-source --output "$ax/m15-source.json"
  "$PY" $D/cache_methods.py "$in/cache.npz" --method m03 --summary route --layer 8 --name route-L8 --output "$ax/route-L8.json"
  "$PY" $D/cache_methods.py "$in/cache-w50.npz" --method m03 --layer 8 --dims 64 --name m39-source --output "$ax/m39-source.json"
  "$PY" $D/cache_methods.py "$in/cache.npz" --method m03 --summary route --layer 20 --name route-L20 --output "$ax/route-L20.json"
  "$PY" $D/j09_hmm.py "$in/frames.npz" --output "$ax/j09.json"
  "$PY" $D/b3_behaviour.py "$in/cache.npz" --output "$ax/b3_behaviour.json"
  "$PY" $D/b3_infractions.py "$in/cache.npz" --output "$ax/b3_infraction.json"
  "$PY" $D/pool_axes.py --name m23-w50L8+routeL8 --source "$ax/m15-source.json" --source "$ax/route-L8.json" --output "$ax/m23.json"
  "$PY" $D/pool_axes.py --name m40-w50L8pca64+routeL20 --source "$ax/m39-source.json" --source "$ax/route-L20.json" --output "$ax/m40.json"
}

# score METHOD_AXES AXES_DIR ROUTES MANIFEST LABEL REPORT [SEED [BUDGET]]: sprint_score.py, rivals from AXES_DIR.
# BUDGET != 10 sets sprint_score.M without editing the file (sensitivity rows only).
score() {
  local method=$1 ax=$2 routes=$3 manifest=$4 label=$5 report=$6 seed=${7:-0} budget=${8:-10}
  "$PY" -c 'import importlib.util, sys
spec = importlib.util.spec_from_file_location("sprint_score", sys.argv[1]); s = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s); s.M = int(sys.argv[2]); sys.argv = [sys.argv[1], *sys.argv[3:]]; s.main()' \
    $D/sprint_score.py "$budget" \
    --method "$method" --rival B3_behaviour="$ax/b3_behaviour.json" --reported-rival B3_infraction="$ax/b3_infraction.json" \
    --primary-rival B3_behaviour --manifest "$manifest" --routes "$routes" --gaps "${GAPS[@]}" --decoys "${DECOYS[@]}" \
    --tried 219 --seed "$seed" --label "$label" --output "$report"
}

# run_pool NAME INPUT_DIR ROUTES MANIFEST LABEL: axes, five reports, m23 at bootstrap seeds 0, 1, 2.
run_pool() {
  local name=$1 in=$2 routes=$3 manifest=$4 label=$5
  local ax=$OUT/$name/axes
  build_axes "$in" "$ax"
  for m in m40 j09; do score "$ax/$m.json" "$ax" "$routes" "$manifest" "$label" "$OUT/$name/report-$m.json"; done
  score "$ax/b3_behaviour.json" "$ax" "$routes" "$manifest" "$label" "$OUT/$name/report-B3-behaviour.json"
  score "$ax/b3_infraction.json" "$ax" "$routes" "$manifest" "$label" "$OUT/$name/report-B3-infraction.json"
  for seed in 0 1 2; do
    score "$ax/m23.json" "$ax" "$routes" "$manifest" "$label" "$OUT/$name/report-m23-seed$seed.json" "$seed"
  done
}

# Corrected manifest (A1): pair = base_id without -sNN.
"$PY" $OUT/pool_inputs.py manifest "$H21B/manifest.json" $OUT/manifest.json

# Step 2: full pool, corrected manifest. Stops here unless axes and point scores equal the recorded run.
run_pool full "$POOL" "$H21B/routes.jsonl" $OUT/manifest.json "DEV: SimLingo H21b robustness, seeds 24-26; rescore, not a try"
"$PY" $OUT/summarize.py check --recorded "$H21B" --out $OUT

# Steps 3 and 4: one seed, and leave one seed out. Pool rows subset, methods refit on them.
subset_and_run() {
  local name=$1; shift
  "$PY" $OUT/pool_inputs.py subset "$POOL" "$H21B/routes.jsonl" $OUT/manifest.json --seeds "$@" --out "$WORK/$name"
  run_pool "$name" "$WORK/$name" "$WORK/$name/routes.jsonl" "$WORK/$name/manifest.json" \
    "DEV: SimLingo H21b robustness, seeds $*; rescore, not a try"
}
# wait_all PIDS: fails if any background pool failed.
wait_all() { local pid; for pid in "$@"; do wait "$pid"; done; }
subset_and_run s24 24 & a=$!; subset_and_run s25 25 & b=$!; subset_and_run s26 26 & c=$!; wait_all $a $b $c
subset_and_run no24 25 26 & a=$!; subset_and_run no25 24 26 & b=$!; subset_and_run no26 24 25 & c=$!; wait_all $a $b $c

# Step 6 (exploratory): m23 on the full pool, one setting changed. Rivals and route-L8 stay as in "full".
SENS=$OUT/sensitivity
FULL=$OUT/full/axes
SLABEL="DEV: SimLingo H21b robustness, seeds 24-26; m23 sensitivity, exploratory; rescore, not a try"
mkdir -p "$WORK/full" "$SENS"
"$PY" $OUT/pool_inputs.py window "$POOL/frames.npz" "$POOL/cache.npz" --last 50 --out "$WORK/full/cache-w50-rebuilt.npz" \
  --expect "$POOL/cache-w50.npz"
"$PY" $OUT/pool_inputs.py window "$POOL/frames.npz" "$POOL/cache.npz" --last 20 --out "$WORK/full/cache-w20.npz"
"$PY" $D/cache_methods.py "$WORK/full/cache-w20.npz" --method m03 --layer 8 --name m15-source-w20 --output $SENS/m15-source-w20.json
"$PY" $D/pool_axes.py --name m23-w20L8+routeL8 --source $SENS/m15-source-w20.json --source $FULL/route-L8.json --output $SENS/m23-W20.json
score $SENS/m23-W20.json $FULL "$H21B/routes.jsonl" $OUT/manifest.json "$SLABEL" $SENS/report-m23-W20.json
# W = 100 is not run: frames.npz stores at most 50 frames per route; the next line exits non-zero by design.
"$PY" $OUT/pool_inputs.py window "$POOL/frames.npz" "$POOL/cache.npz" --last 100 --out "$WORK/full/cache-w100.npz" || true
for cap in 5 10 15; do
  "$PY" $OUT/pool_inputs.py round-robin --cap $cap --name m23-w50L8+routeL8 \
    --source $FULL/m15-source.json --source $FULL/route-L8.json --output $SENS/m23-M$cap.json
done
cmp <("$PY" -c 'import json,sys; print(json.load(open(sys.argv[1]))["axes"])' $SENS/m23-M10.json) \
    <("$PY" -c 'import json,sys; print(json.load(open(sys.argv[1]))["axes"])' $FULL/m23.json)
score $SENS/m23-M5.json $FULL "$H21B/routes.jsonl" $OUT/manifest.json "$SLABEL" $SENS/report-m23-M5.json 0 10
score $SENS/m23-M15.json $FULL "$H21B/routes.jsonl" $OUT/manifest.json "$SLABEL" $SENS/report-m23-M15.json 0 15

# The tables in report.md.
"$PY" $OUT/summarize.py tables --recorded "$H21B" --out $OUT > $OUT/tables.md
