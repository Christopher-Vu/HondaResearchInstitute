"""UniAD is the sprint's third policy (docs/prd-discovery-sprint.md §7). Like TransFuser++, it must not inherit
SimLingo's checkpoint, module path or capture options without anyone noticing."""
import ast
import os
from pathlib import Path

import pytest

from route_run import (BENCHMARKS, SOURCE, UNIAD_AGENT, UNIAD_CONFIG, UNIAD_WEIGHTS, UNIAD_ZOO_PARENT, Ports,
                       agent_and_capture_environment, evaluator_command, policy_environment, policy_name)

PORTS = Ports(rpc=2000, traffic_manager=8000)


def config_for(benchmark="fail2drive"):
    return {"policy": {"name": "uniad"}, "route": {"seed": 1, "id": "7"},
            "simulator": {"timeout_seconds": 600, "benchmark": benchmark}}


def test_uniad_needs_fail2drive():
    assert policy_name(config_for()) == "uniad"
    with pytest.raises(ValueError, match="fail2drive"):
        policy_name(config_for("bench2drive"))


def test_uniad_agent_config_is_model_config_plus_weights():
    command = evaluator_command(Path("out"), config_for(), PORTS, 4, UNIAD_AGENT)
    config, weights = command[command.index("--agent-config") + 1].split("+")
    assert (config, weights) == (str(UNIAD_CONFIG), str(UNIAD_WEIGHTS))


def test_uniad_path_has_the_zoo_parent_and_no_other_team_code():
    environment = policy_environment(Path("out"), "cuda", Path("api"), False, {}, BENCHMARKS["fail2drive"], "uniad")
    paths = environment["PYTHONPATH"].split(os.pathsep)
    assert str(UNIAD_ZOO_PARENT) in paths
    assert str(BENCHMARKS["fail2drive"] / "team_code") not in paths
    assert str(SOURCE / "team_code") not in paths and str(SOURCE) not in paths
    assert "SAVE_PATH" not in environment
    assert environment["UNIAD_ZOO_PARENT"] == str(UNIAD_ZOO_PARENT)


def test_uniad_captures_and_refuses_token_layers():
    assert agent_and_capture_environment(10, policy="uniad") == (UNIAD_AGENT, {"SIMLINGO_CAPTURE_EVERY": "10"})
    with pytest.raises(ValueError, match="per-token"):
        agent_and_capture_environment(10, [10], policy="uniad")


def test_uniad_capture_moves_means_to_cpu_before_stacking_skipped_stages():
    """The GPU hook mean and a skipped stage's CPU zeros must be stackable together."""
    tree = ast.parse(Path("adapters/uniad/uniad_agent.py").read_text())
    capture = next(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == "_forward_done")
    layers = next(
        node for node in ast.walk(capture)
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "layers" for target in node.targets)
    )
    assert isinstance(layers.value, ast.Call)
    assert isinstance(layers.value.args[0], ast.ListComp)
    pooled_or_zeros = layers.value.args[0].elt
    assert isinstance(pooled_or_zeros, ast.IfExp)
    assert ast.unparse(pooled_or_zeros.body).endswith(".to(CPU)")
