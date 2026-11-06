"""TransFuser++ is the Fail2Drive track's second policy (docs/prd-fail2drive.md, F6). It must not inherit SimLingo's
checkpoint, module path or capture options without anyone noticing."""
import os
from pathlib import Path

import pytest

from route_run import (BENCHMARKS, CHECKPOINT, SOURCE, TFPP_AGENT, TFPP_CHECKPOINT, Ports,
                       agent_and_capture_environment, evaluator_command, policy_environment, policy_name)

PORTS = Ports(rpc=2000, traffic_manager=8000)


def config_for(policy, benchmark="fail2drive"):
    return {"policy": {"name": policy}, "route": {"seed": 1, "id": "7"},
            "simulator": {"timeout_seconds": 600, "benchmark": benchmark}}


def agent_config(command):
    return command[command.index("--agent-config") + 1]


def test_policy_defaults_to_simlingo_and_refuses_unknown_names():
    assert policy_name({"simulator": {}}) == "simlingo"
    with pytest.raises(ValueError, match="Unknown policy"):
        policy_name(config_for("uniad"))


def test_tfpp_needs_fail2drive():
    with pytest.raises(ValueError, match="fail2drive"):
        policy_name(config_for("tfpp", benchmark="bench2drive"))


def test_each_policy_gets_its_own_checkpoint():
    tfpp = evaluator_command(Path("out"), config_for("tfpp"), PORTS, 4, TFPP_AGENT)
    assert agent_config(tfpp) == str(TFPP_CHECKPOINT)
    assert tfpp[tfpp.index("--agent") + 1] == str(TFPP_AGENT)
    assert agent_config(evaluator_command(Path("out"), config_for("simlingo"), PORTS, 4)) == str(CHECKPOINT) + "+agent"


def test_tfpp_path_has_fail2drive_team_code_and_not_simlingos():
    environment = policy_environment(Path("out"), "cuda", Path("api"), False, {}, BENCHMARKS["fail2drive"], "tfpp")
    paths = environment["PYTHONPATH"].split(os.pathsep)
    assert str(BENCHMARKS["fail2drive"] / "team_code") in paths
    assert str(SOURCE / "team_code") not in paths and str(SOURCE) not in paths
    assert "SAVE_PATH" not in environment
    assert environment["SIMLINGO_EVIDENCE"] == "out"


def test_tfpp_captures_and_refuses_token_layers():
    assert agent_and_capture_environment(10, policy="tfpp") == (TFPP_AGENT, {"SIMLINGO_CAPTURE_EVERY": "10"})
    with pytest.raises(ValueError, match="per-token"):
        agent_and_capture_environment(10, [10], policy="tfpp")
