"""The evaluator's debug level draws route markers into the policy's camera, so it belongs to the hashed rollout config."""
import ast
from pathlib import Path

import pytest

from harness.config import content_hash
from route_run import AGENT, BENCHMARKS, SOURCE, Ports, evaluator_command, expert_command

PORTS = Ports(rpc=2000, traffic_manager=8000)


def config_with(**simulator):
    return {"route": {"seed": 1, "id": "7"}, "simulator": {"timeout_seconds": 600, **simulator}}


def debug_argument(command):
    return command[command.index("--debug") + 1]


def test_a_config_without_the_key_keeps_the_level_every_past_run_used():
    assert debug_argument(evaluator_command(Path("out"), config_with(), PORTS, 4)) == "2"


def test_the_config_sets_the_level_and_zero_is_not_read_as_missing():
    assert debug_argument(evaluator_command(Path("out"), config_with(debug_level=0), PORTS, 4)) == "0"


def test_the_level_is_part_of_the_hash_and_building_a_command_does_not_add_it():
    config = config_with()
    before = content_hash(config)
    evaluator_command(Path("out"), config, PORTS, 4)
    assert content_hash(config) == before
    assert content_hash(config_with(debug_level=0)) != before


def test_the_wrong_key_refuses_rather_than_running_with_markers():
    with pytest.raises(ValueError, match="debug_level"):
        evaluator_command(Path("out"), config_with(debug=0), PORTS, 4)


def test_the_expert_stays_at_zero():
    assert debug_argument(expert_command(Path("out"), config_with(debug_level=2), PORTS)) == "0"


def prints_outside_any_branch(path, method, needle):
    """True when `method` holds a print of text containing `needle` as a direct statement of its body."""
    function = next(node for node in ast.walk(ast.parse(path.read_text())) if isinstance(node, ast.FunctionDef) and node.name == method)
    return any(isinstance(statement, ast.Expr) and ast.unparse(statement.value).startswith("print(")
               and needle in ast.unparse(statement.value) for statement in function.body)


def test_the_silence_guard_hears_a_step_print_at_every_level():
    assert prints_outside_any_branch(AGENT, "run_step", "SimLingo step")


def test_the_evaluators_own_step_print_does_not_depend_on_debug():
    evaluator_agent = SOURCE / "Bench2Drive/leaderboard/leaderboard/autoagents/autonomous_agent.py"
    if not evaluator_agent.is_file():
        pytest.skip("evaluator not installed")
    assert prints_outside_any_branch(evaluator_agent, "__call__", "[Agent]")


def test_fail2drive_runs_its_own_evaluator_without_the_external_server_flag():
    command = evaluator_command(Path("out"), config_with(benchmark="fail2drive"), PORTS, 4)
    assert repr(str(BENCHMARKS["fail2drive"] / "leaderboard/leaderboard/leaderboard_evaluator.py")) in command[3]
    assert "--external-server" not in command
    assert "--external-server" in evaluator_command(Path("out"), config_with(), PORTS, 4)


def test_an_unknown_benchmark_refuses():
    with pytest.raises(ValueError, match="benchmark"):
        evaluator_command(Path("out"), config_with(benchmark="carla-leaderboard"), PORTS, 4)
