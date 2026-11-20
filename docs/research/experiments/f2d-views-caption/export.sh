#!/usr/bin/env bash
# The views prereg's caption row (docs/prereg-views.md, "The caption row"): frame export and the route-marker sample.
# CPU only. MODEL is simlingo; SHARDS its test shards. Frames go outside the repo; salt and mapping stay in results/.
#   CMD='MODEL=simlingo POOL=c SHARDS=results/savio/f2d-test-simlingo/shards MANIFEST=configs/rollout/f2d-test-simlingo.manifest.json bash docs/research/experiments/f2d-views-caption/export.sh' \
#     POLICY_VENV_LOCAL_TAR=... bash scripts/submit.sh cpu_node --time=0-02:00:00 docs/research/experiments/f2d-dev-simlingo/cpu.sbatch
set -euo pipefail
: "${MODEL:?}" "${POOL:?}" "${SHARDS:?}" "${MANIFEST:?}"
R=results/savio/f2d-views
F=/global/scratch/users/christophervu/caption-frames
mkdir -p $R $F
SALT=$R/caption-salt-$MODEL.txt
[ -s $SALT ] || python -c "import secrets; print(secrets.token_hex(16))" > $SALT
rm -rf $F/$POOL
python docs/research/experiments/h25-caption-cluster/export_frames.py $SHARDS --salt-file $SALT --frames-out $F/$POOL \
  --mapping $R/caption-mapping-$MODEL.json
# Route markers: frame 200 of 2 routes per Fail2Drive type, the first 2 by salted hash; reads no outcome.
python docs/research/experiments/f2d-views-caption/markers.py "$SHARDS" "$SALT" "$MANIFEST" "$R/markers-$MODEL.png"
du -sh $F/$POOL; ls $F/$POOL | wc -l
