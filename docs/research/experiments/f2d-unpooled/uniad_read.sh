#!/usr/bin/env bash
# The UniAD read of docs/prereg-views.md, one command, CPU only, run from the hri-dev clone (it holds UniAD's job dirs):
#   CMD='bash docs/research/experiments/f2d-unpooled/uniad_read.sh test interim' \
#     POLICY_VENV_LOCAL_TAR=/global/scratch/users/imhaohao/policy-venv.tar \
#     bash scripts/submit.sh cpu_node --export=ALL --time=0-06:00:00 docs/research/experiments/f2d-dev-simlingo/cpu.sbatch
# MODE dev runs every stage on UniAD's seed-24 screen (dev, never evidence); MODE test is the blind read and refuses
# to start unless tag views-prereg-v1 exists (git fetch --tags first). READ is interim or final (a label only).
# 1. merge: score_routes.py over the job dirs in job order; each route keeps its first attempt with a valid driving
#    outcome, so partial or cut-off attempts are skipped (cut-off dirs were moved to <job>-cutoff/, not listed here).
# 2. shards (export_activations.py) of the chosen attempts only, cache_pool.py --window 50, b4-split.json, and the
#    prereg §1 class of every type (gap, ceiling, decoy, background).
# 3. rows: m23, m40, B3-behaviour, B3-infraction, B7-pool as heldout.sh runs them on TF++ (transfer-spec.md), plus
#    img-mean (last BEV encoder layer) and query-mean (last track decoder layer): m03 on the 50-frame approach-window
#    mean (12.5 s at 5 steps per frame). SimLingo's and TF++'s img-mean and query-mean rows are built once if missing.
# 4. units_rule.py on this read's routes, then view_score.py: UniAD alone and pooled with SimLingo and TF++, on the
#    rule units without Wall (primary), all rule units, and the named gaps.
set -euo pipefail
MODE=${1:?dev or test}; READ=${2:-interim}
E=docs/research/experiments/f2d-unpooled
D=docs/research/experiments/f2d-dev-simlingo
REF=${REF:-/global/scratch/users/christophervu/hri-tfpp/results/savio}  # SimLingo and TF++ rows, routes and caches
V=results/savio/f2d-views
TEST_MANIFEST=configs/rollout/f2d-test-simlingo.manifest.json
export PYTHONPATH=src:adapters/simlingo
case "$MODE" in
dev)
  CONFIG=configs/rollout/f2d-screen-uniad.yaml; XML=configs/rollout/f2d-tfpp-screen.xml
  JOBS=${JOBS:-"41434958 41523040"}
  O=$V/uniad-dev; TAG="UniAD seed-24 screen, DEV ONLY (not evidence)" ;;
test)
  git rev-parse -q --verify refs/tags/views-prereg-v1 >/dev/null || { echo "views-prereg-v1 is not tagged: no UniAD test read"; exit 1; }
  CONFIG=configs/rollout/f2d-test-uniad-s101.yaml; XML=configs/rollout/f2d-test-simlingo.xml
  # first arrays s101..s106, reruns s101..s105 and s106, 3-route reruns s101..s106
  JOBS=${JOBS:-"41434964 41434967 41434969 41434973 41434975 41434977 41523041 41523042 41523043 41523044 41523045 41555288 41580713 41580714 41580715 41580716 41580717 41580718"}
  O=$V/uniad-test-$READ-$(date +%Y%m%d-%H%M); TAG="UniAD test pool, $READ read at views-prereg-v1 (blind)" ;;
*) echo "MODE is dev or test"; exit 2 ;;
esac
mkdir -p $O/rows $V/simlingo $V/tfpp
git rev-parse HEAD > $O/commit.txt

# 1. merge
DIRS=$(for j in $JOBS; do [ -d results/savio/$j ] && echo results/savio/$j; done)
python adapters/simlingo/score_routes.py $CONFIG $DIRS --output $O/merge > $O/merge.log; tail -1 $O/merge.log
R=$O/merge/routes.jsonl
python - "$CONFIG" "$O" <<'EOF'
import json, sys, yaml
from pathlib import Path
config, out = yaml.safe_load(Path(sys.argv[1]).read_text()), Path(sys.argv[2])
entries = json.loads(Path(config["route"]["manifest"]).read_text())
for e in entries:
    e.setdefault("pair", e["base_id"])  # the screen manifest has no pair field; a pair is its base route there
(out / "manifest.json").write_text(json.dumps(entries))
rows = [json.loads(l) for l in (out / "merge/routes.jsonl").read_text().splitlines()]
(out / "dirs.txt").write_text("".join(f"results/savio/{r['job']}/route-{r['id']}\n" for r in rows))
EOF
MANIFEST=$O/manifest.json

# 2. shards, cache, B4 split, classes
mkdir -p $O/shards
xargs -P 8 -n 20 python adapters/simlingo/export_activations.py --output $O/shards --manifest $MANIFEST \
  < $O/dirs.txt > $O/export.log
python $D/cache_pool.py $O/shards --window 50 --output $O/cache-w50.npz
C=$O/cache-w50.npz
python scripts/b4_split.py $O/shards $R $MANIFEST $XML --output $O/b4-split.json > $O/b4-split.log
python - "$MANIFEST" "$R" "$O" "$JOBS" <<'EOF' | tee $O/classes.txt
import json, sys
from collections import Counter
from pathlib import Path
from harness.efficacy import decoy_verdict, efficacy
manifest = json.loads(Path(sys.argv[1]).read_text())
rows = [json.loads(l) for l in Path(sys.argv[2]).read_text().splitlines()]
named = []
for gap in sorted({g for e in manifest for g in e["practice_gaps"]}):
    rep = efficacy(manifest, rows, gap)
    u, p = rep["prd_9_1"], rep["c23_paired"]
    is_gap = bool(u["passes"])
    ceiling = is_gap and u["fail_rate_in"] >= 0.95 and u["fail_rate_neighbourhood"] <= 0.20
    cls = "ceiling" if ceiling else "gap" if is_gap else "decoy" if decoy_verdict(p)["passes"] else "background"
    named += [gap] if cls == "gap" else []
    print(json.dumps({"type": gap, "class": cls, "n_in": u.get("n_in"), "fisher_p": u.get("fisher_p")}))
ids = {r["id"] for r in rows}
base = Counter(e["base_id"] for e in manifest if e["id"] in ids)
cov = {"routes": len(rows), "routes_listed": len(manifest), "twin_pairs_complete": sum(n == 2 for n in base.values()),
       "twin_pairs_listed": len({e["base_id"] for e in manifest}),
       "by_seed": dict(sorted(Counter(str(e.get("seed", "")) for e in manifest if e["id"] in ids).items())),
       "jobs": sys.argv[4].split()}
(Path(sys.argv[3]) / "coverage.json").write_text(json.dumps(cov, indent=1) + "\n")
print(json.dumps(cov))
print(" ".join(f"uniad:{g}" for g in named))
EOF

# 3. rows
read -r IMG TRK B7L <<<"$(python - "$(head -1 $O/dirs.txt)" "$C" <<'EOF'
import sys, numpy as np, torch
names = torch.load(f"{sys.argv[1]}/capture/steps.pt", map_location="cpu", weights_only=False)["layer_names"]
last = lambda stage: names.index(max((n for n in names if n.startswith(stage + ".")), key=lambda n: int(n.split(".")[1])))
depth = np.load(sys.argv[2])["driving_queries"].shape[2]
print(last("bev_encoder"), last("track_decoder"), min(depth - 1, int(np.floor(10 / 23 * (depth - 1) + 0.5))))
EOF
)"
echo "img-mean: all_tokens layer $IMG; query-mean: all_tokens layer $TRK; B7 at driving_queries layer $B7L" | tee $O/sites.txt
T=$O/rows
python $D/cache_methods.py $C --method m03 --site all_tokens --layer $IMG --name img-mean --output $T/img-mean.json
python $D/cache_methods.py $C --method m03 --site all_tokens --layer $TRK --name query-mean --output $T/query-mean.json
python $D/cache_methods.py $C --method m03 --layer-fraction 8/23 --name m23-window --output $T/m23-window.json
python $D/cache_methods.py $C --method m03 --summary route --layer-fraction 8/23 --name m23-route --output $T/m23-route.json
python $D/pool_axes.py --name m23 --output $T/m23.json --source $T/m23-window.json --source $T/m23-route.json
python $D/cache_methods.py $C --method m03 --layer-fraction 8/23 --dims 64 --name m40-window --output $T/m40-window.json
python $D/cache_methods.py $C --method m03 --summary route --layer-fraction 20/23 --name m40-route --output $T/m40-route.json
python $D/pool_axes.py --name m40 --output $T/m40.json --source $T/m40-window.json --source $T/m40-route.json
python $D/b3_behaviour.py $C --output $T/b3_behaviour.json
python $D/b3_infractions.py $C --output $T/b3_infraction.json
python $D/train_saes.py $O/shards --layer $B7L --ks 18 --seeds 0 --output $T/b7/sae
python -m discovery.emit_directives $O/shards --layer $B7L --sae $T/b7/sae/L${B7L}_k18_s0 --manifests $MANIFEST \
  --primary-dictionary L${B7L}_k18_s0 --m1-min-support 20 --output $T/b7/directives-ms20
# SimLingo and TF++ (outcomes already read): image site llm10 (SIMLINGO_IMG=vit for the ViT bridge), query site dq at
# layer 10; TF++ image site the fused backbone grid (vision_bridge), query site the last decoder join layer.
SC=$REF/f2d-dev/round2/simlingo/cache-w50.npz; TC=$REF/f2d-heldout/tfpp/cache-w50.npz
SIMG=$([ "${SIMLINGO_IMG:-llm10}" = vit ] && echo "--site vision_bridge" || echo "--site all_tokens --layer 10")
[ -f $V/simlingo/img-mean.json ] || python $D/cache_methods.py $SC --method m03 $SIMG --name img-mean --output $V/simlingo/img-mean.json
[ -f $V/simlingo/query-mean.json ] || python $D/cache_methods.py $SC --method m03 --site driving_queries --layer 10 --name query-mean --output $V/simlingo/query-mean.json
[ -f $V/tfpp/img-mean.json ] || python $D/cache_methods.py $TC --method m03 --site vision_bridge --name img-mean --output $V/tfpp/img-mean.json
[ -f $V/tfpp/query-mean.json ] || python $D/cache_methods.py $TC --method m03 --site driving_queries --layer-fraction 1 --name query-mean --output $V/tfpp/query-mean.json

# 4. units and scores
SR=$REF/f2d-test-simlingo/routes.jsonl; TR=$REF/f2d-test-tfpp/routes.jsonl
python $E/units_rule.py $MANIFEST $R --model uniad > $O/units-uniad.txt
python $E/units_rule.py $TEST_MANIFEST $SR --model simlingo > $O/units-simlingo.txt
python $E/units_rule.py $TEST_MANIFEST $TR --model tfpp > $O/units-tfpp.txt
nowall() { tr ' ' '\n' | grep -v ':F2D_Wall$' | tr '\n' ' '; }
RULE_U=$(tail -1 $O/units-uniad.txt | grep : || true); NAMED_U=$(tail -1 $O/classes.txt | grep : || true)
RULE_S=$(tail -1 $O/units-simlingo.txt); RULE_T=$(tail -1 $O/units-tfpp.txt)
NAMED_S="simlingo:F2D_PedestriansOnRoad simlingo:F2D_FullyBlocked simlingo:F2D_BadParking"
NAMED_T="tfpp:F2D_PedestriansOnRoad tfpp:F2D_FullyBlocked"
S=$REF/f2d-dev/simlingo; H=$REF/f2d-heldout/tfpp
row() { echo --row $1 simlingo=$2 tfpp=$3 uniad=$4; }
ROWS="$(row B3_behaviour $S/sprint/a3/b3_behaviour.json $H/b3_behaviour.json $T/b3_behaviour.json)
 $(row B3_infraction $S/sprint/b3_infraction.json $H/b3_infraction.json $T/b3_infraction.json)
 $(row B7_pool $S/v1/plain/directives-ms20:B7_pool:L10_k64_s0 $H/b7/directives-ms20:B7_pool:L2_k18_s0 $T/b7/directives-ms20:B7_pool:L${B7L}_k18_s0)
 $(row m23 $S/sprint/batch4/m23.json $H/m23.json $T/m23.json)
 $(row m40 $S/sprint/batch4/pools/m40.json $H/m40.json $T/m40.json)
 $(row img-mean $V/simlingo/img-mean.json $V/tfpp/img-mean.json $T/img-mean.json)
 $(row query-mean $V/simlingo/query-mean.json $V/tfpp/query-mean.json $T/query-mean.json)"
ROWS_U=$(echo $ROWS | sed -E 's/ (simlingo|tfpp)=[^ ]+//g')
# the pooled manifest: the test pool's, plus the screen's entries on a dev run (ids are disjoint)
python - $TEST_MANIFEST $MANIFEST $O/manifest-pooled.json <<'EOF'
import json, sys
a, b = (json.load(open(p)) for p in sys.argv[1:3])
ids = {e["id"] for e in a}
json.dump(a + [e for e in b if e["id"] not in ids], open(sys.argv[3], "w"))
EOF
score() {  # name label units models...
  local name=$1 label=$2 units=$3; shift 3
  case "$name:$units" in uniad-*:*uniad:*|pooled-*:?*) ;; *) echo "$name: no unit, not scored" | tee $O/$name.log; return ;; esac
  python $E/view_score.py --manifest $O/manifest-pooled.json "$@" --gaps $units --primary-rival B3_behaviour \
    --label "$label" --output $O/$name.json > $O/$name.log 2>&1 &
}
U="--model uniad $R"; P="--model simlingo $SR --model tfpp $TR $U"
score uniad-rule-nowall "$TAG; UniAD alone, rule units without Wall (primary)" "$(echo $RULE_U | nowall)" $U $ROWS_U
score uniad-rule "$TAG; UniAD alone, all rule units" "$RULE_U" $U $ROWS_U
score uniad-named "$TAG; UniAD alone, named gaps" "$NAMED_U" $U $ROWS_U
LBL="$TAG; pooled with SimLingo and TF++ (their outcomes already read)"
score pooled-rule-nowall "$LBL, rule units without Wall (primary)" "$(echo $RULE_S $RULE_T $RULE_U | nowall)" $P $ROWS
score pooled-rule "$LBL, all rule units" "$RULE_S $RULE_T $RULE_U" $P $ROWS
score pooled-named "$LBL, named gaps" "$NAMED_S $NAMED_T $NAMED_U" $P $ROWS
wait
cat $O/coverage.json $O/sites.txt
tail -n +1 $O/units-uniad.txt $O/*.log
