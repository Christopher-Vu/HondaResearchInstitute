#!/usr/bin/env bash
# Sprint batch 5 on SimLingo (VARIANTS.md m45-m49), the last search batch, and the lead robustness check. CPU only.
#   CMD='bash docs/research/experiments/f2d-dev-simlingo/batch5.sh methods|robust' bash scripts/submit.sh cpu ... cpu.sbatch
set -euo pipefail
E=docs/research/experiments/f2d-dev-simlingo
S=results/savio/f2d-dev/simlingo
A=$S/sprint/a2
O=$S/sprint/batch5
R8=$A/batch3/method_m03_summary_route_layer_8.json
mkdir -p $O
case "$1" in
methods)
  python "$E/pool_axes.py" --name m45-j06+routeL8 --output $O/m45.json --source $A/j/j06_kinresid.json --source $R8
  python "$E/pool_axes.py" --name m46-j05+routeL8 --output $O/m46.json --source $A/j/j05_knnresid.json --source $R8
  python "$E/probe_mixture.py" $S/cache-w50.npz --mode rf --layer 8 --name m47-forest-w50L8 --output $O/m47.json
  python "$E/pool_axes.py" --name m48-forest+routeL8 --output $O/m48.json --source $O/m47.json --source $R8
  python "$E/probe_mixture.py" $S/cache-w50.npz --mode gmm --layer 8 --name m49-gmm-w50L8 --output $O/m49.json
  MORE="$O/m45.json $O/m46.json $O/m47.json $O/m48.json $O/m49.json" TRIED=174 BATCH=batch5 bash "$E/batch1.sh" ;;
pools49)  # m50, m51: m49 pooled with the whole-route views (rows written after batch 5's scores)
  python "$E/pool_axes.py" --name m50-gmm+routeL8 --output $O/m50.json --source $O/m49.json --source $R8
  python "$E/pool_axes.py" --name m51-gmm+routeL20 --output $O/m51.json --source $O/m49.json     --source $S/sprint/batch4/method_m03_summary_route_layer_20.json
  MORE="$O/m50.json $O/m51.json" TRIED=188 BATCH=batch5-pools bash "$E/batch1.sh" ;;
robust)
  python "$E/robustness.py" --replicates 30 --output $S/sprint/robustness/report.json ;;
esac
