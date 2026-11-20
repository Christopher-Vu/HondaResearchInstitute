#!/usr/bin/env bash
# The caption row on SimLingo alone (outcomes already read), beside the table's rows on the same routes. Every
# failing SimLingo route has frames, so no route is dropped. CPU only:
#   CMD='bash docs/research/experiments/f2d-views-caption/score_simlingo.sh' bash scripts/submit.sh cpu_node \
#     --time=0-03:00:00 docs/research/experiments/f2d-dev-simlingo/cpu.sbatch
# Needs results/savio/f2d-views/caption-c/groups.json (agents.py groups) and the SimLingo caption mapping.
set -euo pipefail
E=docs/research/experiments/f2d-unpooled
MANIFEST=configs/rollout/f2d-test-simlingo.manifest.json
SR=results/savio/f2d-test-simlingo/routes.jsonl
S=results/savio/f2d-dev/simlingo
R=results/savio/f2d-dev/round2
V=results/savio/f2d-views
O=$V/caption-c
python docs/research/experiments/h25-caption-cluster/to_axes.py $O/groups.json $V/caption-mapping-simlingo.json \
  --pool c --output $O/axes.json
python $E/units_rule.py $MANIFEST $SR --model simlingo | tee $O/units.txt
NAMED="simlingo:F2D_PedestriansOnRoad simlingo:F2D_FullyBlocked simlingo:F2D_BadParking"
RULE=$(tail -1 $O/units.txt)
ALL=$(echo $NAMED $RULE | tr ' ' '\n' | sort -u | tr '\n' ' ')
NOWALL=$(echo $ALL | tr ' ' '\n' | grep -v F2D_Wall | tr '\n' ' ')
ROWS="--row caption simlingo=runs:$O/axes.json --row B3_behaviour simlingo=$S/sprint/a3/b3_behaviour.json
 --row B3_infraction simlingo=$S/sprint/b3_infraction.json
 --row B7_pool simlingo=$S/v1/plain/directives-ms20:B7_pool:L10_k64_s0
 --row m23 simlingo=$S/sprint/batch4/m23.json --row m40 simlingo=$S/sprint/batch4/pools/m40.json"
D=$S/v1/plain/directives-ms20
ls $D/B2_taxonomy@* >/dev/null 2>&1 && ROWS="$ROWS --row B2_oracle simlingo=$D:B2_taxonomy"
for U in named rule nowall; do
  UNITS=$([ $U = named ] && echo $NAMED || ([ $U = rule ] && echo $ALL || echo $NOWALL))
  python $E/view_score.py --manifest $MANIFEST --model simlingo $SR --gaps $UNITS $ROWS --primary-rival B3_behaviour \
    --label "SimLingo alone, caption row, $U units (outcomes already read)" --output $O/score-$U.json > $O/score-$U.log 2>&1 &
done
wait
tail -n +1 $O/score-*.log
