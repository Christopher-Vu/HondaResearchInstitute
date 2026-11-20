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
python - "$SHARDS" "$SALT" "$MANIFEST" "$R/markers-$MODEL.png" <<'PY'
import hashlib, json, sys
from pathlib import Path
from PIL import Image
shards, salt, out = Path(sys.argv[1]), Path(sys.argv[2]).read_text().strip(), Path(sys.argv[4])
types = {r["id"]: r["practice_gaps"] for r in json.loads(Path(sys.argv[3]).read_text())}
by_type = {}
for meta in sorted(shards.glob("*.json")):
    m = json.loads(meta.read_text())
    src = Path(m.get("source", ""))
    frame = next(iter(sorted(src.rglob("frames/200.png"))), None) if src.exists() else None
    gaps = types.get(str(m.get("route_id")), [])
    if frame is None or not gaps:
        continue
    key = hashlib.sha256((salt + str(m["route_id"])).encode()).hexdigest()
    by_type.setdefault(gaps[0], []).append((key, frame))
tiles = [(t, f) for t in sorted(by_type) for _, f in sorted(by_type[t])[:2]]
W = 480
imgs = [Image.open(f).convert("RGB") for _, f in tiles]
imgs = [i.resize((W, round(i.height * W / i.width))) for i in imgs]
H = max(i.height for i in imgs)
sheet = Image.new("RGB", (W * 4, H * ((len(imgs) + 3) // 4)))
for n, i in enumerate(imgs):
    sheet.paste(i, ((n % 4) * W, (n // 4) * H))
sheet.save(out)
print(f"marker sheet: {len(tiles)} frames from {len(by_type)} types -> {out}")
PY
du -sh $F/$POOL; ls $F/$POOL | wc -l
