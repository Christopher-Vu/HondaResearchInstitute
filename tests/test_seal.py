"""PRD 9.1 sealing: the commitment binds the exact key bytes, and scoring builds gaps from the key."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from harness import seal  # noqa: E402

KEY = {"version": 1, "gaps": [
    {"gap_id": "G1", "tier": "T2_interactional", "predicate": [{"field": "weather.fog_density", "op": ">=", "value": 50}],
     "efficacy": {"uplift": 0.3}},
    {"gap_id": "D1", "tier": "T0_control", "decoy": True,
     "predicate": [{"field": "injected", "op": "==", "value": "Thing"}]},
]}


@pytest.fixture
def files(tmp_path):
    key, salt = tmp_path / "key.json", tmp_path / "salt"
    key.write_text(json.dumps(KEY))
    salt.write_text("0f" * 32)
    return key, salt, tmp_path / "KEY_COMMITMENT.txt"


def test_commit_then_verify_and_any_change_breaks_it(files):
    key, salt, out = files
    digest = seal.write_commitment(key, salt, out)
    assert len(digest) == 64 and seal.verify(key, salt, out)
    key.write_text(json.dumps(KEY, indent=1))
    assert not seal.verify(key, salt, out)


def test_a_commitment_is_written_once(files):
    key, salt, out = files
    seal.write_commitment(key, salt, out)
    with pytest.raises(FileExistsError):
        seal.write_commitment(key, salt, out)


def test_the_salt_matters(files, tmp_path):
    key, salt, out = files
    other = tmp_path / "other"
    other.write_text("aa" * 32)
    assert seal.commitment(key, salt) != seal.commitment(key, other)


def test_gaps_from_key_use_predicates_and_outcomes():
    manifest = [{"id": "1", "weather": {"fog_density": 90}}, {"id": "2", "weather": {"fog_density": 90}},
                {"id": "3", "weather": {"fog_density": 0}}, {"id": "4", "injected": "Thing"},
                {"id": "5", "weather": {"fog_density": 90}}]
    failed = {"1": True, "2": False, "3": True, "4": False}
    g1, d1 = seal.gaps_from_key(KEY["gaps"], manifest, failed)
    assert g1.slice_rollouts == {"1", "2"} and g1.failing_rollouts == {"1"} and g1.efficacy == {"uplift": 0.3}
    assert d1.is_decoy and d1.slice_rollouts == {"4"} and d1.failing_rollouts == set()


def test_bad_keys_are_refused(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"gaps": [{"gap_id": "X", "tier": "T9", "predicate": [{}]}]}))
    with pytest.raises(ValueError):
        seal.load_key(bad)
    bad.write_text(json.dumps({"gaps": [{"gap_id": "X", "tier": "T0_control", "predicate": []}]}))
    with pytest.raises(ValueError):
        seal.load_key(bad)
