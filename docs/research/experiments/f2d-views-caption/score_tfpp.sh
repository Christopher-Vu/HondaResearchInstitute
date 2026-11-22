#!/usr/bin/env bash
# The caption row on TF++ alone (outcomes already read), beside every other row rescored on the same routes: every
# first-drive passing route plus every route of a pair whose failure reproduced (export_tfpp.sh's routes.txt). CPU
# only, from the hri-tfpp clone:
#   CMD='bash docs/research/experiments/f2d-views-caption/score_tfpp.sh' bash scripts/submit.sh cpu_node \
#     --time=0-03:00:00 docs/research/experiments/f2d-dev-simlingo/cpu.sbatch
# Needs results/savio/f2d-views/caption-d/groups.json (agents.py groups) and the TF++ caption mapping.
set -euo pipefail
E=docs/research/experiments/f2d-unpooled
MANIFEST=configs/rollout/f2d-test-simlingo.manifest.json
TR=results/savio/f2d-test-tfpp/routes.jsonl
H=results/savio/f2d-heldout/tfpp
V=results/savio/f2d-views
VD=/global/scratch/users/christophervu/hri-dev/results/savio/f2d-views/tfpp  # the views' TF++ rows (uniad_read.sh)
O=$V/caption-d
export PYTHONPATH=src:adapters/simlingo
git rev-parse HEAD > $O/score-commit.txt
python docs/research/experiments/h25-caption-cluster/to_axes.py $O/groups.json $V/caption-mapping-tfpp.json \
  --pool d --output $O/axes.json
python $E/units_rule.py $MANIFEST $TR --model tfpp | tee $O/units.txt
NAMED="tfpp:F2D_PedestriansOnRoad tfpp:F2D_FullyBlocked"
RULE=$(tail -1 $O/units.txt)
NOWALL=$(echo $RULE | tr ' ' '\n' | grep -v ':F2D_Wall$' | tr '\n' ' ')
ROWS="--row caption tfpp=runs:$O/axes.json --row B3_behaviour tfpp=$H/b3_behaviour.json
 --row B3_infraction tfpp=$H/b3_infraction.json --row B7_pool tfpp=$H/b7/directives-ms20:B7_pool:L2_k18_s0
 --row m23 tfpp=$H/m23.json --row m40 tfpp=$H/m40.json
 --row img-mean tfpp=$VD/img-mean.json --row query-mean tfpp=$VD/query-mean-alljoin.json"
SEL="--select best_new img-mean query-mean caption --select-vs B3_behaviour m23"
PIDS=()
for U in named rule nowall; do
  UNITS=$([ $U = named ] && echo $NAMED || ([ $U = rule ] && echo $RULE || echo $NOWALL))
  python $E/view_score.py --manifest $MANIFEST --model tfpp $TR --restrict tfpp=$O/routes.txt --gaps $UNITS $ROWS \
    --primary-rival B3_behaviour $SEL --label "TF++ alone, caption row, $U units (outcomes already read)" \
    --output $O/score-$U.json > $O/score-$U.log 2>&1 &
  PIDS+=($!)
done
for p in "${PIDS[@]}"; do wait $p; done
tail -n +1 $O/score-*.log
