#!/usr/bin/env bash
# Dry run of uniad_read.sh stage 4 and uniad_caption.sh scoring on the SimLingo H21b three-seed dev pool.
# DEV ONLY: seeds 24-26, never evidence. Stand-ins: img-mean=route-L20, query-mean=j09, img-mean-allseq=route-L8,
# caption=a synthetic 6-run file built from six existing rows' axes (mechanics only). The model is named "uniad"
# so the read's unit filters run unchanged.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
export PYTHONPATH=src
PY=/opt/miniconda3/bin/python
E=docs/research/experiments/f2d-unpooled
O=results/h21/reaudit-20261122-050757-21391
H=results/h21/h21b; A=$H/axes; R=$H/routes.jsonl
MANIFEST=$O/manifest-stripped.json
$PY - $H/manifest.json $MANIFEST <<'EOF'
import json, re, sys
m = json.load(open(sys.argv[1]))
for e in m:
    e["pair"] = re.sub(r"-s\d+$", "", e["pair"])
json.dump(m, open(sys.argv[2], "w"))
print("pairs", len({e["pair"] for e in m}))
EOF
# synthetic caption runs file (to_axes.py's format)
$PY - $A $O/caption-standin.json <<'EOF'
import json, sys
from pathlib import Path
A = Path(sys.argv[1])
src = ["b3_infraction", "m40", "route-L8", "m23", "route-L20", "b3_behaviour"]
runs = [{"run": r, "names": [a.get("name", str(i)) for i, a in enumerate(json.loads((A / f"{s}.json").read_text())["axes"])],
         "axes": [sorted(map(str, a["rollouts"])) for a in json.loads((A / f"{s}.json").read_text())["axes"]][:10]}
        for r, s in enumerate(src)]
Path(sys.argv[2]).write_text(json.dumps({"caption_standin": runs}))
EOF
# uniad_read.sh:153,156-157
$PY $E/units_rule.py $MANIFEST $R --model uniad > $O/units-uniad.txt
nowall() { tr ' ' '\n' | grep -v ':F2D_Wall$' | tr '\n' ' '; }
RULE_U=$(tail -1 $O/units-uniad.txt | grep : || true)
row() { echo --row $1 uniad=$2; }
ROWS_U="$(row B3_behaviour $A/b3_behaviour.json) $(row B3_infraction $A/b3_infraction.json) $(row m23 $A/m23.json)
 $(row m40 $A/m40.json) $(row img-mean $A/route-L20.json) $(row query-mean $A/j09.json)"
SEL="--select best_new img-mean query-mean --select-vs B3_behaviour m23"   # uniad_read.sh:175
U="--model uniad $R"
TAG="DEV DRY RUN: SimLingo H21b seeds 24-26 standing in for UniAD; not evidence"
# uniad_read.sh:186-187, in the foreground
$PY $E/view_score.py --manifest $MANIFEST $U --gaps $(echo $RULE_U | nowall) $ROWS_U --primary-rival B3_behaviour \
  $SEL --label "$TAG; rule units without Wall" --output $O/uniad-rule-nowall.json > $O/uniad-rule-nowall.log 2>&1
# same call with the row order reversed: every A - B key becomes B - A on the same draws
ROWS_REV="$(row query-mean $A/j09.json) $(row img-mean $A/route-L20.json) $(row m40 $A/m40.json)
 $(row m23 $A/m23.json) $(row B3_infraction $A/b3_infraction.json) $(row B3_behaviour $A/b3_behaviour.json)"
$PY $E/view_score.py --manifest $MANIFEST $U --gaps $(echo $RULE_U | nowall) $ROWS_REV --primary-rival B3_behaviour \
  $SEL --label "$TAG; reversed row order" --output $O/uniad-rule-nowall-rev.json > $O/uniad-rule-nowall-rev.log 2>&1
# uniad_caption.sh:32-44 on the same pool: caption as a runs: row, restricted to every route (no-op restrict)
cut -d'"' -f4 $R > $O/all-ids.txt
SELC="--select best_new img-mean query-mean caption --select-vs B3_behaviour m23"
$PY $E/view_score.py --manifest $MANIFEST $U --restrict uniad=$O/all-ids.txt --gaps $(echo $RULE_U | nowall) $ROWS_U \
  --row caption uniad=runs:$O/caption-standin.json --primary-rival B3_behaviour $SELC \
  --label "$TAG; caption stand-in" --output $O/caption-nowall.json > $O/caption-nowall.log 2>&1
# uniad_caption.sh:46 argument shape: --restrict tfpp=... then $U's --restrict uniad=...
# tfpp keeps only half the routes; if the first --restrict is honoured, tfpp's failing count halves
awk 'NR%2==0' $O/all-ids.txt > $O/half-ids.txt
row2() { echo --row $1 tfpp=$2 uniad=$2; }
ROWS2="$(row2 B3_behaviour $A/b3_behaviour.json) $(row2 m23 $A/m23.json)"
G2="$(echo $RULE_U | nowall) $(echo $RULE_U | nowall | sed 's/uniad:/tfpp:/g')"
P2="--model tfpp $R --restrict tfpp=$O/half-ids.txt --model uniad $R --restrict uniad=$O/all-ids.txt"
$PY $E/view_score.py --manifest $MANIFEST $P2 --gaps $G2 $ROWS2 --primary-rival B3_behaviour --replicates 50 \
  --label "$TAG; restrict shape of uniad_caption.sh:46" --output $O/restrict-shape.json > $O/restrict-shape.log 2>&1
# control: tfpp's restrict given last (alone it would be honoured)
P3="--model tfpp $R --model uniad $R --restrict tfpp=$O/half-ids.txt"
$PY $E/view_score.py --manifest $MANIFEST $P3 --gaps $G2 $ROWS2 --primary-rival B3_behaviour --replicates 50 \
  --label "$TAG; tfpp restrict alone" --output $O/restrict-control.json > $O/restrict-control.log 2>&1
