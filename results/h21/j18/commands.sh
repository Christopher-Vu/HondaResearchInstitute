#!/usr/bin/env bash
# LAPTOPWORKER 20261120-000900-16273, 2026-11-20. Exact commands, in order; all exited 0.
# Working directory: the clone root. On this clone the shared inputs sit one level deeper than the task text says:
# results/savio/f2d-h21b/pool/ is results/savio/savio/f2d-h21b/pool/, results/h21/h21b/ is results/h21/h21/h21b/.
set -euo pipefail
export PYTHONPATH=src LOKY_MAX_CPU_COUNT=4
PY=/opt/miniconda3/bin/python
D=docs/research/experiments/f2d-dev-simlingo
POOL=results/savio/savio/f2d-h21b/pool
H21B=results/h21/h21/h21b
OUT=results/h21/j18
GAPS="--gaps F2D_CustomObstacles F2D_Wall F2D_PedestriansOnRoad --decoys F2D_Animals F2D_ConstructionPermutations F2D_ImageOnObject F2D_ObscuredStop F2D_PassableObstacles F2D_RightOfWay"
RIVALS="--rival B3_behaviour=$OUT/axes/b3_behaviour.json --reported-rival B3_infraction=$OUT/axes/b3_infraction.json --primary-rival B3_behaviour"
MAN="--manifest $OUT/manifest-pair-fixed.json --routes $H21B/routes.jsonl"
mkdir -p $OUT/axes $OUT/seeds

# Inputs (no score read). route-L8 and both rivals were byte-compared with $H21B/axes/: identical axes.
$PY $D/cache_methods.py $POOL/cache.npz --method m03 --summary route --layer 8 --name route-L8 --output $OUT/axes/route-L8.json
$PY $D/j18_gmm.py $POOL/cache-w50.npz --output $OUT/axes/j18-source.json
$PY $D/pool_axes.py --name j18-routeL8+gmm --source $OUT/axes/route-L8.json --source $OUT/axes/j18-source.json --output $OUT/axes/j18.json
$PY - <<'PY'
import json, re
m = json.load(open('results/h21/h21/h21b/manifest.json'))
for e in m: e['pair'] = re.sub(r'-s\d+$', '', e['pair'])
json.dump(m, open('results/h21/j18/manifest-pair-fixed.json', 'w'), indent=1)
PY
# Rows committed here (912d34f), before any score.
$PY $D/b3_behaviour.py $POOL/cache.npz --output $OUT/axes/b3_behaviour.json
$PY $D/b3_infractions.py $POOL/cache.npz --output $OUT/axes/b3_infraction.json

# j18: try 219 + 1.
$PY $D/sprint_score.py --method $OUT/axes/j18.json $RIVALS $MAN $GAPS --tried 220 --label "EXPLORATORY DEV: SimLingo H21b pool only, seeds 24-26; j18, try 219 + 1 laptop try this batch; pair seed suffix stripped" --output $OUT/report-j18.json

# Check, not a try: m23 on the stripped-pair manifest.
$PY $D/sprint_score.py --method $H21B/axes/m23.json $RIVALS $MAN $GAPS --tried 220 --label "EXPLORATORY DEV: H21b; m23 rescore with pair suffix stripped, not a try" --output $OUT/check-m23.json

# Robustness, not tries: mixture seeds 1-5, 200 replicates.
for s in 1 2 3 4 5; do
  $PY $D/j18_gmm.py $POOL/cache-w50.npz --seed $s --name j18-seed$s --output $OUT/seeds/j18-source-seed$s.json
  $PY $D/pool_axes.py --name j18-seed$s --source $OUT/axes/route-L8.json --source $OUT/seeds/j18-source-seed$s.json --output $OUT/seeds/j18-seed$s.json
  $PY $D/sprint_score.py --method $OUT/seeds/j18-seed$s.json $RIVALS $MAN $GAPS --replicates 200 --tried 220 --label "EXPLORATORY DEV: H21b; j18 mixture seed $s, robustness, not a try" --output $OUT/seeds/report-j18-seed$s.json
done

# j19 row committed here (c3e1f9e), before its score. Try 219 + 2.
$PY $D/j18_gmm.py $POOL/cache-w50.npz --rank failure-rate --name j19 --output $OUT/axes/j19-source.json
$PY $D/pool_axes.py --name j19-routeL8+gmm-failrate --source $OUT/axes/route-L8.json --source $OUT/axes/j19-source.json --output $OUT/axes/j19.json
$PY $D/sprint_score.py --method $OUT/axes/j19.json $RIVALS $MAN $GAPS --tried 221 --label "EXPLORATORY DEV: SimLingo H21b pool only, seeds 24-26; j19, try 219 + 2 laptop tries this batch; pair seed suffix stripped" --output $OUT/report-j19.json
