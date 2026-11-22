#!/usr/bin/env bash
# The caption row's frames for TF++ (docs/prereg-views.md, "The caption row"; outcomes already read). CPU only, from
# the hri-tfpp clone, once the re-drive arrays have ended:
#   CMD='bash docs/research/experiments/f2d-views-caption/export_tfpp.sh' POLICY_VENV_LOCAL_TAR=... \
#     bash scripts/submit.sh cpu_node --export=ALL --time=0-03:00:00 docs/research/experiments/f2d-dev-simlingo/cpu.sbatch
# 1. Each re-driven route's chosen attempt (score_routes.py's rule: the first attempt with a valid outcome, in job
#    order), exported to shards. Reruns (s105b, s103b) are listed after the arrays they repeat.
# 2. match_rate.py against the first drive: the pairs whose failure reproduced.
# 3. tfpp_frames.py on those pairs' failing routes, and the route-marker sheet (capture at step 200 of 2 routes per
#    type, first 2 by salted hash). The kept routes for scoring are every first-drive passing route plus every route
#    of a reproducing pair: O/routes.txt, uniad_caption.sh's TFPP_CAPTION_DIR.
set -euo pipefail
JOBS=${JOBS:-"41537279 41537280 41537281 41537282 41537283 41537284 41575660 41696611"}
MANIFEST=configs/rollout/f2d-test-simlingo.manifest.json
FIRST=results/savio/f2d-test-tfpp
V=results/savio/f2d-views
O=$V/caption-d
F=/global/scratch/users/christophervu/caption-frames
export PYTHONPATH=src:adapters/simlingo
mkdir -p $O
git rev-parse HEAD > $O/commit.txt
python - $JOBS <<'EOF' > $O/dirs.txt
import sys
from pathlib import Path
sys.path.insert(0, "adapters/simlingo")
import score_routes as s
attempts = s.attempts_by_route([Path(f"results/savio/{j}") for j in sys.argv[1:] if Path(f"results/savio/{j}").is_dir()])
chosen = {r: s.chosen_attempt(a) for r, a in attempts.items()}
print("\n".join(str(p) for r, p in sorted(chosen.items()) if p is not None))
print(f"{sum(p is not None for p in chosen.values())} of {len(chosen)} re-driven routes have a valid attempt",
      file=sys.stderr)
EOF
rm -rf $O/shards
xargs -P 8 -n 20 python adapters/simlingo/export_activations.py --output $O/shards --manifest $MANIFEST \
  < $O/dirs.txt > $O/export.log
python docs/research/experiments/f2d-unpooled/match_rate.py $O/shards $FIRST/shards $FIRST/routes.jsonl $MANIFEST \
  --output $O/reproducing-pairs.json | tee $O/match-rate.txt
python - $O $FIRST/routes.jsonl $MANIFEST <<'EOF'
import json, sys
from pathlib import Path
from harness.scoring_run import load_pool
out = Path(sys.argv[1])
pairs = json.loads((out / "reproducing-pairs.json").read_text())
in_pairs = {str(r) for p in pairs for r in p["routes"]}
_, outcome = load_pool([Path(sys.argv[3])], [Path(sys.argv[2])])
keep = sorted({r for r, failed in outcome.items() if not failed} | in_pairs)
(out / "routes.txt").write_text("\n".join(keep) + "\n")
(out / "keep-failing.txt").write_text("\n".join(sorted(r for r in in_pairs if outcome.get(r))) + "\n")
print(json.dumps({"reproducing_pairs": len(pairs), "routes_in_pairs": len(in_pairs), "kept_routes": len(keep),
                  "failing_kept": sum(bool(outcome.get(r)) for r in in_pairs)}))
EOF
SALT=$V/caption-salt-tfpp.txt
[ -s $SALT ] || python -c "import secrets; print(secrets.token_hex(16))" > $SALT
rm -rf $F/d
python docs/research/experiments/f2d-unpooled/tfpp_frames.py $O/shards --salt-file $SALT --frames-out $F/d \
  --mapping $V/caption-mapping-tfpp.json --keep $O/keep-failing.txt | tee $O/frames.log
python - $O/shards $SALT $MANIFEST $V/markers-tfpp.png <<'EOF'
import hashlib, json, sys
from pathlib import Path
from PIL import Image
sys.path.insert(0, "docs/research/experiments/f2d-unpooled")
from tfpp_frames import image_of
shards, salt, manifest, out = Path(sys.argv[1]), Path(sys.argv[2]).read_text().strip(), sys.argv[3], Path(sys.argv[4])
types = {str(r["id"]): r["practice_gaps"] for r in json.loads(Path(manifest).read_text())}
by_type = {}
for sidecar in sorted(shards.glob("*.json")):
    meta = json.loads(sidecar.read_text())
    capture = Path(meta["source"]) / "capture/inputs/000200.pt"
    gaps = types.get(str(meta["route_id"]), [])
    if capture.exists() and gaps:
        key = hashlib.sha256((salt + str(meta["route_id"])).encode()).hexdigest()
        by_type.setdefault(gaps[0], []).append((key, capture))
tiles = [image_of(c).resize((480, 180)) for t in sorted(by_type) for _, c in sorted(by_type[t])[:2]]
sheet = Image.new("RGB", (960, 180 * ((len(tiles) + 1) // 2)))
for i, tile in enumerate(tiles):
    sheet.paste(tile, (480 * (i % 2), 180 * (i // 2)))
sheet.save(out)
print(f"marker sheet: {len(tiles)} frames from {len(by_type)} types -> {out}")
EOF
du -sh $F/d; ls $F/d | wc -l
