#!/usr/bin/env bash
# Audit dry run: units_rule.py, the class heredoc and view_score.py called as uniad_read.sh calls them (bash word
# splitting, nowall filter, --primary-rival B3_behaviour), on the H21b three-seed SimLingo pool. DEV ONLY.
set -euo pipefail
A=results/h21/audit-20261119-185008-11421; E=docs/research/experiments/f2d-unpooled; X=results/h21/h21b/axes
PY=/opt/miniconda3/bin/python; export PYTHONPATH=src
nowall() { tr ' ' '\n' | grep -v ':F2D_Wall$' | tr '\n' ' '; }
RULE=$(tail -1 $A/units-h21b.txt | grep : || true); NAMED=$(tail -1 $A/classes-h21b.txt | grep : || true)
ROWS="--row B3_behaviour simlingo=$X/b3_behaviour.json --row B3_infraction simlingo=$X/b3_infraction.json
 --row m23 simlingo=$X/m23.json --row m40 simlingo=$X/m40.json --row j09 simlingo=$X/j09.json"
U="--model simlingo results/h21/h21b/routes.jsonl"
L="H21b seeds 24-26, DEV ONLY (audit dry run, not evidence)"
run() {  # name manifest units
  local name=$1 man=$2 units=$3
  { time $PY $E/view_score.py --manifest $man $U --gaps $units $ROWS --primary-rival B3_behaviour \
      --label "$L; $name" --output $A/$name.json ; } > $A/$name.log 2>&1 &
}
run rule-nowall $A/manifest-pairfix.json "$(echo $RULE | nowall)"
run rule $A/manifest-pairfix.json "$RULE"
run named $A/manifest-pairfix.json "$NAMED"
run rule-nowall-unstripped results/h21/h21b/manifest.json "$(echo $RULE | nowall)"
wait
# pooled path: the same dev pool under two model names, as uniad_read.sh's pooled call passes three models
$PY $E/view_score.py --manifest $A/manifest-pairfix.json --model simlingo results/h21/h21b/routes.jsonl \
  --model uniad results/h21/h21b/routes.jsonl --gaps $(echo $RULE | nowall) $(echo $RULE | nowall | sed 's/simlingo:/uniad:/g') \
  --row B3_behaviour simlingo=$X/b3_behaviour.json uniad=$X/b3_behaviour.json --row m23 simlingo=$X/m23.json uniad=$X/m23.json \
  --primary-rival B3_behaviour --label "$L; pooled-path smoke" --output $A/pooled-smoke.json > $A/pooled-smoke.log 2>&1
