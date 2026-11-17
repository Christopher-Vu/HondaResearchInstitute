#!/usr/bin/env bash
# Sprint batch 4 on SimLingo (VARIANTS.md m22-m39 and j09 on this pool), CPU only, scored under amendment A2.
#   CMD='bash docs/research/experiments/f2d-dev-simlingo/batch4.sh fast|w100|frames' bash scripts/submit.sh cpu ... cpu.sbatch
# fast needs a2_rescore.sh m (its A2 axes for the pooled methods); frames needs a2_rescore.sh frames.
set -euo pipefail
E=docs/research/experiments/f2d-dev-simlingo
S=results/savio/f2d-dev/simlingo
A=$S/sprint/a2
O=$S/sprint/batch4
mkdir -p $O
case "$1" in
fast)
  python "$E/pool_axes.py" --name m23-w50L8+routeL8 --output $O/m23.json \
    --source $A/batch3-w50/method_m03_layer_8.json --source $A/batch3/method_m03_summary_route_layer_8.json
  python "$E/pool_axes.py" --name m28-w50L8+routeL8+B7 --output $O/m28.json \
    --source $A/batch3-w50/method_m03_layer_8.json --source $A/batch3/method_m03_summary_route_layer_8.json \
    --source $S/v1/plain/directives-ms20:B7_pool:L10_k64_s0
  python "$E/j05_knnresid.py" $S/cache-w50.npz --layer 8 --output $O/m38.json
  python - $O/m38.json <<'EOF'
import json, sys
d = json.load(open(sys.argv[1])); d["method"] = "m38-knnresid-w50L8"; json.dump(d, open(sys.argv[1], "w"), indent=1)
EOF
  MORE="$O/m23.json $O/m28.json $O/m38.json" CACHE=$S/cache-w50.npz TRIED=159 BATCH=batch4 bash "$E/batch1.sh" \
    "--method m03 --layer 8 --also-summary route" \
    "--method m03 --summary route --layer 5" "--method m03 --summary route --layer 10" \
    "--method m03 --summary route --layer 20" "--method m03 --summary route --layer 5 8 20" \
    "--method m03 --summary route --site all_tokens --layer 1" \
    "--method m03 --layer 8 --minus route" \
    "--method m03 --layer 8 --extra all_tokens:1" \
    "--method m03 --layer 8 --dims 16" "--method m03 --layer 8 --dims 64"
  CACHE=$S/cache-w20.npz TRIED=159 BATCH=batch4-w20 bash "$E/batch1.sh" "--method m03 --minus route" ;;
w100)  # m24: 100-frame windows
  [ -f $S/cache-w100.npz ] || python "$E/cache_pool.py" results/savio/f2d-test-simlingo/shards --window 100 --output $S/cache-w100.npz
  CACHE=$S/cache-w100.npz TRIED=159 BATCH=batch4-w100 bash "$E/batch1.sh" "--method m03 --layer 8" "--method m03 --layer 5 8 20" ;;
frames)  # j09 on this pool, m29-m36
  F=$S/frames.npz
  P=$O/frames
  mkdir -p $P
  python "$E/j09_hmm.py" $F --output $P/j09.json
  python "$E/j09_hmm.py" $F --layer 10 --output $P/m33.json
  python "$E/j09_hmm.py" $F --layer 20 --output $P/m34.json
  for f in m33 m34; do python - $P/$f.json $f <<'EOF'
import json, sys
d = json.load(open(sys.argv[1])); d["method"] = f"{sys.argv[2]}-{d['method']}"; json.dump(d, open(sys.argv[1], "w"), indent=1)
EOF
  done
  python "$E/frames_methods.py" $F --mode multiscale --name m29-multiscale-L8 --output $P/m29.json
  python "$E/frames_methods.py" $F --mode trend --name m30-trend-L8 --output $P/m30.json
  python "$E/frames_methods.py" $F --mode stopped --name m31-stopped-L8 --output $P/m31.json
  python "$E/frames_methods.py" $F --mode spread --name m32-spread-L8 --output $P/m32.json
  python "$E/frames_methods.py" $F --mode hmm+mean --name m35-hmm+mean-L8 --output $P/m35.json
  python "$E/frames_methods.py" $F --mode hmm-multi --layer 5 8 20 --name m36-hmm-L5+8+20 --output $P/m36.json
  MORE="$(ls $P/*.json | tr '\n' ' ')" TRIED=159 BATCH=batch4-frames bash "$E/batch1.sh" ;;
esac
