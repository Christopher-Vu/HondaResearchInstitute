#!/usr/bin/env bash
# LAPTOPWORKER 20261120-155431-29349, 2026-11-20. Exact commands, in order, from the clone root. Exploratory, dev, H21b only.
set -euo pipefail
export PYTHONPATH=src LOKY_MAX_CPU_COUNT=4
PY=/opt/miniconda3/bin/python
D=docs/research/experiments/f2d-dev-simlingo
POOL=results/savio/f2d-h21b/pool
H21B=results/h21/h21b
OUT=results/h21/j26
GAPS="--gaps F2D_CustomObstacles F2D_Wall F2D_PedestriansOnRoad --decoys F2D_Animals F2D_ConstructionPermutations F2D_ImageOnObject F2D_ObscuredStop F2D_PassableObstacles F2D_RightOfWay"
RIVALS="--rival B3_behaviour=$OUT/axes/b3_behaviour.json --reported-rival B3_infraction=$OUT/axes/b3_infraction.json --primary-rival B3_behaviour"
MAN="--manifest results/h21/j18/manifest-pair-fixed.json --routes $H21B/routes.jsonl"
mkdir -p $OUT/axes $OUT/seeds

# Position-confound check (label-free, pass/fail only, no score read). Ran before the row (commit 5814876).
$PY - <<'PY'
import importlib.util, json
import numpy as np
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.stats import spearmanr
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import RidgeCV
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import KFold, cross_val_predict
spec = importlib.util.spec_from_file_location("j26", "docs/research/experiments/f2d-dev-simlingo/j26_attr.py")
j26 = importlib.util.module_from_spec(spec); spec.loader.exec_module(j26)
POOL = "results/savio/f2d-h21b/pool"
d = j26.read_inputs(f"{POOL}/frames.npz", f"{POOL}/cache.npz", 8)
fail = d["failing"]
end = np.log(np.array([j26.window_steps(d["steps"][i], d["failure_steps"][i], n)[-1] for i, n in enumerate(d["n_frames"])]))
r2 = lambda model, x, y: float(1 - ((cross_val_predict(model, x, y, cv=KFold(5)) - y) ** 2).mean() / y.var())
def eta2(labels, y):
    return float(sum((labels == c).sum() * (y[labels == c].mean() - y.mean()) ** 2 for c in set(labels)) / ((y - y.mean()) ** 2).sum())
out = {"auroc_window_end_alone": round(float(roc_auc_score(fail, -end)), 3)}
raw = j26.window_features(d["block"], d["n_frames"])[fail]
out["eta2_end_on_raw_window_clusters_m15_input"] = {k: round(eta2(fcluster(linkage(j26.cache_methods.standardise(raw), "ward"), k, "maxclust"), end[fail]), 3) for k in (2, 3, 5)}
for keep in (True, False):
    r = j26.j26_features(d["block"], d["n_frames"], d["steps"], d["failure_steps"], fail, 0, keep)
    x, f = r["inputs"][fail], r["features"][fail]
    tree = linkage(f, "ward")
    out["keep_position" if keep else "position_removed"] = {
        "directions_removed": r["removed"], "oof_pass_fail_auroc": round(r["auroc"], 3),
        "failing_end_r2_linear": round(r2(RidgeCV(alphas=np.logspace(-2, 3, 12)), x, end[fail]), 3),
        "failing_end_r2_boosted": round(r2(HistGradientBoostingRegressor(random_state=0), x, end[fail]), 3),
        "spearman_logit_end_failing": round(float(spearmanr(r["logit"][fail], end[fail])[0]), 3),
        "spearman_logit_end_passing": round(float(spearmanr(r["logit"][~fail], end[~fail])[0]), 3),
        "eta2_end_on_attr_clusters": {k: round(eta2(fcluster(tree, k, "maxclust"), end[fail]), 3) for k in (2, 3, 5)}}
print(json.dumps(out, indent=1))
open("results/h21/j26/position-check.json", "w").write(json.dumps(out, indent=1) + "\n")
PY

# Inputs (no score read).
$PY $D/cache_methods.py $POOL/cache.npz --method m03 --summary route --layer 8 --name route-L8 --output $OUT/axes/route-L8.json
$PY $D/b3_behaviour.py $POOL/cache.npz --output $OUT/axes/b3_behaviour.json
$PY $D/b3_infractions.py $POOL/cache.npz --output $OUT/axes/b3_infraction.json
for f in route-L8 b3_behaviour b3_infraction; do
  $PY -c "import json,sys; a=lambda p:[x['rollouts'] for x in json.load(open(p))['axes']]; sys.exit(a('$OUT/axes/$f.json')!=a('$H21B/axes/$f.json'))" && echo "$f equals recorded"
done
$PY $D/j26_attr.py $POOL/frames.npz $POOL/cache.npz --output $OUT/axes/j26-source.json
$PY $D/pool_axes.py --name j26-routeL8+attr --source $OUT/axes/route-L8.json --source $OUT/axes/j26-source.json --output $OUT/axes/j26.json

# j26: try 230 + 1.
$PY $D/sprint_score.py --method $OUT/axes/j26.json $RIVALS $MAN $GAPS --tried 231 --label "EXPLORATORY DEV: SimLingo H21b pool only, seeds 24-26; j26, try 230 + 1 laptop try this batch; pair seed suffix stripped" --output $OUT/report-j26.json

# Robustness, not tries: probe seeds 1-3, 200 replicates.
for s in 1 2 3; do
  $PY $D/j26_attr.py $POOL/frames.npz $POOL/cache.npz --seed $s --output $OUT/seeds/j26-source-seed$s.json
  $PY $D/pool_axes.py --name j26-seed$s --source $OUT/axes/route-L8.json --source $OUT/seeds/j26-source-seed$s.json --output $OUT/seeds/j26-seed$s.json
  $PY $D/sprint_score.py --method $OUT/seeds/j26-seed$s.json $RIVALS $MAN $GAPS --replicates 200 --tried 231 --label "EXPLORATORY DEV: H21b; j26 probe seed $s, robustness, not a try" --output $OUT/seeds/report-j26-seed$s.json
done
