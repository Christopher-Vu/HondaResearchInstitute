#!/usr/bin/env bash
# Laptop worker 20261120-001014-14644. Run from the clone root. Exploratory, dev, H21b only.
set -euo pipefail
PY=/opt/miniconda3/bin/python
POOL=results/savio/savio/f2d-h21b/pool
H21B=results/h21/h21/h21b
OUT=results/h21/j16
D=docs/research/experiments/f2d-dev-simlingo
export PYTHONPATH=src
mkdir -p $OUT/axes

# Manifest copy with pair = base pair (seed suffix stripped), so the bootstrap resamples 100 Fail2Drive pairs (A1).
$PY - "$H21B/manifest.json" "$OUT/manifest-basepair.json" <<'PY'
import json, re, sys
rows = json.load(open(sys.argv[1]))
for row in rows:
    row["pair"] = re.sub(r"-s\d+$", "", row["pair"])
json.dump(rows, open(sys.argv[2], "w"), indent=1)
print("pairs", len({r["pair"] for r in rows}), "routes", len(rows))
PY

$PY $D/j16_change.py $POOL/frames.npz --output $OUT/axes/j16.json
$PY $D/cache_methods.py $POOL/cache.npz --method m03 --summary route --layer 8 --name route-L8 --output $OUT/axes/route-L8.json
$PY $D/b3_behaviour.py $POOL/cache.npz --output $OUT/axes/b3_behaviour.json
$PY $D/b3_infractions.py $POOL/cache.npz --output $OUT/axes/b3_infraction.json
$PY $D/pool_axes.py --name j16+route --source $OUT/axes/route-L8.json --source $OUT/axes/j16.json --output $OUT/axes/j16+route.json

score() {  # $1 method axes, $2 tried, $3 report
  $PY $D/sprint_score.py --method "$1" --rival B3_behaviour=$OUT/axes/b3_behaviour.json \
    --reported-rival B3_infraction=$OUT/axes/b3_infraction.json --primary-rival B3_behaviour \
    --manifest $OUT/manifest-basepair.json --routes $H21B/routes.jsonl \
    --gaps F2D_CustomObstacles F2D_Wall F2D_PedestriansOnRoad \
    --decoys F2D_Animals F2D_ConstructionPermutations F2D_ImageOnObject F2D_ObscuredStop F2D_PassableObstacles F2D_RightOfWay \
    --tried "$2" --label "EXPLORATORY DEV: SimLingo H21b pool, seeds 24-26, laptop j16" --output "$3"
}
score $OUT/axes/j16.json 220 $OUT/report-j16.json
score $OUT/axes/j16+route.json 221 $OUT/report-j16+route.json
# Reference rescore (not a try): m23 from the recorded axes on the corrected unit, as a check against 0.395.
score $H21B/axes/m23.json 221 $OUT/report-m23-check.json

# j17 (written after j16+route scored below m23; row committed before this ran). Only the pooled row is a try.
$PY $D/j16_change.py $POOL/frames.npz --direction --output $OUT/axes/j17.json
$PY $D/pool_axes.py --name j17+route --source $OUT/axes/route-L8.json --source $OUT/axes/j17.json --output $OUT/axes/j17+route.json
score $OUT/axes/j17+route.json 222 $OUT/report-j17+route.json
