#!/usr/bin/env bash
# The caption row of a UniAD read (docs/prereg-views.md, "The caption row"), after uniad_read.sh has run in O and the
# laptop has captioned O's frames with f2d-views-caption/api.py and agents.py groups (copied to O/caption/groups.json).
# CPU only, from the hri-dev clone:
#   CMD='bash docs/research/experiments/f2d-unpooled/uniad_caption.sh O [TFPP_CAPTION_DIR]' bash scripts/submit.sh \
#     cpu_node --export=ALL --time=0-04:00:00 docs/research/experiments/f2d-dev-simlingo/cpu.sbatch
# Every row is rescored beside the caption row on the routes the caption row covers: a failing route with no frame
# leaves the pool (prereg "Coverage"). UniAD alone always; pooled once TF++'s caption row exists (TFPP_CAPTION_DIR holds
# its axes.json and routes.txt, the re-driven routes whose failure reproduced). The best new view (img-mean,
# query-mean, caption) is re-selected in every draw.
set -euo pipefail
O=${1:?read folder}; TC=${2:-}
E=docs/research/experiments/f2d-unpooled
REF=${REF:-/global/scratch/users/christophervu/hri-tfpp/results/savio}
export PYTHONPATH=src:adapters/simlingo
source $O/score.env
C=$O/caption
python docs/research/experiments/h25-caption-cluster/to_axes.py $C/groups.json $O/caption-mapping.json --pool e \
  --output $C/axes.json | tee $C/to_axes.log
# UniAD's kept routes: every passing route, and every failing route that has frames
python - $O/manifest-pooled.json $R $O/caption-mapping.json $C/routes-uniad.txt <<'EOF' | tee $C/coverage.txt
import json, sys
from pathlib import Path
from harness.scoring_run import load_pool
_, outcome = load_pool([Path(sys.argv[1])], [Path(sys.argv[2])])
framed = {str(v["route"]) for v in json.loads(Path(sys.argv[3]).read_text())["mapping"].values()}
keep = sorted(r for r, failed in outcome.items() if not failed or r in framed)
Path(sys.argv[4]).write_text("\n".join(keep) + "\n")
print(json.dumps({"routes": len(outcome), "failing": sum(map(bool, outcome.values())), "failing_with_frames":
                  len(framed & {r for r, f in outcome.items() if f}), "kept": len(keep)}))
EOF
SEL="--select best_new img-mean query-mean caption --select-vs B3_behaviour m23"
score() {  # name label units args...
  local name=$1 label=$2 units=$3; shift 3
  [ -n "$(echo $units)" ] || { echo "$name: no unit, not scored" | tee $C/$name.log; return; }
  python $E/view_score.py --manifest $O/manifest-pooled.json "$@" --gaps $units --primary-rival B3_behaviour $SEL \
    --label "$label" --output $C/$name.json > $C/$name.log 2>&1 &
}
U="--model uniad $R --restrict uniad=$C/routes-uniad.txt"
RU="$ROWS_U --row caption uniad=runs:$C/axes.json"
L="$TAG; UniAD alone, caption row and every row on its routes"
score uniad-rule-nowall "$L, rule units without Wall (primary)" "$UNITS_U_NOWALL" $U $RU
score uniad-rule "$L, all rule units" "$UNITS_U_RULE" $U $RU
score uniad-named "$L, named gaps" "$UNITS_U_NAMED" $U $RU
if [ -n "$TC" ]; then
  P="--model simlingo $SR --model tfpp $TR --restrict tfpp=$TC/routes.txt $U"
  RP="$ROWS_P --row caption simlingo=runs:$REF/f2d-views/caption-c/axes.json tfpp=runs:$TC/axes.json uniad=runs:$C/axes.json"
  L="$TAG; pooled with SimLingo and TF++ (their outcomes already read), caption row and every row on its routes"
  score pooled-rule-nowall "$L, rule units without Wall (primary)" "$UNITS_P_NOWALL" $P $RP
  score pooled-rule "$L, all rule units" "$UNITS_P_RULE" $P $RP
  score pooled-named "$L, named gaps" "$UNITS_P_NAMED" $P $RP
fi
wait
cat $C/coverage.txt
tail -n +1 $C/*.log
