"""Re-audit inputs: the H21b manifest with -sNN stripped from pair (prereg A1), and a stand-in multi-run row in
to_axes.py's format (six H21b method files as six runs, aligned and rotated by 3). DEV ONLY."""
import json, re
from pathlib import Path
A = Path("results/h21/reaudit-20261122-050754-8303")
m = json.loads(Path("results/h21/h21b/manifest.json").read_text())
for e in m:
    e["pair"] = re.sub(r"-s\d+$", "", e["pair"])
(A / "manifest-pairfix.json").write_text(json.dumps(m))
print(len({e["pair"] for e in m}), "pairs")
srcs = ["m15-source", "m39-source", "route-L20", "route-L8", "j09", "b3_infraction"]
runs = [{"run": r, "names": [a.get("name", "") for a in d["axes"]], "axes": [sorted(map(str, a["rollouts"])) for a in d["axes"]]}
        for r, d in enumerate(json.loads(Path(f"results/h21/h21b/axes/{s}.json").read_text()) for s in srcs)]
(A / "runs-aligned.json").write_text(json.dumps({"H25_caption_cluster": runs}))
(A / "runs-rotated.json").write_text(json.dumps({"H25_caption_cluster": runs[3:] + runs[:3]}))
