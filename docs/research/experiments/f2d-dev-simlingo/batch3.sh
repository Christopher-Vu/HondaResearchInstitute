#!/usr/bin/env bash
# Sprint batch 3 on SimLingo (VARIANTS.md m15-m21), CPU only. One part per job:
#   CMD='bash docs/research/experiments/f2d-dev-simlingo/batch3.sh fast|windows|b7' bash scripts/submit.sh cpu ... cpu.sbatch
# Every part scores against B3-infraction (m21) as well as the amendment's rivals.
set -euo pipefail
E=docs/research/experiments/f2d-dev-simlingo
S=results/savio/f2d-dev/simlingo
B2=$S/sprint/batch2
W20=$S/sprint/batch2-w20
[ -f $S/sprint/b3_infraction.json ] || python "$E/b3_infractions.py" $S/cache.npz --output $S/sprint/b3_infraction.json
export RIVALS="--rival B3_infraction=$S/sprint/b3_infraction.json"
case "$1" in
fast)
  # m20: axis pooling of the best pedestrian method with the best FullyBlocked ones
  python "$E/pool_axes.py" --name m20-w20L10+B7 --output $S/sprint/batch3/m20a.json --source $W20/method_m03.json \
    --source $S/v1/plain/directives-ms20:B7_pool:L10_k64_s0
  python "$E/pool_axes.py" --name m20-w20L10+atL1 --output $S/sprint/batch3/m20b.json --source $W20/method_m03.json \
    --source $S/sprint/m05/method_m03_site_all_tokens_layer_1.json
  # earlier leads, rescored against B3-infraction (rescores, not new tries)
  LEADS="$W20/method_m03.json $W20/method_m03_layer_8.json $B2/method_m03_layer_5_8_20.json $B2/method_m03_layer_8_cluster_average.json"
  MORE="$S/sprint/batch3/m20a.json $S/sprint/batch3/m20b.json $LEADS" CACHE=$S/cache-w20.npz TRIED=96 BATCH=batch3 \
    bash "$E/batch1.sh" \
    "--method m03 --summary route" "--method m03 --summary route --layer 8" \
    "--method m03 --layer 5 8 20" \
    "--method m03 --cluster average" "--method m03 --cluster complete" "--method m03 --cuts 10" \
    "--method m03 --layer 5 8 20 --cluster average" \
    "--method m03 --site all_tokens --layer 0" "--method m03 --site all_tokens --layer 1" \
    "--method m03 --site all_tokens --layer 2" "--method m03 --site all_tokens --layer 3" "--method m03 --site vision_bridge" \
    "--method m03 --auto-layers 3" "--method m03 --site all_tokens --auto-layers 3"
  CACHE=$S/cache-w10.npz TRIED=96 BATCH=batch3-w10 bash "$E/batch1.sh" "--method m03 --layer 5 8 20" ;;
windows)  # m15 and m16 on 30- and 50-frame windows
  for W in 30 50; do
    [ -f $S/cache-w$W.npz ] || python "$E/cache_pool.py" results/savio/f2d-test-simlingo/shards --window $W --output $S/cache-w$W.npz
    CACHE=$S/cache-w$W.npz TRIED=102 BATCH=batch3-w$W bash "$E/batch1.sh" "--method m03" "--method m03 --layer 8" "--method m03 --layer 5 8 20"
  done ;;
b7)  # m18: plain B7-pool on 20- and 50-frame windows of v1's primary dictionary
  python "$E/b7_error_aware.py" results/savio/f2d-test-simlingo/shards --layer 10 --sae $S/v1/plain/sae/L10_k64_s0 \
    --b7-windows 20 50 --output-dir $S/sprint/m18
  MORE="$S/sprint/m18/m18-B7pool-w20-L10_k64_s0.json $S/sprint/m18/m18-B7pool-w50-L10_k64_s0.json" TRIED=104 BATCH=m18 \
    bash "$E/batch1.sh" ;;
esac
