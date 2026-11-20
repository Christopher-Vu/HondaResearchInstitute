#!/usr/bin/env bash
# LAPTOPWORKER 20261120-055952-26854, 2026-11-20. Exact commands, in order. Working directory: the clone root.
set -euo pipefail
export PYTHONPATH=src LOKY_MAX_CPU_COUNT=4
PY=/opt/miniconda3/bin/python
D=docs/research/experiments/f2d-dev-simlingo
POOL=results/savio/f2d-h21b/pool
H21B=results/h21/h21b
OUT=results/h21/j20
GAPS="--gaps F2D_CustomObstacles F2D_Wall F2D_PedestriansOnRoad --decoys F2D_Animals F2D_ConstructionPermutations F2D_ImageOnObject F2D_ObscuredStop F2D_PassableObstacles F2D_RightOfWay"
RIVALS="--rival B3_behaviour=$OUT/axes/b3_behaviour.json --reported-rival B3_infraction=$OUT/axes/b3_infraction.json --primary-rival B3_behaviour"
MAN="--manifest results/h21/j18/manifest-pair-fixed.json --routes $H21B/routes.jsonl"
mkdir -p $OUT/axes $OUT/seeds

# Rows committed (a5824c9) before anything below ran.
# Inputs, no score read.
$PY $D/cache_methods.py $POOL/cache.npz --method m03 --summary route --layer 8 --name route-L8 --output $OUT/axes/route-L8.json
$PY $D/b3_behaviour.py $POOL/cache.npz --output $OUT/axes/b3_behaviour.json
$PY $D/b3_infractions.py $POOL/cache.npz --output $OUT/axes/b3_infraction.json
$PY $D/j20_ssl.py $POOL/frames.npz --output $OUT/axes/j20-source.json
$PY $D/pool_axes.py --name j20-routeL8+ssl --source $OUT/axes/route-L8.json --source $OUT/axes/j20-source.json --output $OUT/axes/j20.json

# j20: try 224 + 1.
$PY $D/sprint_score.py --method $OUT/axes/j20.json $RIVALS $MAN $GAPS --tried 225 --label "EXPLORATORY DEV: SimLingo H21b pool only, seeds 24-26; j20, try 224 + 1 laptop try this batch; pair seed suffix stripped" --output $OUT/report-j20.json
