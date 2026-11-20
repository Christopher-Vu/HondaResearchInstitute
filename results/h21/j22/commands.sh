#!/usr/bin/env bash
# LAPTOPWORKER 20261120-055955-27931, 2026-11-20. Exact commands, in order. Run from the clone root with bash.
# Usage: bash results/h21/j22/commands.sh [inputs|j22|seeds|j23|all]
set -euo pipefail
export PYTHONPATH=src LOKY_MAX_CPU_COUNT=4
PY=/opt/miniconda3/bin/python
D=docs/research/experiments/f2d-dev-simlingo
POOL=results/savio/f2d-h21b/pool
H21B=results/h21/h21b
OUT=results/h21/j22
GAPS="--gaps F2D_CustomObstacles F2D_Wall F2D_PedestriansOnRoad --decoys F2D_Animals F2D_ConstructionPermutations F2D_ImageOnObject F2D_ObscuredStop F2D_PassableObstacles F2D_RightOfWay"
RIVALS="--rival B3_behaviour=$OUT/axes/b3_behaviour.json --reported-rival B3_infraction=$OUT/axes/b3_infraction.json --primary-rival B3_behaviour"
MAN="--manifest $OUT/manifest-pair-fixed.json --routes $H21B/routes.jsonl"
PART=${1:-all}

if [[ $PART == inputs || $PART == all ]]; then
  # Inputs, no score read. route-L8 and both rivals were compared with the recorded axes: identical.
  mkdir -p $OUT/axes $OUT/seeds
  $PY $D/cache_methods.py $POOL/cache.npz --method m03 --summary route --layer 8 --name route-L8 --output $OUT/axes/route-L8.json
  $PY $D/j22_dict.py $POOL/frames.npz --output $OUT/axes/j22-source.json
  $PY $D/pool_axes.py --name j22-routeL8+dict --source $OUT/axes/route-L8.json --source $OUT/axes/j22-source.json --output $OUT/axes/j22.json
  cp results/h21/j18/manifest-pair-fixed.json $OUT/manifest-pair-fixed.json   # pair with -sNN stripped, 100 pairs
  $PY $D/b3_behaviour.py $POOL/cache.npz --output $OUT/axes/b3_behaviour.json
  $PY $D/b3_infractions.py $POOL/cache.npz --output $OUT/axes/b3_infraction.json
fi
# j22 row committed here (56ecbf5), before any score.

if [[ $PART == j22 || $PART == all ]]; then
  # j22: try 224 + 1.
  $PY $D/sprint_score.py --method $OUT/axes/j22.json $RIVALS $MAN $GAPS --tried 225 --label "EXPLORATORY DEV: SimLingo H21b pool only, seeds 24-26; j22, try 224 + 1 laptop try this batch; pair seed suffix stripped" --output $OUT/report-j22.json
fi

if [[ $PART == seeds || $PART == all ]]; then
  # Robustness, not tries: dictionary seeds 1-3, 200 replicates.
  for s in 1 2 3; do
    $PY $D/j22_dict.py $POOL/frames.npz --seed $s --name j22-seed$s --output $OUT/seeds/j22-source-seed$s.json
    $PY $D/pool_axes.py --name j22-seed$s --source $OUT/axes/route-L8.json --source $OUT/seeds/j22-source-seed$s.json --output $OUT/seeds/j22-seed$s.json
    $PY $D/sprint_score.py --method $OUT/seeds/j22-seed$s.json $RIVALS $MAN $GAPS --replicates 200 --tried 225 --label "EXPLORATORY DEV: H21b; j22 dictionary seed $s, robustness, not a try" --output $OUT/seeds/report-j22-seed$s.json
  done
fi
# j22 row filled and j23 row committed here (9ad327e), before j23's score.

if [[ $PART == j23 || $PART == all ]]; then
  # j23: try 224 + 2. j22 with the late active-share columns dropped.
  $PY $D/j22_dict.py $POOL/frames.npz --columns change --name j23 --output $OUT/axes/j23-source.json
  $PY $D/pool_axes.py --name j23-routeL8+dict-change --source $OUT/axes/route-L8.json --source $OUT/axes/j23-source.json --output $OUT/axes/j23.json
  $PY $D/sprint_score.py --method $OUT/axes/j23.json $RIVALS $MAN $GAPS --tried 226 --label "EXPLORATORY DEV: SimLingo H21b pool only, seeds 24-26; j23, try 224 + 2 laptop tries this batch; pair seed suffix stripped" --output $OUT/report-j23.json
fi
