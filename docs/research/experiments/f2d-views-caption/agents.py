#!/usr/bin/env python3
"""The caption row's agent plumbing (docs/prereg-views.md, "The caption row"): H25's workflow.js as files.

    python agents.py inputs OUT POOL       # captions OUT/POOL/<id>.json -> 6 grouping inputs OUT/POOL/group-input-<r>.txt
    python agents.py groups OUT POOL       # OUT/POOL/group-<r>.json -> OUT/POOL/groups.json (to_axes.py's input)
    python agents.py audit TRANSCRIPTS FRAMES OUT --output audit.json
    python agents.py flags GROUPS.json POOL --output flags.json   # the prereg's synonym check on every mode name

The describing and grouping prompts are workflow.js's. The descriptions' order per run is workflow.js's `order`, over
ids sorted as strings. Checks match workflow.js: ids an agent invents are dropped and counted, a repeat stays in its
first mode, routes left out are counted, and a failed run scores as no axes.

Audit: a describing agent may Read only files in FRAMES/<pool>/<its id>/ and Write only OUT/<pool>/<its id>.json. A
grouping agent may Read only OUT/<pool>/group-input-<r>.txt and Write only OUT/<pool>/group-<r>.json. Anything else is
a breach, which voids that pool's row. Every agent's reported model id is listed.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

STEPS = [1, 7, 11, 13, 17, 19]
RUNS = 6


def flat(text) -> str:
    return re.sub(r"\s+", " ", str(text)).strip()


def order(items: list, run: int) -> list:
    k = len(items)
    step = STEPS[run % 6]
    usable = 1 if k % step == 0 else step
    return [items[(i * usable + run) % k] for i in range(k)]


def captions(out: Path, pool: str) -> list[dict]:
    rows = []
    for path in sorted((out / pool).glob("*.json")):
        if path.stem.startswith("group"):
            continue
        rows.append({"id": path.stem, **json.loads(path.read_text(encoding="utf-8"))})
    return sorted(rows, key=lambda r: r["id"])


def inputs(out: Path, pool: str) -> None:
    items = captions(out, pool)
    for run in range(RUNS):
        lines = [f"{c['id']}: scene: {flat(c['scene'])} | reason: {flat(c['reason'])} | mode: {flat(c['mode'])}"
                 for c in order(items, run)]
        (out / pool / f"group-input-{run}.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{len(items)} captions, {RUNS} grouping inputs")


def groups(out: Path, pool: str) -> None:
    items = captions(out, pool)
    known = {c["id"] for c in items}
    runs = []
    for run in range(RUNS):
        path = out / pool / f"group-{run}.json"
        raw = json.loads(path.read_text(encoding="utf-8")).get("modes", []) if path.exists() else None
        placed, invented, duplicated, modes = set(), 0, 0, []
        for mode in (raw or [])[:10]:
            members = []
            for m in mode["members"]:
                if m not in known:
                    invented += 1
                elif m in placed:
                    duplicated += 1
                else:
                    placed.add(m)
                    members.append(m)
            modes.append({"name": flat(mode["name"]), "members": members})
        runs.append({"run": run, "modes": modes, "invented": invented, "duplicated": duplicated,
                     "unassigned": len(known - placed), "failed": raw is None})
        print(f"run {run}: {len(modes)} modes, {invented} invented, {duplicated} repeats, "
              f"{len(known - placed)} unassigned{', failed' if raw is None else ''}")
    (out / pool / "groups.json").write_text(json.dumps({pool: {"captions": items, "runs": runs}}, indent=1) + "\n",
                                            encoding="utf-8")


def norm(path: str) -> str:
    return str(Path(path).resolve()).lower() if path else ""


def audit(transcripts: Path, frames: Path, out: Path, output: Path) -> None:
    frames_root, out_root = norm(str(frames)), norm(str(out))
    report = {"agents": 0, "frame_reads": 0, "breaches": [], "models": {}}
    for transcript in sorted(transcripts.rglob("agent-*.jsonl")):
        events = [json.loads(line) for line in transcript.read_text(encoding="utf-8").splitlines() if line.strip()]
        prompt = next((e["message"]["content"] for e in events if e.get("type") == "user"
                       and isinstance(e.get("message", {}).get("content"), str)), "")
        if prompt.startswith("You are a dispatcher"):  # may launch agents and nothing else
            report["dispatchers"] = report.get("dispatchers", 0) + 1
            for e in events:
                content = e.get("message", {}).get("content")
                for block in content if isinstance(content, list) else []:
                    if isinstance(block, dict) and block.get("type") == "tool_use" and block.get("name") not in (
                            "Agent", "SubagentHandback", "StructuredOutput", "ToolSearch"):
                        report["breaches"].append({"transcript": transcript.name, "tool": block.get("name")})
            continue
        caption = re.search(r"caption-frames/(\w+)/(\w+)/f0\.png", prompt)
        group = re.search(r"caption-out/(\w+)/group-input-(\d)\.txt", prompt)
        if not (caption or group):
            continue
        report["agents"] += 1
        if caption:
            pool, ident = caption.groups()
            reads, writes = norm(str(frames / pool / ident)), norm(str(out / pool / f"{ident}.json"))
        else:
            pool, run = group.groups()
            reads, writes = norm(str(out / pool / f"group-input-{run}.txt")), norm(str(out / pool / f"group-{run}.json"))
        seen = set()
        for e in events:
            for block in e.get("message", {}).get("content", []) if isinstance(e.get("message", {}).get("content"), list) else []:
                if not (isinstance(block, dict) and block.get("type") == "tool_use"):
                    continue
                name, inp = block.get("name"), block.get("input", {})
                if block.get("id") in seen or name in ("SubagentHandback", "StructuredOutput", "ToolSearch"):
                    continue
                seen.add(block.get("id"))
                path = norm(inp.get("file_path", ""))
                if name == "Read" and (path == reads or path.startswith(reads + "\\") or path.startswith(reads + "/")):
                    report["frame_reads"] += caption is not None
                    continue
                if name == "Write" and path == writes:
                    try:
                        report["models"].setdefault(json.loads(inp.get("content", "{}")).get("model", "unreported"), 0)
                        report["models"][json.loads(inp.get("content", "{}")).get("model", "unreported")] += 1
                    except json.JSONDecodeError:
                        report["models"]["unparsed"] = report["models"].get("unparsed", 0) + 1
                    continue
                report["breaches"].append({"transcript": transcript.name, "tool": name,
                                           "input": {k: inp.get(k) for k in ("file_path", "path", "pattern", "command") if inp.get(k)}})
    output.write_text(json.dumps(report, indent=1) + "\n")
    print(f"{report['agents']} agents, {report['frame_reads']} frame reads, {len(report['breaches'])} breaches, models {report['models']}")


PREREG = Path(__file__).resolve().parents[3] / "prereg-views.md"


def stems(text: str) -> list[str]:
    def stem(w: str) -> str:
        w = re.sub(r"(ing|ed)$", "", w) if len(w) > 5 else w
        return w[:-1] if len(w) > 3 and w.endswith("s") and not w.endswith("ss") else w
    return [stem(w) for w in re.findall(r"[a-z]+", text.lower())]


def synonyms() -> dict[str, list[list[str]]]:
    """The frozen list: the table rows after the prereg's '**Synonym list**' line."""
    text = PREREG.read_text(encoding="utf-8").split("**Synonym list**", 1)[1].split("\n## ", 1)[0]
    rows = re.findall(r"^\| (\w+) \| (.+?) \|$", text, flags=re.M)
    return {t: [stems(p) for p in m.split(",")] for t, m in rows if t != "Type"}


def flags(groups: Path, pool: str, output: Path) -> None:
    table = synonyms()
    out = []
    for run in json.loads(groups.read_text(encoding="utf-8"))[pool]["runs"]:
        for mode in run["modes"]:
            words = stems(mode["name"])
            hit = sorted(t for t, phrases in table.items() for p in phrases
                         if any(words[i:i + len(p)] == p for i in range(len(words))))
            out.append({"run": run["run"], "name": mode["name"], "size": len(mode["members"]), "types": sorted(set(hit))})
    output.write_text(json.dumps({"types_in_list": len(table), "modes": out}, indent=1) + "\n")
    print(f"{len(table)} types; {sum(bool(m['types']) for m in out)} of {len(out)} modes flagged")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    for cmd in ("inputs", "groups"):
        p = sub.add_parser(cmd)
        p.add_argument("out", type=Path)
        p.add_argument("pool")
    p = sub.add_parser("flags")
    p.add_argument("groups", type=Path)
    p.add_argument("pool")
    p.add_argument("--output", type=Path, required=True)
    p = sub.add_parser("audit")
    p.add_argument("transcripts", type=Path)
    p.add_argument("frames", type=Path)
    p.add_argument("out", type=Path)
    p.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.cmd == "flags":
        flags(args.groups, args.pool, args.output)
    elif args.cmd == "audit":
        audit(args.transcripts, args.frames, args.out, args.output)
    else:
        (inputs if args.cmd == "inputs" else groups)(args.out, args.pool)


if __name__ == "__main__":
    main()
