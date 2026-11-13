#!/usr/bin/env bash
# Resource flags come from configs/cluster/savio.yaml via scripts/submit.sh.
#SBATCH --job-name=h24-h25-export
#SBATCH --output=h24-h25-export-%j.out
#   bash scripts/submit.sh cpu --time=0-02:00:00 docs/research/experiments/h24-error-aware-grouping/export.sbatch
# Exports H24's features and H25's frames for both pools. Reads shards and run folders only, never a key.
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
git merge-base --is-ancestor h24-h25-locked HEAD || { echo "HEAD does not contain h24-h25-locked" >&2; exit 2; }
PY=.runtime/policy-venv/bin/python
export PYTHONPATH=src
OUT=results/savio/h24-h25
FRAMES=results/savio/h25-frames  # holds only per-id frame folders; mapping and salt stay in $OUT
mkdir -p "$OUT" "$FRAMES"
F2D=(results/savio/f2d-all/shards)
H1=(); for n in step4-dev-pool step4-dev-pool-wave2 step5-pilot-p4-main step5-pilot-p7-main step5-pilot-p8-main; do H1+=("results/savio/$n/shards"); done
[ -f "$OUT/salt" ] || $PY -c "import secrets; print(secrets.token_hex(16))" > "$OUT/salt"
$PY docs/research/experiments/h24-error-aware-grouping/export_features.py "${F2D[@]}" --output "$OUT/f2d-features.npz"
$PY docs/research/experiments/h24-error-aware-grouping/export_features.py "${H1[@]}" --output "$OUT/h1-features.npz"
$PY docs/research/experiments/h25-caption-cluster/export_frames.py "${F2D[@]}" --salt-file "$OUT/salt" --frames-out "$FRAMES/a" --mapping "$OUT/f2d-mapping.json"
$PY docs/research/experiments/h25-caption-cluster/export_frames.py "${H1[@]}" --salt-file "$OUT/salt" --frames-out "$FRAMES/b" --mapping "$OUT/h1-mapping.json"
cp results/savio/h22/plain/directives/B3_behavioral@none@non_residualized.json "$OUT/f2d-b3.json"
cp results/savio/h20/plain/directives/B3_behavioral@none@non_residualized.json "$OUT/h1-b3.json"
cat results/savio/{step4-dev-pool,step4-dev-pool-wave2,step5-pilot-p4-main,step5-pilot-p7-main,step5-pilot-p8-main}/routes.jsonl > "$OUT/h1-routes.jsonl"
echo "export done after $SECONDS s"
