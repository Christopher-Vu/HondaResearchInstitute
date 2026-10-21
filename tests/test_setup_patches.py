"""The source patch chain in setup_savio must cover every patch the manifest names."""
import pytest

import setup_savio
from artifacts import load_manifest
from setup_savio import ROOT, SOURCE_PATCH_KEYS, prepare_source


def source_patches() -> dict[str, str]:
    source = load_manifest()["source"]
    return {key: value for key, value in source.items() if key.endswith("patch") and value.endswith(".patch")}


def test_every_manifest_source_patch_exists():
    for patch in source_patches().values():
        assert (ROOT / patch).is_file(), patch


def test_setup_chain_covers_every_manifest_source_patch():
    assert set(SOURCE_PATCH_KEYS) == set(source_patches())


def test_prepare_source_applies_crossing_patch_last(monkeypatch, tmp_path):
    applied = []
    monkeypatch.setattr(setup_savio, "SOURCE", tmp_path)
    monkeypatch.setattr(setup_savio, "run", lambda command: None)
    monkeypatch.setattr(setup_savio, "apply_once", applied.append)
    prepare_source(load_manifest())
    assert [patch.name for patch in applied][-1] == "left-crossing-walk.patch"
    assert len(applied) == len(SOURCE_PATCH_KEYS)
