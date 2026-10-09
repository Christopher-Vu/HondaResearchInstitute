"""Pinned-artifact checks shared by the model verifier and both route launchers."""
from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "configs/setup/simlingo-artifacts.yaml"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_manifest() -> dict[str, Any]:
    manifest: dict[str, Any] = yaml.safe_load(MANIFEST.read_text())
    return manifest


def verify_artifacts(source: Path, checkpoint: Path) -> dict[str, Any]:
    manifest = load_manifest()
    revision = subprocess.check_output(
        ["git", "-C", str(source), "rev-parse", "HEAD"], text=True,
    ).strip()
    if revision != manifest["source"]["revision"]:
        raise ValueError("SimLingo source revision does not match the artifact manifest")
    if sha256(checkpoint) != manifest["checkpoint"]["sha256"]:
        raise ValueError("SimLingo checkpoint checksum does not match the publisher")
    subprocess.run([
        "git", "-C", str(source), "apply", "--reverse", "--check",
        str(ROOT / manifest["source"]["patch"]),
    ], check=True)
    return manifest
