#!/usr/bin/env bash
# Re-audit dry run: view_score.py called as uniad_read.sh:183-187 and uniad_caption.sh:33-37 call it (bash word
# splitting, nowall filter, --primary-rival B3_behaviour, --select ... --select-vs B3_behaviour m23, runs: row), on the
# H21b three-seed SimLingo pool with the -sNN pair suffix stripped. DEV ONLY, never evidence.
# Stand-ins: m40 and j09 play the two new views; "caption" is six H21b method files read as six runs.
set -euo pipefail
A=results/h21/reaudit-20261122-050754-8303; E=docs/research/experiments/f2d-unpooled; X=results/h21/h21b/axes
PY=/opt/miniconda3/bin/python; export PYTHONPATH=src
R=results/h21/h21b/routes.jsonl
nowall() { tr ' ' '\n' | grep -v ':F2D_Wall$' | tr '\n' ' '; }
RULE=$(tail -1 $A/units-h21b.txt | grep : || true)
UNITS=$(echo $RULE | nowall)
row() { echo --row $1 simlingo=$2; }
ROWS="$(row B3_behaviour $X/b3_behaviour.json) $(row B3_infraction $X/b3_infraction.json) $(row m23 $X/m23.json)
 $(row m40 $X/m40.json) $(row j09 $X/j09.json) --row caption simlingo=runs:$A/runs-aligned.json"
ROWS_REV="--row caption simlingo=runs:$A/runs-aligned.json $(row j09 $X/j09.json) $(row m40 $X/m40.json)
 $(row m23 $X/m23.json) $(row B3_infraction $X/b3_infraction.json) $(row B3_behaviour $X/b3_behaviour.json)"
SEL="--select best_new m40 j09 caption --select-vs B3_behaviour m23"
L="H21b seeds 24-26, DEV ONLY (re-audit dry run, not evidence)"
run() {  # name units args...
  local name=$1 units=$2; shift 2
  { time $PY $E/view_score.py --manifest $A/manifest-pairfix.json "$@" --gaps $units --primary-rival B3_behaviour \
      $SEL --label "$L; $name" --output $A/$name.json ; } > $A/$name.log 2>&1 &
}
run rule-nowall "$UNITS" --model simlingo $R $ROWS
run rule-nowall-reversed "$UNITS" --model simlingo $R $ROWS_REV
# pooled path: the same pool under a second model name, caption runs aligned (run r = run r) or rotated by 3
TWIN=$(echo $UNITS | sed 's/simlingo:/twin:/g')
prow() { echo --row $1 simlingo=$2 twin=$3; }
PROWS="$(prow B3_behaviour $X/b3_behaviour.json $X/b3_behaviour.json) $(prow m23 $X/m23.json $X/m23.json)
 $(prow m40 $X/m40.json $X/m40.json) $(prow j09 $X/j09.json $X/j09.json)"
run pooled-aligned "$UNITS $TWIN" --model simlingo $R --model twin $R $PROWS \
  --row caption simlingo=runs:$A/runs-aligned.json twin=runs:$A/runs-aligned.json
run pooled-rotated "$UNITS $TWIN" --model simlingo $R --model twin $R $PROWS \
  --row caption simlingo=runs:$A/runs-aligned.json twin=runs:$A/runs-rotated.json
wait
