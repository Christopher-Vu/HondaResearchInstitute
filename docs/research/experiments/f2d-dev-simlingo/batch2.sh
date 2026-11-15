#!/usr/bin/env bash
# Sprint batch 2 on SimLingo (VARIANTS.md m08-m14), CPU only. One part per job, so the three run in parallel:
#   CMD='bash docs/research/experiments/f2d-dev-simlingo/batch2.sh fast|windows|m14' bash scripts/submit.sh cpu ... cpu.sbatch
set -euo pipefail
E=docs/research/experiments/f2d-dev-simlingo
S=results/savio/f2d-dev/simlingo
P=$S/sprint/m05/method_m03_site
case "$1" in
fast)  # m08 multi-layer, m09 and m10 axis pooling, m12 clustering, m13 cuts
  python "$E/pool_axes.py" --name m09 --output $S/sprint/batch2/m09.json --source ${P}_driving_queries_layer_8.json \
    --source ${P}_driving_queries_layer_20.json --source ${P}_driving_queries_layer_5.json --source ${P}_all_tokens_layer_1.json
  python "$E/pool_axes.py" --name m10 --output $S/sprint/batch2/m10.json --source ${P}_driving_queries_layer_8.json \
    --source $S/v1/plain/directives-ms20:B7_pool:L10_k64_s0
  MORE="$S/sprint/batch2/m09.json $S/sprint/batch2/m10.json" TRIED=71 BATCH=batch2 bash "$E/batch1.sh" \
    "--method m03 --layer 1 5 8 20" "--method m03 --layer 5 8 20" \
    "--method m03 --cluster average" "--method m03 --cluster complete" "--method m03 --cluster spectral" \
    "--method m03 --layer 8 --cluster average" "--method m03 --layer 8 --cluster complete" "--method m03 --layer 8 --cluster spectral" \
    "--method m03 --cuts 4 6" "--method m03 --cuts 10" ;;
windows)  # m11: approach windows of 3, 10 and 20 frames, m03 at layers 10 and 8
  for W in 3 10 20; do
    [ -f $S/cache-w$W.npz ] || python "$E/cache_pool.py" results/savio/f2d-test-simlingo/shards --window $W --output $S/cache-w$W.npz
    CACHE=$S/cache-w$W.npz TRIED=77 BATCH=batch2-w$W bash "$E/batch1.sh" "--method m03" "--method m03 --layer 8"
  done ;;
m14)  # a dictionary trained on window frames only, B7-pool and error-aware on its latents
  python "$E/b7_error_aware.py" results/savio/f2d-test-simlingo/shards --layer 10 --train-window 64 --output-dir $S/sprint/m14
  MORE="$S/sprint/m14/m14-B7pool-win-k64.json $S/sprint/m14/m14-erraware-win-k64.json" TRIED=79 BATCH=m14 bash "$E/batch1.sh" ;;
esac
