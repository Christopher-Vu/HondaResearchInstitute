"""The sealed-key guard must actually fail on a leak.

A guard that silently stops working is worse than no guard, because we would
rely on it. This test injects both leak shapes into a temp tree and asserts the
checker exits non-zero.
"""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUARD = ROOT / "scripts" / "check_sealed_imports.py"


def _run(root: Path) -> subprocess.CompletedProcess:
    env = {**os.environ, "SEALED_GUARD_ROOT": str(root)}
    return subprocess.run([sys.executable, str(GUARD)], cwd=root,
                          capture_output=True, text=True, env=env)


def _tree(tmp_path: Path) -> Path:
    """A synthetic repo root containing only src/discovery."""
    (tmp_path / "src" / "discovery").mkdir(parents=True)
    return tmp_path


def test_clean_tree_passes(tmp_path):
    t = _tree(tmp_path)
    (t / "src" / "discovery" / "m.py").write_text("X = 1\n", encoding="utf-8")
    assert _run(t).returncode == 0


def test_string_path_leak_is_caught(tmp_path):
    t = _tree(tmp_path)
    (t / "src" / "discovery" / "m.py").write_text(
        'KEY = "gaps/sealed/key_v1.json"\n', encoding="utf-8")
    r = _run(t)
    assert r.returncode == 1
    assert "SEALED-KEY LEAK" in r.stdout


def test_import_leak_is_caught(tmp_path):
    t = _tree(tmp_path)
    (t / "src" / "discovery" / "m.py").write_text(
        "from gaps.sealed import key_v1\n", encoding="utf-8")
    assert _run(t).returncode == 1


def test_docstring_mentioning_sealed_is_not_a_violation(tmp_path):
    """Prose cannot open a file, and these packages are supposed to document
    the rule. False positives train us to ignore the checker."""
    t = _tree(tmp_path)
    (t / "src" / "discovery" / "m.py").write_text(
        '"""Never read gaps/sealed/key_v1.json."""\nX = 1\n', encoding="utf-8")
    assert _run(t).returncode == 0


def test_escape_hatch_is_honoured(tmp_path):
    t = _tree(tmp_path)
    (t / "src" / "discovery" / "m.py").write_text(
        'KEY = "gaps/sealed/key_v1.json"  # sealed-ok\n', encoding="utf-8")
    assert _run(t).returncode == 0
