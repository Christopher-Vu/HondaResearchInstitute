"""The stub adapter (PRD 8.2): a policy unlike SimLingo meets the shard contract, and the pipeline runs on it end
to end. Its planted gap (fog with a pedestrian) is the one failure mode, so probe-residual should recover it."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "adapters" / "stub"))

import stub_adapter  # noqa: E402
from baselines.behavioral import BehavioralConfig, behavioral_directive  # noqa: E402
from baselines.behavioral import load_shard as behavioral_shard  # noqa: E402
from discovery.probe_residual import ProbeResidualConfig, load_shard, probe_residual_directive  # noqa: E402
from harness.schema import Gap  # noqa: E402
from harness.scoring import score  # noqa: E402
from harness.shards import shard_problems  # noqa: E402


@pytest.fixture(scope="module")
def stub(tmp_path_factory):
    output = tmp_path_factory.mktemp("stub-shards")
    return output, stub_adapter.generate(output, episodes=400, seed=0)


def planted(metas):
    failing = {m["route_id"] for m in metas if m["success"] is False and m["fog"] and m["pedestrian"]}
    return [Gap("planted_fog_pedestrian", "T2_interactional", failing)]


def test_every_stub_shard_meets_the_contract(stub):
    output, _ = stub
    assert [problems for path in output.glob("*.json") if (problems := shard_problems(path))] == []


def test_the_planted_gap_holds_fog_or_a_pedestrian_alone_does_not_fail(stub):
    _, metas = stub
    def rate(fog, pedestrian):
        group = [m for m in metas if m["fog"] == fog and m["pedestrian"] == pedestrian]
        return sum(not m["success"] for m in group) / len(group)
    assert rate(True, True) >= 0.4
    assert max(rate(True, False), rate(False, True), rate(False, False)) <= 0.05


def test_probe_residual_recovers_the_planted_gap_from_the_stub_s_activations(stub):
    output, metas = stub
    rollouts = [r for r in (load_shard(path, "mlp", 1) for path in sorted(output.glob("*.json"))) if r]
    directive = probe_residual_directive(rollouts, ProbeResidualConfig(min_cluster_size=40, min_support=10))
    report = score(directive, planted(metas))
    assert report.matches[0].matched


def test_b3_runs_on_the_stub(stub):
    output, metas = stub
    rollouts = [r for r in (behavioral_shard(path) for path in sorted(output.glob("*.json"))) if r]
    directive = behavioral_directive(rollouts, BehavioralConfig())
    assert directive.axes and score(directive, planted(metas)).mean_best_jaccard > 0
