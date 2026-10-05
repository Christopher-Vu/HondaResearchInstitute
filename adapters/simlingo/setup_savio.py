"""Prepare the Linux runtime on Savio: pinned SimLingo source and weights, CARLA with maps, the policy venv.

Run once on a Savio login node, from a clone of this repository on scratch:

    uv run --no-project --python 3.10 --with pyyaml adapters/simlingo/setup_savio.py

Every step is idempotent and checksum-verified, so rerun it after any interruption.
"""
from __future__ import annotations

import json
import os
import shlex
import shutil
import socket
import subprocess
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from artifacts import load_manifest, sha256, verify_artifacts
from route_run import BASE_MODEL, CHECKPOINT, ROOT, SOURCE
from run_savio import CARLA_ROOT

DOWNLOADS = ROOT / ".runtime/downloads"
VENV = ROOT / ".runtime/policy-venv"
MAPS_DIRECTORY = CARLA_ROOT / "CarlaUE4/Content/Carla/Maps"
HUGGING_FACE = "https://huggingface.co"
BASE_MODEL_SKIPPED = ("examples/", "README.md", ".gitattributes")


def run(command: list[str], cwd: Path | None = None, log: Path | None = None) -> None:
    print("+ " + shlex.join(command) + (f" > {log}" if log else ""), flush=True)
    if log is None:
        subprocess.run(command, cwd=cwd, check=True)
        return
    with log.open("w") as stream:
        subprocess.run(command, cwd=cwd, check=True, stdout=stream, stderr=subprocess.STDOUT)


def download(url: str, target: Path, size: int, digest: str | None) -> None:
    """Resume a partial download, then accept it only at the expected size and checksum."""
    marker = target.with_name(target.name + ".verified")
    if target.is_file() and marker.is_file():
        return
    if target.is_file() and target.stat().st_size == size and digest in (None, sha256(target)):
        marker.write_text((digest or "size-verified") + "\n")
        return
    partial = target.with_name(target.name + ".part")
    target.parent.mkdir(parents=True, exist_ok=True)
    if partial.is_file() and partial.stat().st_size > size:
        partial.unlink()
    if not partial.is_file() or partial.stat().st_size < size:
        run(["curl", "-fL", "--retry", "5", "--retry-delay", "10", "-C", "-", "-o", str(partial), url])
    if partial.stat().st_size != size:
        raise ValueError(f"{target.name}: expected {size} bytes, received {partial.stat().st_size}")
    if digest is not None and sha256(partial) != digest:
        partial.unlink()
        raise ValueError(f"{target.name}: checksum differs from the pinned value; the download was deleted")
    partial.replace(target)
    marker.write_text((digest or "size-verified") + "\n")


def hugging_face_files(repository: str, revision: str) -> list[dict[str, Any]]:
    url = f"{HUGGING_FACE}/api/models/{repository}/revision/{revision}?blobs=true"
    with urllib.request.urlopen(url, timeout=60) as response:
        siblings: list[dict[str, Any]] = json.load(response)["siblings"]
    return siblings


def download_hugging_face(repository: str, revision: str, wanted: list[str], target: Path) -> None:
    files = {entry["rfilename"]: entry for entry in hugging_face_files(repository, revision)}
    for name in wanted:
        entry = files[name]
        digest = (entry.get("lfs") or {}).get("sha256")
        download(f"{HUGGING_FACE}/{repository}/resolve/{revision}/{name}", target / name, entry["size"], digest)


def apply_once(patch: Path) -> None:
    applied = subprocess.run(["git", "-C", str(SOURCE), "apply", "--reverse", "--check", str(patch)],
                             capture_output=True).returncode == 0
    if not applied:
        run(["git", "-C", str(SOURCE), "apply", str(patch)])


def prepare_source(manifest: dict[str, Any]) -> None:
    source = manifest["source"]
    if not SOURCE.is_dir():
        run(["git", "clone", source["repository"], str(SOURCE)])
    run(["git", "-C", str(SOURCE), "checkout", "--detach", source["revision"]])
    for patch in (source["patch"], source["benchmark_patch"]):
        apply_once(ROOT / patch)


def prepare_weights(manifest: dict[str, Any]) -> None:
    checkpoint = manifest["checkpoint"]
    download_hugging_face(checkpoint["repository"], checkpoint["revision"],
                          ["simlingo/.hydra/config.yaml", checkpoint["file"]], ROOT / "checkpoints")
    base = manifest["base_model"]
    names = [entry["rfilename"] for entry in hugging_face_files(base["repository"], base["revision"])]
    download_hugging_face(base["repository"], base["revision"],
                          [name for name in names if not name.startswith(BASE_MODEL_SKIPPED)], BASE_MODEL)


def download_carla(linux: dict[str, Any]) -> tuple[Path, Path]:
    archives = []
    for key in ("server", "additional_maps"):
        archive = linux[key]
        target = DOWNLOADS / archive["package"]
        download(archive["source_url"], target, archive["bytes"], archive["sha256"])
        archives.append(target)
    return archives[0], archives[1]


def extract_carla(server: Path) -> None:
    if (CARLA_ROOT / ".extracted").is_file():
        return
    staging = CARLA_ROOT.with_name(CARLA_ROOT.name + ".partial")
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True)
    run(["tar", "-xzf", str(server), "-C", str(staging)])
    (staging / ".extracted").touch()
    shutil.rmtree(CARLA_ROOT, ignore_errors=True)
    staging.rename(CARLA_ROOT)


def import_maps(maps: Path, towns: list[str]) -> None:
    if (CARLA_ROOT / ".maps-imported").is_file():
        return
    staged = CARLA_ROOT / "Import" / maps.name
    staged.unlink(missing_ok=True)
    os.link(maps, staged)
    run(["bash", "ImportAssets.sh"], cwd=CARLA_ROOT, log=ROOT / ".runtime/carla-import.log")
    missing = [town for town in towns if not any(MAPS_DIRECTORY.glob(f"{town}*"))]
    if missing:
        raise RuntimeError(f"Benchmark towns missing after map import: {missing}")
    (CARLA_ROOT / ".maps-imported").touch()


def prepare_venv(linux: dict[str, Any]) -> str:
    uv = os.environ.get("UV", "uv")
    python = VENV / "bin/python"
    if not python.is_file():
        run([uv, "venv", "--python", linux["python"], str(VENV)])
    run([uv, "pip", "install", "--python", str(python), "-r", str(ROOT / linux["requirements"])])
    probe = "import carla, torch, transformers; print(torch.__version__, torch.version.cuda)"
    return subprocess.check_output([str(python), "-c", probe], text=True).strip()


def main() -> None:
    os.environ.setdefault("UV_CACHE_DIR", str(ROOT / ".runtime/uv-cache"))
    manifest = load_manifest()
    linux = manifest["linux"]
    prepare_source(manifest)
    prepare_weights(manifest)
    server, maps = download_carla(linux)
    extract_carla(server)
    import_maps(maps, manifest["benchmark"]["towns"])
    torch_build = prepare_venv(linux)
    verify_artifacts(SOURCE, CHECKPOINT)
    report = {
        "scope": "savio_runtime_setup", "host": socket.gethostname(),
        "finished": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_revision": manifest["source"]["revision"], "checkpoint_sha256": manifest["checkpoint"]["sha256"],
        "carla_root": str(CARLA_ROOT), "benchmark_towns_present": manifest["benchmark"]["towns"],
        "torch_and_cuda_build": torch_build, "gpu_verified": False,
    }
    output = ROOT / "results/setup/savio-setup.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
