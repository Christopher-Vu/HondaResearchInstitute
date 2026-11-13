"""Guards for H25's opaque-frame workflow before it reads real route frames."""
import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "docs/research/experiments/h25-caption-cluster"


def load(name):
    spec = importlib.util.spec_from_file_location(f"h25_{name}", EXPERIMENT / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[f"h25_{name}"] = module
    spec.loader.exec_module(module)
    return module


audit = load("audit")


def transcript(path, calls):
    path.write_text("\n".join(json.dumps({"message": {"content": [{
        "type": "tool_use", "name": name, "input": values,
    }]}}) for name, values in calls) + "\n")


def run_audit(tmp_path, calls):
    frames = tmp_path / "frames"
    allowed = frames / "a" / "opaque-id"
    allowed.mkdir(parents=True, exist_ok=True)
    (allowed / "f0.png").touch()
    transcripts = tmp_path / "transcripts"
    transcripts.mkdir()
    transcript(transcripts / "agent-1.jsonl", calls)
    output = tmp_path / "audit.json"
    old_argv = sys.argv
    sys.argv = ["audit.py", str(transcripts), str(frames), "--output", str(output)]
    try:
        audit.main()
    finally:
        sys.argv = old_argv
    return json.loads(output.read_text())


def test_audit_accepts_only_a_single_leaf_frame_folder(tmp_path):
    frame = tmp_path / "frames" / "a" / "opaque-id" / "f0.png"
    result = run_audit(tmp_path, [("Read", {"file_path": str(frame)})])
    assert result == {"frames_opened": 1, "breaches": []}


def test_audit_rejects_a_sibling_whose_path_only_shares_the_prefix(tmp_path):
    # This was previously accepted by the string-prefix check for the real frames root.
    sibling = tmp_path / "frames-secret" / "a" / "opaque-id" / "f0.png"
    sibling.parent.mkdir(parents=True)
    sibling.touch()
    result = run_audit(tmp_path, [("Read", {"file_path": str(sibling)})])
    assert result["frames_opened"] == 0
    assert len(result["breaches"]) == 1


def test_audit_rejects_a_read_that_escapes_the_assigned_leaf_folder(tmp_path):
    frames = tmp_path / "frames"
    (frames / "a" / "opaque-id" / "nested").mkdir(parents=True)
    escaped = frames / "a" / "opaque-id" / "nested" / "other.png"
    escaped.touch()
    result = run_audit(tmp_path, [("Read", {"file_path": str(escaped)})])
    assert result["frames_opened"] == 0
    assert len(result["breaches"]) == 1
