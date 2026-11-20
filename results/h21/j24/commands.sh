#!/usr/bin/env bash
# LAPTOPWORKER 20261120-055958-30070, 2026-11-20. Exact commands, in order, from the clone root. Exploratory, dev, H21b only.
set -euo pipefail
export PYTHONPATH=src LOKY_MAX_CPU_COUNT=4
PY=/opt/miniconda3/bin/python
D=docs/research/experiments/f2d-dev-simlingo
POOL=results/savio/f2d-h21b/pool
H21B=results/h21/h21b
OUT=results/h21/j24
GAPS="--gaps F2D_CustomObstacles F2D_Wall F2D_PedestriansOnRoad --decoys F2D_Animals F2D_ConstructionPermutations F2D_ImageOnObject F2D_ObscuredStop F2D_PassableObstacles F2D_RightOfWay"
RIVALS="--rival B3_behaviour=$OUT/axes/b3_behaviour.json --reported-rival B3_infraction=$OUT/axes/b3_infraction.json --primary-rival B3_behaviour"
MAN="--manifest results/h21/j18/manifest-pair-fixed.json --routes $H21B/routes.jsonl"
mkdir -p $OUT/axes $OUT/alpha

# Inputs (no score read). Row committed in e3a3031 before any of this ran.
$PY $D/cache_methods.py $POOL/cache.npz --method m03 --summary route --layer 8 --name route-L8 --output $OUT/axes/route-L8.json
$PY $D/b3_behaviour.py $POOL/cache.npz --output $OUT/axes/b3_behaviour.json
$PY $D/b3_infractions.py $POOL/cache.npz --output $OUT/axes/b3_infraction.json
for f in route-L8 b3_behaviour b3_infraction; do
  $PY -c "import json,sys; a=lambda p:[x['rollouts'] for x in json.load(open(p))['axes']]; sys.exit(a('$OUT/axes/$f.json')!=a('$H21B/axes/$f.json'))" && echo "$f equals recorded"
done
$PY $D/j24_ar.py $POOL/frames.npz --output $OUT/axes/j24-source.json
$PY $D/pool_axes.py --name j24-routeL8+ar --source $OUT/axes/route-L8.json --source $OUT/axes/j24-source.json --output $OUT/axes/j24.json

# j24: try 224 + 1.
$PY $D/sprint_score.py --method $OUT/axes/j24.json $RIVALS $MAN $GAPS --tried 225 --label "EXPLORATORY DEV: SimLingo H21b pool only, seeds 24-26; j24, try 224 + 1 laptop try this batch; pair seed suffix stripped" --output $OUT/report-j24.json

# Robustness, not tries: ridge alpha 0.3x and 3x, 200 replicates.
for a in 0.3 3.0; do
  $PY $D/j24_ar.py $POOL/frames.npz --alpha $a --name j24-alpha$a --output $OUT/alpha/j24-source-alpha$a.json
  $PY $D/pool_axes.py --name j24-alpha$a --source $OUT/axes/route-L8.json --source $OUT/alpha/j24-source-alpha$a.json --output $OUT/alpha/j24-alpha$a.json
  $PY $D/sprint_score.py --method $OUT/alpha/j24-alpha$a.json $RIVALS $MAN $GAPS --replicates 200 --tried 225 --label "EXPLORATORY DEV: H21b; j24 ridge alpha $a, robustness, not a try" --output $OUT/alpha/report-j24-alpha$a.json
done

# j25 row committed in bd90938 (reason from j24's own features, below), before its score. Try 224 + 2.
# Label-free diagnostic that gave the reason (no key read): which block carries j24's first Ward split.
$PY - <<'PY'
import importlib.util, json
import numpy as np
from scipy.cluster.hierarchy import fcluster, linkage
spec = importlib.util.spec_from_file_location("j24", "docs/research/experiments/f2d-dev-simlingo/j24_ar.py")
j24 = importlib.util.module_from_spec(spec); spec.loader.exec_module(j24)
z = np.load("results/savio/f2d-h21b/pool/frames.npz")
fail = np.array([not json.loads(str(m))["success"] for m in z["meta"]])
F = j24.j24_features(np.asarray(z["frames"][:, 1], dtype=np.float64), z["n_frames"])[fail]
lab = fcluster(linkage(F, "ward"), 2, "maxclust")
for name, cols in (("direction", slice(0, 16)), ("norm profile", slice(16, 19))):
    B = F[:, cols]
    between = sum((lab == c).sum() * ((B[lab == c].mean(0) - B.mean(0)) ** 2).sum() for c in (1, 2))
    print(name, "between-split share", round(float(between / ((B - B.mean(0)) ** 2).sum()), 3))
PY
$PY $D/j24_ar.py $POOL/frames.npz --direction-only --output $OUT/axes/j25-source.json
$PY $D/pool_axes.py --name j25-routeL8+ardir --source $OUT/axes/route-L8.json --source $OUT/axes/j25-source.json --output $OUT/axes/j25.json
$PY $D/sprint_score.py --method $OUT/axes/j25.json $RIVALS $MAN $GAPS --tried 226 --label "EXPLORATORY DEV: SimLingo H21b pool only, seeds 24-26; j25, try 224 + 2 laptop tries this batch; pair seed suffix stripped" --output $OUT/report-j25.json
