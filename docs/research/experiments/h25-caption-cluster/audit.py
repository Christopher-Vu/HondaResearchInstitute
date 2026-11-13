#!/usr/bin/env python3
"""H25's blinding audit: every file each agent opened, from the workflow's transcripts.

    python docs/research/experiments/h25-caption-cluster/audit.py TRANSCRIPT_DIR FRAMES_ROOT --output audit.json

A describing agent may open only files under FRAMES_ROOT/<pool>/<its id>/. A grouping agent may open nothing. Any
other tool use that names a path (Read, Glob, Grep, Bash, LS) is a breach, and the protocol voids that pool's run.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

PATH_KEYS = ("file_path", "path", "pattern", "command")


def tool_calls(transcript: Path):
    for line in transcript.read_text().splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        content = (event.get("message") or {}).get("content")
        for block in content if isinstance(content, list) else []:
            if isinstance(block, dict) and block.get("type") == "tool_use" and block.get("name") != "StructuredOutput":
                yield block.get("name"), {k: block.get("input", {}).get(k) for k in PATH_KEYS if block.get("input", {}).get(k)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("transcripts", type=Path)
    parser.add_argument("frames_root", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.frames_root.resolve()
    breaches, opened = [], 0
    for transcript in sorted(args.transcripts.rglob("agent-*.jsonl")):
        calls = list(tool_calls(transcript))
        folders = {Path(v["file_path"]).resolve().parent for name, v in calls if name == "Read" and "file_path" in v}
        for name, values in calls:
            path = values.get("file_path", "")
            candidate = Path(path).resolve() if name == "Read" and path else None
            # `str.startswith` would accept a sibling such as ``frames-secret``.
            # Caption inputs are exactly ROOT/<pool>/<opaque-id>/fN.png, so require
            # that shape as well as one folder per describing agent.
            is_frame = candidate is not None and candidate.is_relative_to(root) and \
                len(candidate.relative_to(root).parts) == 3 and candidate.suffix == ".png"
            if name == "Read" and is_frame and len(folders) == 1:
                opened += 1
                continue
            breaches.append({"transcript": transcript.name, "tool": name, "input": values})
    args.output.write_text(json.dumps({"frames_opened": opened, "breaches": breaches}, indent=1) + "\n")
    print(f"{opened} frame reads, {len(breaches)} breaches")


if __name__ == "__main__":
    main()
