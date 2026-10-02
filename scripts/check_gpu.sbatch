#!/usr/bin/env bash
# Resource flags (account/partition/qos/gres/cpus) come from
# configs/cluster/savio.yaml via scripts/submit.sh. Do not add them here.
#SBATCH --job-name=gpu-smoke
#SBATCH --time=0-00:10:00
#SBATCH --output=gpu-smoke-%j.out
#
# Step 0 Track B item 3: the done-condition for Step 0.
#   bash scripts/submit.sh gpu scripts/check_gpu.sbatch
# Blocked until configs/cluster/savio.yaml has a GPU partition.
#
# Also probes the off-screen rendering question (Step 1 stage 1.2), which is
# the most likely project-level blocker.

echo "=== node ==="; hostname; date
echo "=== gpu ==="; nvidia-smi
echo "=== cuda ==="; nvcc --version 2>&1 | tail -2 || echo "nvcc absent (fine)"
echo "=== gpu rendering libs — relevant to CARLA off-screen ==="
ls /usr/lib64/libGL.so* /usr/lib/x86_64-linux-gnu/libGL.so* 2>/dev/null || echo "no libGL found"
command -v vulkaninfo >/dev/null && vulkaninfo --summary 2>&1 | head -15 || echo "vulkaninfo absent"
command -v glxinfo   >/dev/null && glxinfo -B 2>&1 | head -10    || echo "glxinfo absent"
command -v Xvfb      >/dev/null && echo "Xvfb present (off-screen fallback available)" || echo "Xvfb absent"
echo "=== done ==="
