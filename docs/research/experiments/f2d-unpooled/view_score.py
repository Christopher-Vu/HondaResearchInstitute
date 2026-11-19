#!/usr/bin/env python3
"""Score views by rank-averaged best match and top-10 best match, with paired pair-bootstrap contrasts and
selection-adjusted "best of a grid" contrasts (protocol.md in this folder).

    PYTHONPATH=src python docs/research/experiments/f2d-unpooled/view_score.py --manifest MANIFEST \
        --model simlingo ROUTES [--restrict simlingo=IDS.txt] --gaps simlingo:F2D_FullyBlocked ... \
        --row vit-max simlingo=a.json --row B3_behaviour simlingo=b3.json ... --primary-rival B3_behaviour \
        --select unpooled vit-max:vit-mean vit-topk:vit-mean ... --select-vs B3_behaviour \
        --label "SimLingo test (outcomes already read)" --output report.json

Method files and rank order are sprint_score.py's (first 10 distinct axes). Rank-averaged best match for a gap is the
mean over k = 1..10 of the best Jaccard among the top k axes (a method with fewer axes keeps its last best). Each
unit (model, gap) weighs equally. The bootstrap resamples Fail2Drive pairs, every model's routes in a pair together.
--restrict keeps only the listed routes of a model (coverage-limited rows); gaps and the failing pool shrink with it.
--select NAME ROW[:OWN] ...: in every draw the member with the highest rank-averaged score is taken, and the
contrasts are that member minus its OWN comparator (if given) and minus each --select-vs row, on the same draw.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

import numpy as np

from harness.bootstrap import weighted_jaccard
from harness.scoring import jaccard
from harness.scoring_run import load_pool

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("sprint_score", HERE.parent / "f2d-dev-simlingo/sprint_score.py")
sprint_score = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sprint_score)
M = sprint_score.M


def ranked(axes: list[set[str]], gap: set[str], weight=None) -> float:
    """Mean over k = 1..M of the best Jaccard among the first k axes."""
    best, total = 0.0, 0.0
    for k in range(M):
        if k < len(axes):
            a = axes[k]
            best = max(best, jaccard(gap, a) if weight is None else weighted_jaccard(gap, a, weight))
        total += best
    return total / M


def interval(delta: np.ndarray, point: float) -> dict:
    return {"delta": point, "interval": [float(np.percentile(delta, 2.5)), float(np.percentile(delta, 97.5))],
            "p_one_sided": float((delta <= 0).mean())}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--model", nargs=2, action="append", required=True, metavar=("NAME", "ROUTES"))
    parser.add_argument("--restrict", nargs="*", default=[], metavar="MODEL=IDS")
    parser.add_argument("--gaps", nargs="+", required=True, metavar="MODEL:TYPE")
    parser.add_argument("--row", nargs="+", action="append", required=True, metavar="NAME MODEL=SPEC")
    parser.add_argument("--primary-rival", default="B3_behaviour")
    parser.add_argument("--select", nargs="+", action="append", default=[], metavar="NAME ROW[:OWN]")
    parser.add_argument("--select-vs", nargs="*", default=[])
    parser.add_argument("--replicates", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--label", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    models = [m for m, _ in args.model]
    keep = {m: set(Path(p).read_text().split()) for m, p in (s.split("=", 1) for s in args.restrict)}
    pair_of, gaps, failing = {}, {}, {}
    for model, routes in args.model:
        manifest, outcome = load_pool([args.manifest], [Path(routes)])
        if model in keep:
            outcome = {r: v for r, v in outcome.items() if r in keep[model]}
        pair_of |= {f"{model}/{e['id']}": e["pair"] for e in manifest if str(e["id"]) in outcome}
        failing[model] = sorted(r for r, v in outcome.items() if v)
        for unit in args.gaps:
            m, c = unit.split(":", 1)
            if m == model:
                gaps[unit] = {f"{model}/{e['id']}" for e in manifest if e["role"] == "pilot_slice"
                              and c in e["practice_gaps"] and outcome.get(str(e["id"]))}
    rows = {}
    for entry in args.row:
        given = dict(s.split("=", 1) for s in entry[1:])
        rows[entry[0]] = {m: [{f"{m}/{r}" for r in a} for a in sprint_score.read_method(given[m])[1]] for m in models}
    pool = sorted(pair_of)
    inside = set(pool)  # a restricted model's axes lose routes outside its kept set (A2's distinctness is kept)
    rows = {n: {m: [a & inside for a in axes] for m, axes in entry.items()} for n, entry in rows.items()}
    pairs = sorted(set(pair_of.values()))
    index = {p: i for i, p in enumerate(pairs)}

    def score(entry, metric, weight=None) -> float:
        f = ranked if metric == "rabm" else sprint_score.best
        return float(np.mean([f(entry[u.split(":", 1)[0]], g, weight) for u, g in gaps.items()]))

    names = list(rows)
    col = {n: i for i, n in enumerate(names)}
    point = {mt: np.array([score(rows[n], mt) for n in names]) for mt in ("rabm", "best")}
    rng = np.random.default_rng(args.seed)
    draws = {mt: np.zeros((args.replicates, len(names))) for mt in ("rabm", "best")}
    for b in range(args.replicates):
        counts = np.bincount(rng.integers(0, len(pairs), len(pairs)), minlength=len(pairs)).astype(float)
        weight = {r: counts[index[pair_of[r]]] for r in pool}
        for mt in draws:
            draws[mt][b] = [score(rows[n], mt, weight) for n in names]

    out_rows = {}
    for n in names:
        out_rows[n] = {"rabm": float(point["rabm"][col[n]]), "best_top10": float(point["best"][col[n]]),
                       "per_unit_rabm": {u: ranked(rows[n][u.split(":", 1)[0]], g) for u, g in gaps.items()},
                       "per_unit_best": {u: sprint_score.best(rows[n][u.split(":", 1)[0]], g) for u, g in gaps.items()}}
        if args.primary_rival in rows and n != args.primary_rival:
            r = col[args.primary_rival]
            out_rows[n]["vs_primary"] = {mt: interval(draws[mt][:, col[n]] - draws[mt][:, r],
                                                      float(point[mt][col[n]] - point[mt][r])) for mt in draws}
    selections = {}
    for entry in args.select:
        members = [(m.split(":")[0], m.split(":")[1] if ":" in m else None) for m in entry[1:]]
        idx = np.array([col[m] for m, _ in members])
        own = [col[o] if o else None for _, o in members]
        pick = draws["rabm"][:, idx].argmax(1)
        chosen = draws["rabm"][np.arange(args.replicates), idx[pick]]
        best_at_point = int(point["rabm"][idx].argmax())
        result = {"members": [m for m, _ in members], "point_choice": members[best_at_point][0],
                  "draw_choice_share": {members[i][0]: float((pick == i).mean()) for i in range(len(members))}}
        if any(o is not None for o in own):
            own_draw = np.array([draws["rabm"][b, own[pick[b]]] for b in range(args.replicates)])
            result["vs_own"] = interval(chosen - own_draw,
                                        float(point["rabm"][idx[best_at_point]] - point["rabm"][own[best_at_point]]))
        for v in args.select_vs:
            result[f"vs_{v}"] = interval(chosen - draws["rabm"][:, col[v]],
                                         float(point["rabm"][idx[best_at_point]] - point["rabm"][col[v]]))
        selections[entry[0]] = result
    report = {"label": args.label, "models": models, "routes": len(pool), "pairs": len(pairs),
              "units": {u: len(g) for u, g in gaps.items()}, "failing": {m: len(f) for m, f in failing.items()},
              "rows": out_rows, "selections": selections}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps({"units": report["units"], "routes": len(pool), "pairs": len(pairs)}))
    for n in names:
        print(json.dumps({n: [round(out_rows[n]["rabm"], 3), round(out_rows[n]["best_top10"], 3)]}))
    print(json.dumps(selections, indent=1))


if __name__ == "__main__":
    main()
