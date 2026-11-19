#!/usr/bin/env bash
# The unpooled experiment's scoring on the SimLingo test pool (protocol.md): the 9-row grid, the reference rows, and
# the decision rule's selection contrasts. Outcomes of this pool were already read. CPU only, after the replay:
#   CMD='bash docs/research/experiments/f2d-unpooled/score_simlingo.sh' POLICY_VENV_LOCAL_TAR=... \
#     bash scripts/submit.sh cpu_node --time=0-04:00:00 docs/research/experiments/f2d-dev-simlingo/cpu.sbatch
set -euo pipefail
E=docs/research/experiments/f2d-unpooled
MANIFEST=configs/rollout/f2d-test-simlingo.manifest.json
SR=results/savio/f2d-test-simlingo/routes.jsonl
S=results/savio/f2d-dev/simlingo
REPLAY=results/savio/f2d-unpooled/simlingo-test
O=results/savio/f2d-unpooled/simlingo-score
T=results/savio/f2d-unpooled/table
mkdir -p $O
python $E/unpooled_methods.py $REPLAY $O/rows | tee $O/methods.log
NAMED="simlingo:F2D_PedestriansOnRoad simlingo:F2D_FullyBlocked simlingo:F2D_BadParking"
RULE=$(tail -1 $T/units-simlingo.txt)
ALL=$(echo $NAMED $RULE | tr ' ' '\n' | sort -u | tr '\n' ' ')
NOWALL=$(echo $ALL | tr ' ' '\n' | grep -v F2D_Wall | tr '\n' ' ')
ROWS="--row B3_behaviour simlingo=$S/sprint/a3/b3_behaviour.json --row m23 simlingo=$S/sprint/batch4/m23.json"
for f in $O/rows/*.json; do n=$(basename $f .json); [ $n = dino-mean ] || ROWS="$ROWS --row $n simlingo=$f"; done
GRID=""
for s in vit llm10 dq; do for a in max topk codebook; do GRID="$GRID $s-$a:$s-mean"; done; done
# Routes the replay refused or failed are missing from REPLAY; the rows and every rival are scored on the same routes.
ls $REPLAY/*.npz | xargs -n1 basename | sed 's/\.npz$//' > $O/routes.txt
wc -l < $O/routes.txt
score() {  # label units output
  python $E/view_score.py --manifest $MANIFEST --model simlingo $SR --restrict simlingo=$O/routes.txt --gaps $2 \
    $ROWS --primary-rival B3_behaviour --select unpooled $GRID --select image dino-max dino-topk dino-codebook \
    --select-vs B3_behaviour --label "SimLingo test, $1 (outcomes already read)" --output $O/$3.json > $O/$3.log 2>&1 &
}
score "named units" "$NAMED" named
score "units by rule" "$ALL" rule
score "units by rule without Wall" "$NOWALL" rule-nowall
wait
tail -n +1 $O/*.log
