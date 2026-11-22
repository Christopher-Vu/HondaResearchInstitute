"""Re-audit checks on the dry-run JSONs: antisymmetry of pairwise intervals across row orders, ranks_above against a
hand computation, vs_primary against the pairwise entry, and the multi-run row's point score as a median of runs."""
import json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, "src")
from harness.scoring import jaccard
from harness.scoring_run import load_pool

A = Path("results/h21/reaudit-20261122-050754-8303")
fwd, rev = (json.loads((A / f"{n}.json").read_text()) for n in ("rule-nowall", "rule-nowall-reversed"))
names = list(fwd["rows"])
worst = 0.0
for key, val in fwd["pairwise"].items():
    a, b = key.split(" - ")
    other = rev["pairwise"][f"{b} - {a}"]
    for mt in ("rabm", "best"):
        lo, hi = val[mt]["interval"]; lo2, hi2 = other[mt]["interval"]
        worst = max(worst, abs(lo + hi2), abs(hi + lo2), abs(val[mt]["delta"] + other[mt]["delta"]))
print(f"antisymmetry: {len(fwd['pairwise'])} pairs x 2 metrics, max |A-B + (B-A)| over interval ends and deltas = {worst:.2e}")

def hand_above(report):
    out = {n: [] for n in report["rows"]}
    for key, val in report["pairwise"].items():
        a, b = key.split(" - ")
        lo, hi = val["rabm"]["interval"]
        if lo > 0: out[a].append(b)
        if hi < 0: out[b].append(a)
    return {n: sorted(v) for n, v in out.items()}
for label, rep in (("forward", fwd), ("reversed", rev)):
    print(f"ranks_above {label} == hand:", rep["ranks_above"] == hand_above(rep))
print("ranks_above forward == reversed:", fwd["ranks_above"] == rev["ranks_above"])
print("ranks_above:", {n: v for n, v in fwd["ranks_above"].items() if v})

mism = 0
for n in names:
    if n == "B3_behaviour": continue
    key = f"{n} - B3_behaviour" if f"{n} - B3_behaviour" in fwd["pairwise"] else None
    if key is None:
        p = fwd["pairwise"][f"B3_behaviour - {n}"]["rabm"]; iv = [-p["interval"][1], -p["interval"][0]]
    else:
        iv = fwd["pairwise"][key]["rabm"]["interval"]
    mism += max(abs(x - y) for x, y in zip(iv, fwd["rows"][n]["vs_primary"]["rabm"]["interval"])) > 1e-12
print("vs_primary rabm interval == pairwise entry, rows mismatching:", mism)

# caption point score by hand: median over the 6 runs of the mean over units of rank-averaged best match
manifest, outcome = load_pool([A / "manifest-pairfix.json"], [Path("results/h21/h21b/routes.jsonl")])
units = [u.split(":", 1)[1] for u in fwd["units"]]
gaps = {c: {str(e["id"]) for e in manifest if e["role"] == "pilot_slice" and c in e["practice_gaps"] and outcome.get(str(e["id"]))}
        for c in units}
def rabm(axes, gap):
    best, total = 0.0, 0.0
    for k in range(10):
        if k < len(axes): best = max(best, jaccard(gap, axes[k]))
        total += best
    return total / 10
def distinct(axes):
    kept = []
    for a in axes:
        if a not in kept: kept.append(a)
    return kept[:10]
(runs,) = json.loads((A / "runs-aligned.json").read_text()).values()
per_run = [float(np.mean([rabm(distinct([set(a) for a in r["axes"]]), g) for g in gaps.values()])) for r in runs]
print("caption per-run rabm:", [round(x, 4) for x in per_run], "median", round(float(np.median(per_run)), 6),
      "report", round(fwd["rows"]["caption"]["rabm"], 6))
for n in ("pooled-aligned", "pooled-rotated"):
    rep = json.loads((A / f"{n}.json").read_text())["rows"]["caption"]
    print(n, "caption rabm", round(rep["rabm"], 4), "best_top10", round(rep["best_top10"], 4),
          "vs B3 rabm", [round(x, 4) for x in rep["vs_primary"]["rabm"]["interval"]])
sel = fwd["selections"]["best_new"]
print("best_new vs B3:", [round(x, 4) for x in sel["vs_B3_behaviour"]["interval"]],
      "| point choice", sel["point_choice"], "own vs B3:", [round(x, 4) for x in fwd["rows"][sel["point_choice"]]["vs_primary"]["rabm"]["interval"]])
