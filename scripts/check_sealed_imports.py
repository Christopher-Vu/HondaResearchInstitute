#!/usr/bin/env python3
"""CI guard: nothing under discovery/, baselines/ or gate/ may read the sealed key.

PRD 6.2 and 9.1. With two people there is no real separation of duties, so the
protection is mechanical rather than social. This is the mechanism.

A leak does not raise an error at runtime; it silently invalidates the headline
metric, which is why it needs a guard rather than care.

    python scripts/check_sealed_imports.py     # exit 1 on violation
"""
from __future__ import annotations

import ast
import os
import re
import sys
from pathlib import Path

# Overridable so the guard can be tested against a synthetic tree, and so it
# can be pointed at a checkout other than its own.
ROOT = Path(os.environ.get("SEALED_GUARD_ROOT")
            or Path(__file__).resolve().parents[1]).resolve()

GUARDED = (
    "discovery", "baselines", "gate",
    "src/discovery", "src/baselines", "src/gate",
)

FORBIDDEN_IMPORT = re.compile(r"(^|\.)gaps\.sealed|(^|\.)sealed($|\.)")
FORBIDDEN_PATH = re.compile(
    r"gaps[/\\]+sealed"      # gaps/sealed or gaps\sealed
    r"|key_v\d+\.json"       # the answer key itself
    r"|\bsalt\b",            # the commitment salt
    re.IGNORECASE,
)

ALLOW_MARKER = "sealed-ok"  # inline escape hatch, must be justified in review


def _docstring_nodes(tree: ast.AST) -> set[int]:
    """ids of Constant nodes that are docstrings.

    Prose cannot open a file, and the guarded packages are *supposed* to say in
    their docstrings that they must not touch the key. Flagging that text would
    train us to ignore the checker, which is worse than the risk it prevents.
    """
    out: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef,
                             ast.AsyncFunctionDef)):
            body = getattr(node, "body", None) or []
            if (body and isinstance(body[0], ast.Expr)
                    and isinstance(body[0].value, ast.Constant)
                    and isinstance(body[0].value.value, str)):
                out.add(id(body[0].value))
    return out


def check_file(path: Path) -> list[str]:
    bad: list[str] = []
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()

    def allowed(lineno: int) -> bool:
        idx = lineno - 1
        return 0 <= idx < len(lines) and ALLOW_MARKER in lines[idx]

    try:
        tree = ast.parse(text, filename=str(path))
    except SyntaxError as exc:
        return ["%s: syntax error: %s" % (path, exc)]

    docstrings = _docstring_nodes(tree)

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if FORBIDDEN_IMPORT.search(alias.name) and not allowed(node.lineno):
                    bad.append("%s:%d imports %s" % (path, node.lineno, alias.name))
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if FORBIDDEN_IMPORT.search(mod) and not allowed(node.lineno):
                bad.append("%s:%d imports from %s" % (path, node.lineno, mod))
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            if id(node) in docstrings:
                continue
            if FORBIDDEN_PATH.search(node.value) and not allowed(node.lineno):
                bad.append("%s:%d references sealed material: %r"
                           % (path, node.lineno, node.value[:60]))
    return bad


def main() -> int:
    violations: list[str] = []
    checked = 0
    present = [r for r in GUARDED if (ROOT / r).is_dir()]

    for rel in present:
        for f in (ROOT / rel).rglob("*.py"):
            checked += 1
            violations.extend(check_file(f))

    if violations:
        print("SEALED-KEY LEAK: %d violation(s)\n" % len(violations))
        for v in violations:
            print("  " + v.replace(str(ROOT) + "\\", "").replace(str(ROOT) + "/", ""))
        print("\nDiscovery, baseline and gate code must never read the answer key.")
        print("A leak invalidates the headline metric silently (PRD 9.1).")
        print("If a reference is genuinely needed, add '# sealed-ok' on that line")
        print("and justify it in review.")
        return 1

    scope = ", ".join(present) if present else "(no guarded dirs yet)"
    print("ok: %d file(s) clean in %s" % (checked, scope))
    return 0


if __name__ == "__main__":
    sys.exit(main())
