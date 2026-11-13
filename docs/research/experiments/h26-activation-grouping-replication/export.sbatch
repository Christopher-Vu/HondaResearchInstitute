#!/usr/bin/env bash
# Resource flags come from configs/cluster/savio.yaml via scripts/submit.sh.
#SBATCH --job-name=h26-export
#SBATCH --output=h26-export-%j.out
#   bash scripts/submit.sh cpu --time=0-01:30:00 docs/research/experiments/h26-activation-grouping-replication/export.sbatch
# H26: H24's features and a fresh B3 on H3's pool. Reads shards only, never a key.
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
git merge-base --is-ancestor h26-locked HEAD || { echo "HEAD does not contain h26-locked" >&2; exit 2; }
PY=.runtime/policy-venv/bin/python
export PYTHONPATH=src
OUT=results/savio/h26
mkdir -p "$OUT"
NAMES=(step5-background-wave3 step5-confirm-p4 step5-confirm-p7)
SHARDS=(); MANIFESTS=(); for n in "${NAMES[@]}"; do SHARDS+=("results/savio/$n/shards"); MANIFESTS+=("configs/rollout/$n.manifest.json"); done
$PY docs/research/experiments/h24-error-aware-grouping/export_features.py "${SHARDS[@]}" --output "$OUT/h3-features.npz"
rm -rf "$OUT/directives"
$PY -m discovery.emit_directives "${SHARDS[@]}" --layer 10 --manifests "${MANIFESTS[@]}" --output "$OUT/directives"
cp "$OUT/directives/B3_behavioral@none@non_residualized.json" "$OUT/h3-b3.json"
cat results/savio/{step5-background-wave3,step5-confirm-p4,step5-confirm-p7}/routes.jsonl > "$OUT/h3-routes.jsonl"
echo "export done after $SECONDS s"
