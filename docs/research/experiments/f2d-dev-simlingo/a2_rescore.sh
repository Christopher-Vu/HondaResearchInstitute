#!/usr/bin/env bash
# Amendment A2 rescore on SimLingo's sprint pool (prereg §8, CONFLICTS C40). Rescores, not new tries. One part per job:
#   CMD='bash docs/research/experiments/f2d-dev-simlingo/a2_rescore.sh m|j|frames' bash scripts/submit.sh cpu ... cpu.sbatch
# m: every cache_methods output under sprint/ is rebuilt from its own recorded settings into sprint/a2/<same path>, the
#    pooled methods are rebuilt from those, and each directory is scored with the B7-based methods read unchanged.
# j: Jerry's j methods logged on this pool, each at its file's defaults, as in VARIANTS.md.
# frames: frames_pool.py's per-frame file for the temporal methods (Jerry's request), copied to the share.
set -euo pipefail
E=docs/research/experiments/f2d-dev-simlingo
S=results/savio/f2d-dev/simlingo
A=$S/sprint/a2
mkdir -p "$A"
[ -f $A/b3_behaviour.json ] || python "$E/b3_behaviour.py" $S/cache.npz --output $A/b3_behaviour.json
[ -f $S/sprint/b3_infraction.json ] || python "$E/b3_infractions.py" $S/cache.npz --output $S/sprint/b3_infraction.json
score() {  # score OUT TRIED METHOD_FILES...
  local out=$1 tried=$2; shift 2
  local methods=()
  for f in "$@"; do methods+=(--method "$f"); done
  python "$E/sprint_score.py" "${methods[@]}" \
    --rival B3_behaviour=$A/b3_behaviour.json --rival B7_pool="$S/v1/plain/directives-ms20:B7_pool:L10_k64_s0" \
    --reported-rival B3_infraction=$S/sprint/b3_infraction.json \
    --manifest configs/rollout/f2d-test-simlingo.manifest.json --routes results/savio/f2d-test-simlingo/routes.jsonl \
    --gaps F2D_PedestriansOnRoad F2D_FullyBlocked F2D_BadParking \
    --decoys F2D_Animals F2D_ConstructionPermutations F2D_ImageOnObject F2D_ObscuredStop F2D_PassableObstacles F2D_RightOfWay \
    --tried "$tried" --output "$out"
}
case "$1" in
m)
  for old in $(grep -l '"settings"' $(find $S/sprint -name '*.json' -not -path "$A/*")); do
    new=$A/${old#$S/sprint/}
    [ -f "$new" ] && continue
    mkdir -p "$(dirname "$new")"
    read -r -a OPTS <<< "$(python - "$old" <<'EOF'
import json, sys
s = json.load(open(sys.argv[1]))["settings"]
layer = s["layer"] if isinstance(s["layer"], list) else [s["layer"]]
opts = [s["cache"], "--method", s["method"], "--base", s["base"], "--site", s["site"], "--layer", *map(str, layer),
        "--summary", s["summary"], "--dims", str(s["dims"]), "--keep", str(s["keep"]), "--seed", str(s["seed"]),
        "--cluster", s.get("cluster", "ward"), "--cuts", *map(str, s.get("cuts", [2, 3, 5])),
        "--auto-layers", str(s.get("auto_layers", 0)), "--name", s["name"]]
print(" ".join(opts))
EOF
)"
    python "$E/cache_methods.py" "${OPTS[@]}" --output "$new"
  done
  P=$A/m05/method_m03_site
  python "$E/pool_axes.py" --name m09 --output $A/batch2/m09.json --source ${P}_driving_queries_layer_8.json \
    --source ${P}_driving_queries_layer_20.json --source ${P}_driving_queries_layer_5.json --source ${P}_all_tokens_layer_1.json
  python "$E/pool_axes.py" --name m10 --output $A/batch2/m10.json --source ${P}_driving_queries_layer_8.json \
    --source $S/v1/plain/directives-ms20:B7_pool:L10_k64_s0
  python "$E/pool_axes.py" --name m20-w20L10+B7 --output $A/batch3/m20a.json --source $A/batch2-w20/method_m03.json \
    --source $S/v1/plain/directives-ms20:B7_pool:L10_k64_s0
  python "$E/pool_axes.py" --name m20-w20L10+atL1 --output $A/batch3/m20b.json --source $A/batch2-w20/method_m03.json \
    --source ${P}_all_tokens_layer_1.json
  for d in $(find $A -mindepth 1 -type d ! -name j ! -name b7); do
    files=$(find "$d" -maxdepth 1 -name '*.json' ! -name 'report*.json' | sort)
    [ -n "$files" ] && score "$d/report.json" 134 $files
  done
  # B7-based methods are not cut-based: their files are read unchanged and only the scorer's distinct-axis rule applies
  mkdir -p $A/b7
  score $A/b7/report.json 134 $(find $S/sprint/m01 $S/sprint/m14 $S/sprint/m18 -name '*.json' ! -name 'report*.json' | sort)
  ;;
j)
  mkdir -p $A/j
  for j in j02_cpca j03_bandpool j04_bgmoment j05_knnresid j06_kinresid j07_stratify j11_knndir j12_gmmresid \
           j13_knntangent j14_earlymatch j15_hdbscan; do
    [ -f $A/j/$j.json ] || python "$E/$j.py" $S/cache.npz --output $A/j/$j.json || echo "{\"failed\": \"$j\"}"
  done
  score $A/j/report.json 134 $(ls $A/j/j*.json)
  ;;
frames)
  [ -f $S/frames.npz ] || python "$E/frames_pool.py" results/savio/f2d-test-simlingo/shards --output $S/frames.npz
  SHARE=/global/scratch/users/christophervu/share-imhaohao/f2d-sprint-simlingo
  cp $S/frames.npz $SHARE/frames.npz && setfacl -m u:imhaohao:r $SHARE/frames.npz
  ;;
esac
