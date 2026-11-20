#!/usr/bin/env python3
"""Route-marker sample (prereg-views.md): frame 200 of the first 2 routes per Fail2Drive type by salted hash, as one sheet.

    python markers.py SHARDS SALT MANIFEST OUT.png
"""
import hashlib, json, sys
from pathlib import Path
from PIL import Image
shards, salt, out = Path(sys.argv[1]), Path(sys.argv[2]).read_text().strip(), Path(sys.argv[4])
types = {r["id"]: r["practice_gaps"] for r in json.loads(Path(sys.argv[3]).read_text())}
by_type = {}
for meta in sorted(shards.glob("*.json")):
    m = json.loads(meta.read_text())
    src = Path(m.get("source", ""))
    frame = next((p for p in sorted(src.rglob("frames/*.png")) if p.stem.isdigit() and int(p.stem) == 200), None) if src.exists() else None
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
