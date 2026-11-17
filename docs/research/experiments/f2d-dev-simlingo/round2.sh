#!/usr/bin/env bash
# Round 2 search batch 1 (prereg A3; VARIANTS.md r01-r07): every method runs on SimLingo and TransFuser++ with the
# same settings (layers as fractions of depth) and is scored pooled over both. CPU only.
#   CMD='bash docs/research/experiments/f2d-dev-simlingo/round2.sh' bash scripts/submit.sh cpu ... cpu.sbatch
set -euo pipefail
E=docs/research/experiments/f2d-dev-simlingo
MANIFEST=configs/rollout/f2d-test-simlingo.manifest.json
S=results/savio/f2d-dev/simlingo
T=results/savio/f2d-heldout/tfpp
O=results/savio/f2d-dev/round2
mkdir -p $O/simlingo $O/tfpp
[ -f $O/simlingo/cache-w50.npz ] || python "$E/cache_pool.py" results/savio/f2d-test-simlingo/shards --window 50 --output $O/simlingo/cache-w50.npz
cp -n $T/cache-w50.npz $O/tfpp/cache-w50.npz
for M in simlingo tfpp; do
  C=$O/$M/cache-w50.npz; D=$O/$M
  run() { python "$E/cache_methods.py" $C --output $D/$1.json --name $1 "${@:2}"; }
  run route8 --method m03 --summary route --layer-fraction 8/23
  run auto-window --method m03 --auto-layers 1
  run auto-route --method m03 --summary route --auto-layers 1
  run kin-window --method m06 --base m03 --layer-fraction 8/23
  run err-window --method m04 --layer-fraction 8/23
  run change-window --method m07 --layer-fraction 8/23
  run depth-window --method m03 --layer-fraction 0 1/3 2/3 1
  run vision-window --method m03 --layer-fraction 8/23 --extra vision_bridge:0
  run m23-window --method m03 --layer-fraction 8/23
  pool() { python "$E/pool_axes.py" --name $1 --output $D/$1.json "${@:2}"; }
  pool r01 --source $D/auto-window.json --source $D/auto-route.json
  pool r02 --source $D/kin-window.json --source $D/route8.json
  B3I=$([ $M = simlingo ] && echo $S/sprint/b3_infraction.json || echo $T/b3_infraction.json)
  pool r03 --source $D/m23-window.json --source $D/route8.json --source $B3I
  pool r04 --source $D/err-window.json --source $D/route8.json
  pool r05 --source $D/change-window.json --source $D/route8.json
  pool r06 --source $D/depth-window.json --source $D/route8.json
  pool r07 --source $D/vision-window.json --source $D/route8.json
done
both() { echo "$1" simlingo=$O/simlingo/$1.json tfpp=$O/tfpp/$1.json; }
METHODS=""; for r in r01 r02 r03 r04 r05 r06 r07; do METHODS="$METHODS --method $(both $r)"; done
python "$E/pooled_score.py" --manifest $MANIFEST \
  --model simlingo results/savio/f2d-test-simlingo/routes.jsonl --model tfpp results/savio/f2d-test-tfpp/routes.jsonl \
  --gaps simlingo:F2D_PedestriansOnRoad simlingo:F2D_FullyBlocked simlingo:F2D_BadParking tfpp:F2D_PedestriansOnRoad tfpp:F2D_FullyBlocked \
  --decoys simlingo:F2D_Animals simlingo:F2D_ConstructionPermutations simlingo:F2D_ImageOnObject simlingo:F2D_ObscuredStop \
    simlingo:F2D_PassableObstacles simlingo:F2D_RightOfWay tfpp:F2D_ConstructionPedestrian tfpp:F2D_ConstructionPermutations \
    tfpp:F2D_HardBrake tfpp:F2D_ImageOnObject tfpp:F2D_ObscuredStop tfpp:F2D_PassableObstacles tfpp:F2D_PedestrianCrowd \
    tfpp:F2D_PedestrianOtherBlocker tfpp:F2D_RightOfWay \
  $METHODS --method m23 simlingo=$S/sprint/batch4/m23.json tfpp=$T/m23.json \
  --method m40 simlingo=$S/sprint/batch4/pools/m40.json tfpp=$T/m40.json \
  --rival B3_behaviour simlingo=$S/sprint/a3/b3_behaviour.json tfpp=$T/b3_behaviour.json \
  --rival B7_pool simlingo=$S/v1/plain/directives-ms20:B7_pool:L10_k64_s0 tfpp=$T/b7/directives-ms20:B7_pool:L2_k18_s0 \
  --reported-rival B3_infraction simlingo=$S/sprint/b3_infraction.json tfpp=$T/b3_infraction.json \
  --tried 197 --label "DEV round 2: SimLingo + TransFuser++ pooled; p values exploratory" --output $O/batch1.json
