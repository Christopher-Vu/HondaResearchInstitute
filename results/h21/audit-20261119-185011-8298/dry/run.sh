#!/usr/bin/env bash
# Dry run of uniad_read.sh stage 4 (units_rule.py, then view_score.py) on the SimLingo H21b three-seed dev pool.
# DEV ONLY: seeds 24-26, never evidence. The model is named "uniad" so the read's own unit filters run unchanged.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
export PYTHONPATH=src
PY=/opt/miniconda3/bin/python
E=docs/research/experiments/f2d-unpooled
O=results/h21/audit-20261119-185011-8298/dry
H=results/h21/h21b
MANIFEST=$O/manifest-stripped.json; R=$H/routes.jsonl; A=$H/axes
# uniad_read.sh:134
$PY $E/units_rule.py $MANIFEST $R --model uniad > $O/units-uniad.txt
# uniad_read.sh:137-138
nowall() { tr ' ' '\n' | grep -v ':F2D_Wall$' | tr '\n' ' '; }
RULE_U=$(tail -1 $O/units-uniad.txt | grep : || true)
echo "rule units: $RULE_U" > $O/units-parsed.txt
echo "rule units without Wall: $(echo $RULE_U | nowall)" >> $O/units-parsed.txt
NAMED_U="uniad:F2D_CustomObstacles uniad:F2D_Wall uniad:F2D_PedestriansOnRoad"  # H21b's named dev gaps (SUMMARY.md)
row() { echo --row $1 uniad=$2; }
ROWS_U="$(row B3_behaviour $A/b3_behaviour.json) $(row B3_infraction $A/b3_infraction.json) $(row m23 $A/m23.json) $(row m40 $A/m40.json) $(row j09 $A/j09.json)"
U="--model uniad $R"
TAG="DEV DRY RUN: SimLingo H21b seeds 24-26 standing in for UniAD; not evidence"
# uniad_read.sh:159-168, run in the foreground
score() {
  local name=$1 label=$2 units=$3; shift 3
  case "$name:$units" in uniad-*:*uniad:*|pooled-*:?*) ;; *) echo "$name: no unit, not scored" | tee $O/$name.log; return ;; esac
  $PY $E/view_score.py --manifest $MANIFEST "$@" --gaps $units --primary-rival B3_behaviour \
    --label "$label" --output $O/$name.json > $O/$name.log 2>&1
}
score uniad-rule-nowall "$TAG; rule units without Wall (primary)" "$(echo $RULE_U | nowall)" $U $ROWS_U
score uniad-rule "$TAG; all rule units" "$RULE_U" $U $ROWS_U
score uniad-named "$TAG; named gaps" "$NAMED_U" $U $ROWS_U
# control: the unstripped manifest (pair carries the seed), to show the resampling unit changes the interval
$PY $E/view_score.py --manifest $H/manifest.json $U --gaps $(echo $RULE_U | nowall) $ROWS_U --primary-rival B3_behaviour \
  --label "$TAG; CONTROL with seed-suffixed pairs (wrong unit)" --output $O/control-unstripped.json > $O/control-unstripped.log 2>&1
# mechanics of the pooled path: the same pool entered twice under two model names (tests prefixing only)
row2() { echo --row $1 simlingo=$2 uniad=$2; }
ROWS2="$(row2 B3_behaviour $A/b3_behaviour.json) $(row2 m23 $A/m23.json)"
GAPS2="$(echo $RULE_U | nowall) $(echo $RULE_U | nowall | sed 's/uniad:/simlingo:/g')"
score pooled-mechanics "$TAG; pooled path, same pool twice (mechanics only)" "$GAPS2" --model simlingo $R $U $ROWS2
