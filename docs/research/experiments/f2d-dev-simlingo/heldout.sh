#!/usr/bin/env bash
# Round 1 of the held-out confirmation (prereg amendment A3, tag f2d-freeze-1), CPU only. Runs at the tag.
#   CMD='bash docs/research/experiments/f2d-dev-simlingo/heldout.sh devrival|tfpp' bash scripts/submit.sh cpu ... cpu.sbatch
# devrival: B3-behaviour rescored on SimLingo dev with the full-length speed cache (A3's rival fix; not a try).
# tfpp: the frozen finalists m23 (primary) and m40 and every rival on TransFuser++, scored once (transfer-spec.md).
set -euo pipefail
E=docs/research/experiments/f2d-dev-simlingo
MANIFEST=configs/rollout/f2d-test-simlingo.manifest.json
case "$1" in
devrival)
  S=results/savio/f2d-dev/simlingo
  O=$S/sprint/a3
  mkdir -p $O
  python "$E/cache_pool.py" results/savio/f2d-test-simlingo/shards --output $O/cache-fullspeed.npz
  python "$E/b3_behaviour.py" $O/cache-fullspeed.npz --output $O/b3_behaviour.json
  python "$E/sprint_score.py" --method $S/sprint/batch4/m23.json --method $S/sprint/batch4/pools/m40.json \
    --rival B3_behaviour=$O/b3_behaviour.json --rival B7_pool=$S/v1/plain/directives-ms20:B7_pool:L10_k64_s0 \
    --reported-rival B3_behaviour_A2=$S/sprint/a2/b3_behaviour.json --reported-rival B3_infraction=$S/sprint/b3_infraction.json \
    --manifest $MANIFEST --routes results/savio/f2d-test-simlingo/routes.jsonl \
    --gaps F2D_PedestriansOnRoad F2D_FullyBlocked F2D_BadParking \
    --decoys F2D_Animals F2D_ConstructionPermutations F2D_ImageOnObject F2D_ObscuredStop F2D_PassableObstacles F2D_RightOfWay \
    --tried 188 --output $O/report.json ;;
tfpp)
  P=results/savio/f2d-test-tfpp
  T=results/savio/f2d-heldout/tfpp
  mkdir -p $T/b7
  [ -f $T/cache-w50.npz ] || python "$E/cache_pool.py" $P/shards --window 50 --output $T/cache-w50.npz
  C=$T/cache-w50.npz
  python "$E/cache_methods.py" $C --method m03 --layer-fraction 8/23 --name m23-window --output $T/m23-window.json
  python "$E/cache_methods.py" $C --method m03 --summary route --layer-fraction 8/23 --name m23-route --output $T/m23-route.json
  python "$E/pool_axes.py" --name m23 --output $T/m23.json --source $T/m23-window.json --source $T/m23-route.json
  python "$E/cache_methods.py" $C --method m03 --layer-fraction 8/23 --dims 64 --name m40-window --output $T/m40-window.json
  python "$E/cache_methods.py" $C --method m03 --summary route --layer-fraction 20/23 --name m40-route --output $T/m40-route.json
  python "$E/pool_axes.py" --name m40 --output $T/m40.json --source $T/m40-window.json --source $T/m40-route.json
  python "$E/b3_behaviour.py" $C --output $T/b3_behaviour.json
  python "$E/b3_infractions.py" $C --output $T/b3_infraction.json
  python "$E/train_saes.py" $P/shards --layer 2 --ks 18 --seeds 0 --output $T/b7/sae
  python -m discovery.emit_directives $P/shards --layer 2 --sae $T/b7/sae/L2_k18_s0 --manifests $MANIFEST \
    --primary-dictionary L2_k18_s0 --m1-min-support 20 --output $T/b7/directives-ms20
  python "$E/sprint_score.py" --method $T/m23.json --method $T/m40.json \
    --rival B3_behaviour=$T/b3_behaviour.json --rival B7_pool=$T/b7/directives-ms20:B7_pool:L2_k18_s0 \
    --reported-rival B3_infraction=$T/b3_infraction.json \
    --manifest $MANIFEST --routes $P/routes.jsonl --gaps F2D_PedestriansOnRoad F2D_FullyBlocked \
    --decoys F2D_ConstructionPedestrian F2D_ConstructionPermutations F2D_HardBrake F2D_ImageOnObject F2D_ObscuredStop \
    F2D_PassableObstacles F2D_PedestrianCrowd F2D_PedestrianOtherBlocker F2D_RightOfWay --tried 2 --output $T/report.json ;;
esac
