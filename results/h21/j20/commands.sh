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

# Robustness, not tries: training seeds 1-3, 200 replicates.
for s in 1 2 3; do
  $PY $D/j20_ssl.py $POOL/frames.npz --seed $s --name j20-seed$s --output $OUT/seeds/j20-source-seed$s.json
  $PY $D/pool_axes.py --name j20-seed$s --source $OUT/axes/route-L8.json --source $OUT/seeds/j20-source-seed$s.json --output $OUT/seeds/j20-seed$s.json
  $PY $D/sprint_score.py --method $OUT/seeds/j20-seed$s.json $RIVALS $MAN $GAPS --replicates 200 --tried 225 --label "EXPLORATORY DEV: H21b; j20 training seed $s, robustness, not a try" --output $OUT/seeds/report-j20-seed$s.json
done
# The loop above was first run from zsh, which does not split $GAPS; its three score calls failed with a usage error
# and were rerun under bash with the same arguments. Training outputs were unaffected.

# Label-free diagnostics behind the j21 row (no key read): ridge R² of each seed's embedding from the route mean of
# its PCA-64 inputs, and best-match Jaccard of j20's axes with m15, route-L8 and the other seeds. Printed, not saved.
$PY - <<'DIAG'
import importlib.util, json
import numpy as np
from sklearn.linear_model import RidgeCV
from sklearn.model_selection import KFold, cross_val_predict
spec = importlib.util.spec_from_file_location('j', 'docs/research/experiments/f2d-dev-simlingo/j20_ssl.py')
j = importlib.util.module_from_spec(spec); spec.loader.exec_module(j)
z, v = j.frame_inputs(np.load('results/savio/f2d-h21b/pool/frames.npz')['frames'][:, 1], 64)
mean = np.stack([z[i][v[i]].mean(0) for i in range(len(z))])
paths = ['results/h21/j20/axes/j20-source'] + [f'results/h21/j20/seeds/j20-source-seed{k}' for k in (1, 2, 3)]
for path in paths:
    e = np.load(path + '.embedding.npy')
    p = cross_val_predict(RidgeCV(alphas=np.logspace(-3, 3, 13)), mean, e, cv=KFold(5, shuffle=True, random_state=0))
    print(path, 'R2 %.3f' % (1 - ((e - p) ** 2).sum() / ((e - e.mean(0)) ** 2).sum()))
axes = lambda p: [set(a['rollouts']) for a in json.load(open(p))['axes']]
jac = lambda a, b: len(a & b) / len(a | b)
j20 = axes(paths[0] + '.json')
for other in ['results/h21/h21b/axes/m15-source.json', 'results/h21/j20/axes/route-L8.json'] + [p + '.json' for p in paths[1:]]:
    print(other, [len(a) for a in axes(other)], np.round([max(jac(a, b) for b in axes(other)) for a in j20], 2).tolist())
DIAG

# j21: try 224 + 2. Row committed (a428935) before this ran.
$PY $D/j20_ssl.py $POOL/frames.npz --temperature 0.5 --name j21 --output $OUT/axes/j21-source.json
$PY $D/pool_axes.py --name j21-routeL8+ssl-t0.5 --source $OUT/axes/route-L8.json --source $OUT/axes/j21-source.json --output $OUT/axes/j21.json
$PY $D/sprint_score.py --method $OUT/axes/j21.json $RIVALS $MAN $GAPS --tried 226 --label "EXPLORATORY DEV: SimLingo H21b pool only, seeds 24-26; j21, try 224 + 2 laptop tries this batch; pair seed suffix stripped" --output $OUT/report-j21.json
