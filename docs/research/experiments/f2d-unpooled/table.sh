#!/usr/bin/env bash
# The comparison table (plan, 2026-11-18): every row already scored on SimLingo and TransFuser++, rescored by
# view_score.py (rank-averaged best match and top-10 best match, pair bootstrap), on the named units and on the units
# by rule. Both pools' outcomes were read long ago: every number here is "outcomes already read". CPU only:
#   CMD='bash docs/research/experiments/f2d-unpooled/table.sh' bash scripts/submit.sh cpu_node --time=0-04:00:00 \
#     docs/research/experiments/f2d-dev-simlingo/cpu.sbatch
set -euo pipefail
E=docs/research/experiments/f2d-unpooled
MANIFEST=configs/rollout/f2d-test-simlingo.manifest.json
SR=results/savio/f2d-test-simlingo/routes.jsonl
TR=results/savio/f2d-test-tfpp/routes.jsonl
S=results/savio/f2d-dev/simlingo
T=results/savio/f2d-heldout/tfpp
R=results/savio/f2d-dev/round2
O=results/savio/f2d-unpooled/table
mkdir -p $O
python $E/units_rule.py $MANIFEST $SR --model simlingo | tee $O/units-simlingo.txt
python $E/units_rule.py $MANIFEST $TR --model tfpp | tee $O/units-tfpp.txt
NAMED_S="simlingo:F2D_PedestriansOnRoad simlingo:F2D_FullyBlocked simlingo:F2D_BadParking"
NAMED_T="tfpp:F2D_PedestriansOnRoad tfpp:F2D_FullyBlocked"
RULE_S=$(tail -1 $O/units-simlingo.txt); RULE_T=$(tail -1 $O/units-tfpp.txt)
ALL_S=$(echo $NAMED_S $RULE_S | tr ' ' '\n' | sort -u | tr '\n' ' ')
ALL_T=$(echo $NAMED_T $RULE_T | tr ' ' '\n' | sort -u | tr '\n' ' ')

both() { echo --row "$1" simlingo=$2 tfpp=$3; }
ROWS="$(both B3_behaviour $S/sprint/a3/b3_behaviour.json $T/b3_behaviour.json)
 $(both B3_infraction $S/sprint/b3_infraction.json $T/b3_infraction.json)
 $(both B7_pool $S/v1/plain/directives-ms20:B7_pool:L10_k64_s0 $T/b7/directives-ms20:B7_pool:L2_k18_s0)
 $(both m23 $S/sprint/batch4/m23.json $T/m23.json)
 $(both m40 $S/sprint/batch4/pools/m40.json $T/m40.json)"
for r in r01 r02 r03 r04 r05 r06 r07 r08 r09 r10 r11 r12; do ROWS="$ROWS $(both $r $R/simlingo/$r.json $R/tfpp/$r.json)"; done
score() {  # label units output models...
  local label=$1 units=$2 out=$3; shift 3
  python $E/view_score.py --manifest $MANIFEST "$@" --gaps $units $ROWS --primary-rival B3_behaviour \
    --label "$label (outcomes already read)" --output $O/$out.json > $O/$out.log 2>&1 &
}
score "Pooled SimLingo+TF++, named units" "$NAMED_S $NAMED_T" pooled-named --model simlingo $SR --model tfpp $TR
score "Pooled SimLingo+TF++, units by rule" "$ALL_S $ALL_T" pooled-rule --model simlingo $SR --model tfpp $TR
# Wall fails on every slice and was set aside as a ceiling unit before the sprint; the rule admits it, so the table
# also reports the rule's units without it.
NOWALL="$(echo $ALL_S $ALL_T | tr ' ' '
' | grep -v F2D_Wall | tr '
' ' ')"
score "Pooled SimLingo+TF++, units by rule without Wall" "$NOWALL" pooled-rule-nowall --model simlingo $SR --model tfpp $TR
wait
# Per model, with the B2 oracle where its directive exists (B2 reads the scenario label: a ceiling, not a rival).
for M in simlingo tfpp; do
  D=$([ $M = simlingo ] && echo $S/v1/plain/directives-ms20 || echo $T/b7/directives-ms20)
  NAMED=$([ $M = simlingo ] && echo $NAMED_S || echo $NAMED_T); ALL=$([ $M = simlingo ] && echo $ALL_S || echo $ALL_T)
  ROUTES=$([ $M = simlingo ] && echo $SR || echo $TR)
  OTHER=$([ $M = simlingo ] && echo tfpp || echo simlingo)
  ROWS_M=$(echo $ROWS | sed -E "s/ $OTHER=[^ ]+//g")
  B2=""; ls $D/B2_taxonomy@* >/dev/null 2>&1 && B2="--row B2_oracle $M=$D:B2_taxonomy"
  for U in named rule; do
    UNITS=$([ $U = named ] && echo $NAMED || echo $ALL)
    python $E/view_score.py --manifest $MANIFEST --model $M $ROUTES --gaps $UNITS $ROWS_M $B2 --primary-rival B3_behaviour \
      --label "$M alone, $U units (outcomes already read)" --output $O/$M-$U.json > $O/$M-$U.log 2>&1 &
  done
done
wait
tail -n +1 $O/*.log
