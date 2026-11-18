#!/usr/bin/env bash
# Round 2 search batch 2 (VARIANTS.md r08-r12), aimed at TransFuser++. Same layout and scoring as round2.sh. CPU only.
set -euo pipefail
E=docs/research/experiments/f2d-dev-simlingo
MANIFEST=configs/rollout/f2d-test-simlingo.manifest.json
S=results/savio/f2d-dev/simlingo
T=results/savio/f2d-heldout/tfpp
O=results/savio/f2d-dev/round2
[ -f $O/simlingo/cache-w20.npz ] || python "$E/cache_pool.py" results/savio/f2d-test-simlingo/shards --window 20 --output $O/simlingo/cache-w20.npz
[ -f $O/tfpp/cache-w20.npz ] || python "$E/cache_pool.py" results/savio/f2d-test-tfpp/shards --window 20 --output $O/tfpp/cache-w20.npz
for M in simlingo tfpp; do
  D=$O/$M; C=$D/cache-w50.npz
  DIMS=$([ $M = simlingo ] && echo 32 || echo 9)  # r12: PCA width scaled with model width, as B7's k (32 x 256 / 896)
  run() { python "$E/cache_methods.py" $1 --output $D/$2.json --name $2 "${@:3}"; }
  run $C tok-window --method m03 --site all_tokens --layer-fraction 8/23
  run $C tok-route --method m03 --site all_tokens --summary route --layer-fraction 8/23
  run $C vb-window --method m03 --site vision_bridge
  run $D/cache-w20.npz w20-window --method m03 --layer-fraction 8/23
  run $C scaled-window --method m03 --layer-fraction 8/23 --dims $DIMS
  run $C scaled-route --method m03 --summary route --layer-fraction 8/23 --dims $DIMS
  pool() { python "$E/pool_axes.py" --name $1 --output $D/$1.json "${@:2}"; }
  pool r08 --source $D/tok-window.json --source $D/tok-route.json
  pool r09 --source $D/vb-window.json --source $D/route8.json
  pool r10 --source $D/w20-window.json --source $D/route8.json
  pool r11 --source $D/route8.json --source $D/m23-window.json
  pool r12 --source $D/scaled-window.json --source $D/scaled-route.json
done
both() { echo "$1" simlingo=$O/simlingo/$1.json tfpp=$O/tfpp/$1.json; }
METHODS=""; for r in r08 r09 r10 r11 r12 r07; do METHODS="$METHODS --method $(both $r)"; done
python "$E/pooled_score.py" --manifest $MANIFEST \
  --model simlingo results/savio/f2d-test-simlingo/routes.jsonl --model tfpp results/savio/f2d-test-tfpp/routes.jsonl \
  --gaps simlingo:F2D_PedestriansOnRoad simlingo:F2D_FullyBlocked simlingo:F2D_BadParking tfpp:F2D_PedestriansOnRoad tfpp:F2D_FullyBlocked \
  --decoys simlingo:F2D_Animals simlingo:F2D_ConstructionPermutations simlingo:F2D_ImageOnObject simlingo:F2D_ObscuredStop \
    simlingo:F2D_PassableObstacles simlingo:F2D_RightOfWay tfpp:F2D_ConstructionPedestrian tfpp:F2D_ConstructionPermutations \
    tfpp:F2D_HardBrake tfpp:F2D_ImageOnObject tfpp:F2D_ObscuredStop tfpp:F2D_PassableObstacles tfpp:F2D_PedestrianCrowd \
    tfpp:F2D_PedestrianOtherBlocker tfpp:F2D_RightOfWay \
  $METHODS --method m23 simlingo=$S/sprint/batch4/m23.json tfpp=$T/m23.json \
  --rival B3_behaviour simlingo=$S/sprint/a3/b3_behaviour.json tfpp=$T/b3_behaviour.json \
  --rival B7_pool simlingo=$S/v1/plain/directives-ms20:B7_pool:L10_k64_s0 tfpp=$T/b7/directives-ms20:B7_pool:L2_k18_s0 \
  --reported-rival B3_infraction simlingo=$S/sprint/b3_infraction.json tfpp=$T/b3_infraction.json \
  --tried 202 --label "DEV round 2 batch 2: SimLingo + TransFuser++ pooled; p values exploratory" --output $O/batch2.json
