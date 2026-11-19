"""Regression coverage for the TransFuser++ re-drive agreement gate.

The unpooled analysis is only allowed to use pairs whose new closed-loop drive
matches the original outcome.  Keep the small, file-level contract here so it
can run without CARLA or a GPU.
"""
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np


SCRIPT = Path(__file__).resolve().parents[1] / "docs/research/experiments/f2d-unpooled/match_rate.py"
spec = importlib.util.spec_from_file_location("tfpp_match_rate", SCRIPT)
match_rate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(match_rate)


def write_sidecar(folder, route_id, *, status, success, infractions=None, locations=None):
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{route_id}.json"
    path.write_text(json.dumps({"route_id": route_id, "status": status, "success": success,
                                "infractions": infractions or {}, "infraction_locations": locations or {}}))
    return path


def test_first_infraction_uses_the_earliest_reached_location(tmp_path):
    sidecar = write_sidecar(tmp_path, "failed", status="Failed", success=False,
                            infractions={"late": 1, "early": 1},
                            locations={"late": [[20.0, 0.0]], "early": [[0.0, 0.0]]})
    np.savez(sidecar.with_suffix(".npz"), step=np.array([0, 10, 20]),
             ego_x=np.array([0.0, 10.0, 20.0]), ego_y=np.zeros(3))

    assert match_rate.first_infraction(sidecar) == "early"


def test_only_complete_matching_failure_pairs_are_emitted(tmp_path, monkeypatch, capsys):
    first, redrive = tmp_path / "first", tmp_path / "redrive"
    # Pair one is fully reproduced.  Pair two is incomplete and must remain
    # pending instead of being treated as a match or a mismatch.
    for folder, suffix in ((first, ""), (redrive, "")):
        write_sidecar(folder, "g1", status="Failed", success=False)
        write_sidecar(folder, "t1", status="Completed", success=True)
    write_sidecar(first, "g2", status="Failed", success=False)
    write_sidecar(first, "t2", status="Completed", success=True)
    write_sidecar(redrive, "g2", status="Failed", success=False)
    # A passing-only pair is irrelevant to the re-drive denominator.
    for folder in (first, redrive):
        write_sidecar(folder, "g3", status="Completed", success=True)
        write_sidecar(folder, "t3", status="Completed", success=True)

    routes = tmp_path / "routes.jsonl"
    routes.write_text("\n".join(json.dumps({"id": route_id, "status": status, "success": success}) for route_id, status, success in (
        ("g1", "Failed", False), ("t1", "Completed", True), ("g2", "Failed", False),
        ("t2", "Completed", True), ("g3", "Completed", True), ("t3", "Completed", True))) + "\n")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps([
        {"id": "g1", "base_id": "one", "seed": 101}, {"id": "t1", "base_id": "one", "seed": 101},
        {"id": "g2", "base_id": "two", "seed": 101}, {"id": "t2", "base_id": "two", "seed": 101},
        {"id": "g3", "base_id": "three", "seed": 101}, {"id": "t3", "base_id": "three", "seed": 101},
    ]))
    output = tmp_path / "reproducing.json"
    monkeypatch.setattr(sys, "argv", ["match_rate.py", str(redrive), str(first), str(routes), str(manifest),
                                       "--output", str(output)])

    match_rate.main()

    assert json.loads(output.read_text()) == [{"base_id": "one", "seed": 101, "routes": ["g1", "t1"]}]
    assert "pairs 1/1 = 1.000 (1 pending)" in capsys.readouterr().out
