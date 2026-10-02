"""Config loading, content hashing and TBD detection.

PRD 6.2: every experiment is a YAML config, and results are keyed by config
content hash. No result that cannot be regenerated from a hash.

Runs anywhere; no GPU, no cluster.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit("pyyaml is required: pip install pyyaml") from exc

TBD_PREFIX = "TBD-"


class ConfigError(ValueError):
    pass


def load(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        raise ConfigError("no config at %s" % p)
    with p.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ConfigError("%s: top level must be a mapping" % p)
    return data


def content_hash(config: dict[str, Any]) -> str:
    """Stable sha256 over the config's content.

    Key order is normalised so that reformatting a file does not change its
    hash, but any value change does.
    """
    blob = json.dumps(config, sort_keys=True, separators=(",", ":"),
                      default=str).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def find_tbd(config: dict[str, Any], _path: str = "") -> list[str]:
    """Dotted paths of every value still marked TBD-*, or null where a value is
    required. Used to refuse a run that would silently use a placeholder.
    """
    out: list[str] = []
    for key, val in config.items():
        here = "%s.%s" % (_path, key) if _path else str(key)
        if isinstance(val, dict):
            out.extend(find_tbd(val, here))
        elif isinstance(val, list):
            for i, item in enumerate(val):
                if isinstance(item, dict):
                    out.extend(find_tbd(item, "%s[%d]" % (here, i)))
                elif isinstance(item, str) and item.startswith(TBD_PREFIX):
                    out.append("%s[%d]" % (here, i))
        elif isinstance(val, str) and val.startswith(TBD_PREFIX):
            out.append(here)
    return out


def require_resolved(config: dict[str, Any], path: str | Path = "<config>") -> None:
    """Raise unless every TBD placeholder has been filled.

    Called before anything that consumes compute, so that a half-filled config
    fails immediately with a list of what is missing rather than producing a run
    whose provenance is a placeholder.
    """
    tbd = find_tbd(config)
    if tbd:
        raise ConfigError(
            "%s has %d unresolved placeholder(s):\n  %s\n"
            "Fill these from the step that measures them before running."
            % (path, len(tbd), "\n  ".join(tbd)))


def describe(path: str | Path) -> str:
    cfg = load(path)
    tbd = find_tbd(cfg)
    lines = ["%s" % path,
             "  hash: %s" % content_hash(cfg)[:16],
             "  keys: %s" % ", ".join(sorted(cfg)),
             "  unresolved: %d" % len(tbd)]
    lines.extend("    - %s" % t for t in tbd)
    return "\n".join(lines)
