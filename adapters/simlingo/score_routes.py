"""Score a Savio route array: Bench2Drive's own merge for DS and SR, plus validity and stall columns.

    .runtime/policy-venv/bin/python adapters/simlingo/score_routes.py \\
        configs/rollout/step2-bench2drive220.yaml results/savio/<array job> [<retry job> ...]

Each configured route takes its first attempt, in job order, with a driving outcome (`VALID_OUTCOMES`),
so a driving result is never re-rolled. Routes with no such attempt, because the agent or simulator
crashed or the job ended first, are listed under `rerun` and never scored.

Two numbers come out. `official` is `Bench2Drive/tools/merge_route_json.py` run over the chosen
results, which is how published scores are made and so the one compared with PRD 10.1; it counts
routes whose scenario was skipped. `clean` leaves those out, as the Mac sweep does
(`docs/WHAT_BROKE.md`). Per-ability scores need `ability_benchmark.py`, which starts its own CARLA.
"""
from __future__ import annotations

import argparse
import contextlib
import importlib.util
import io
import json
import shutil
from pathlib import Path
from typing import Any

import yaml
from route_run import SOURCE, VALID_OUTCOMES, route_from_xml
from sweep_local import route_outcome, summarize

MERGE_SCRIPT = SOURCE / "Bench2Drive/tools/merge_route_json.py"


def attempts_by_route(job_dirs: list[Path]) -> dict[str, list[Path]]:
    found: dict[str, list[Path]] = {}
    for job in sorted(job_dirs, key=lambda path: int(path.name)):
        for route_dir in sorted(job.glob("route-*")):
            found.setdefault(route_dir.name.removeprefix("route-"), []).append(route_dir)
    return found


def status_of(route_dir: Path) -> str | None:
    result = route_dir / "result.json"
    if not result.is_file():
        return None
    records = json.loads(result.read_text()).get("_checkpoint", {}).get("records", [])
    return records[0]["status"] if records else None


def chosen_attempt(attempts: list[Path]) -> Path | None:
    return next((attempt for attempt in attempts if status_of(attempt) in VALID_OUTCOMES), None)


def gpu_columns(route_dir: Path) -> dict[str, Any]:
    readiness = route_dir / "readiness.json"
    if not readiness.is_file():
        return {}
    report = json.loads(readiness.read_text())
    gpus = report.get("gpus") or [{}]
    return {"peak_vram_gb": report.get("whole_stack_peak_vram"),
            "mean_gpu_utilization_percent": gpus[0].get("mean_utilization_percent")}


def official_merge(chosen: dict[str, Path], folder: Path) -> dict[str, Any]:
    if folder.exists():
        shutil.rmtree(folder)
    folder.mkdir(parents=True)
    for route_id, route_dir in chosen.items():
        shutil.copy(route_dir / "result.json", folder / f"{route_id}.json")
    spec = importlib.util.spec_from_file_location("merge_route_json", MERGE_SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    printed = io.StringIO()
    with contextlib.redirect_stdout(printed):
        module.merge_route_json(str(folder))
    merged = json.loads((folder / "merged.json").read_text())
    return {key: merged[key] for key in ("driving score", "success rate", "eval num")} | {
        "warning": next((line for line in printed.getvalue().splitlines() if "Warning" in line), None)}


def score(config_path: Path, job_dirs: list[Path], output: Path) -> dict[str, Any]:
    config = yaml.safe_load(config_path.read_text())
    attempts = attempts_by_route(job_dirs)
    rows, rerun, chosen = [], [], {}
    for route_id in config["routes"]:
        tried = attempts.get(route_id, [])
        attempt = chosen_attempt(tried)
        if attempt is None:
            rerun.append({"id": route_id, "attempts": len(tried),
                          "last_status": status_of(tried[-1]) if tried else None})
            continue
        chosen[route_id] = attempt
        rows.append({**route_from_xml(route_id), "job": attempt.parent.name, "attempts": len(tried),
                     **route_outcome(attempt), **gpu_columns(attempt)})
    output.mkdir(parents=True, exist_ok=True)
    (output / "routes.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows))
    report = {
        "config": str(config_path), "jobs": [path.name for path in job_dirs],
        "routes_configured": len(config["routes"]), "routes_with_outcome": len(rows),
        "official": official_merge(chosen, output / "res") if chosen else None,
        "clean": summarize(rows),
        "scenario_skipped": [row["id"] for row in rows if row["scenario_skipped"]],
        "simulated_seconds_total": round(sum(row.get("duration_game", 0) for row in rows), 1),
        "wall_seconds_total": round(sum(row.get("duration_system", 0) for row in rows), 1),
        "rerun": rerun,
    }
    (output / "summary.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("config", type=Path)
    parser.add_argument("jobs", type=Path, nargs="+", help="results/savio/<job id> directories")
    parser.add_argument("--output", type=Path, help="defaults to results/savio/<config name>")
    args = parser.parse_args()
    name = yaml.safe_load(args.config.read_text())["name"]
    report = score(args.config, args.jobs, args.output or args.jobs[0].parent / name)
    print(json.dumps({key: report[key] for key in ("routes_with_outcome", "official", "clean")}, indent=2))
    print(f"rerun: {[row['id'] for row in report['rerun']]}")


if __name__ == "__main__":
    main()
