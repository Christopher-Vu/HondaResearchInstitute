#!/usr/bin/env python3
"""The caption row on the Messages Batch API (docs/prereg-views.md, the record after the tag).

    python api.py describe FRAMES OUT POOL      # one request per route folder FRAMES/POOL/<id>/f*.png
    python api.py group OUT POOL                # 6 requests, one per OUT/POOL/group-input-<r>.txt (agents.py inputs)
    python api.py collect OUT POOL KIND         # waits for KIND's batches, writes OUT/POOL/<id>.json or group-<r>.json

The prompts are H25's workflow.js text. Frames go inline as images and the descriptions are pasted, as in H25; the
model has no tools, so it sees nothing but what the request carries. Every request's frames are listed with their
sha256 in OUT/POOL-records/requests-KIND.json (records stay out of OUT/POOL, which agents.py reads), which is the row's audit. Each answer keeps the model id the API reports.
The key comes from ANTHROPIC_API_KEY, or else ~/.anthropic-key (outside the repository).
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
import sys
import time
from pathlib import Path

import anthropic

MODEL = "claude-opus-5-5"
EFFORT = "medium"  # the model's default, stated so it is recorded
BATCH_BYTES = 180_000_000  # under the API's 256 MB per batch

DESCRIBE = """You are looking at {n} frame(s) from the forward camera of a car driven by an AI in a driving simulator.
The frames are one second apart, oldest first.
The episode ended in a failure, such as a collision, getting stuck, leaving the lane or a traffic violation, at or
shortly after the last frame. Look at what is in the scene and how it changes across the frames, think step by step
about what the AI most likely did wrong, then answer. Describe only what you can see; if the frames do not show the
cause, say so in the reason.

Answer with only a JSON object with the keys "scene" (what is in front of the car that matters, in one or two
sentences), "reason" (the most likely reason the driving AI failed, in one or two sentences) and "mode" (a short
phrase naming the kind of failure, 3 to 8 words)."""

GROUP = """Below are descriptions of {k} failed episodes of a driving AI in a simulator, one per line, each starting
with its id. First decide on a taxonomy of at most 10 failure modes that explains these failures, grouping by the cause
of the failure. Then assign every id to exactly one mode. Use every id exactly once and copy ids exactly. Name each mode
in a few plain words.

Answer with only a JSON object {{"modes": [{{"name": ..., "members": [ids]}}]}}.

{lines}"""


def params(content) -> dict:
    return {"model": MODEL, "max_tokens": 16000, "thinking": {"type": "adaptive"},
            "output_config": {"effort": EFFORT}, "messages": [{"role": "user", "content": content}]}


def submit(client, requests: list, out: Path, pool: str, kind: str) -> None:
    ids, batch, size = [], [], 0
    for custom_id, p, n in requests + [(None, None, BATCH_BYTES)]:
        if batch and (custom_id is None or size + n > BATCH_BYTES):
            b = client.messages.batches.create(requests=batch)
            ids.append(b.id)
            print(f"batch {b.id}: {len(batch)} requests")
            batch, size = [], 0
        if custom_id is not None:
            batch.append({"custom_id": custom_id, "params": p})
            size += n
    (out / f"{pool}-records" / f"batches-{kind}.txt").write_text("\n".join(ids) + "\n")


def describe(frames: Path, out: Path, pool: str) -> None:
    (out / pool).mkdir(parents=True, exist_ok=True)
    (out / f"{pool}-records").mkdir(exist_ok=True)
    requests, record = [], []
    for folder in sorted(p for p in (frames / pool).iterdir() if p.is_dir()):
        pngs = sorted(folder.glob("f*.png"), key=lambda p: int(p.stem[1:]))
        data = [p.read_bytes() for p in pngs]
        content = [{"type": "image", "source": {"type": "base64", "media_type": "image/png",
                                                 "data": base64.standard_b64encode(d).decode()}} for d in data]
        content.append({"type": "text", "text": DESCRIBE.format(n=len(pngs))})
        requests.append((folder.name, params(content), sum(len(d) for d in data) * 4 // 3 + 4000))
        record.append({"id": folder.name, "frames": [{"file": p.name, "sha256": hashlib.sha256(d).hexdigest()}
                                                    for p, d in zip(pngs, data)]})
    (out / f"{pool}-records" / "requests-describe.json").write_text(json.dumps({"model": MODEL, "effort": EFFORT, "prompt": DESCRIBE,
                                                                   "routes": record}, indent=1) + "\n")
    submit(anthropic.Anthropic(), requests, out, pool, "describe")


def group(out: Path, pool: str) -> None:
    requests, record = [], []
    for r in range(6):
        text = (out / pool / f"group-input-{r}.txt").read_text(encoding="utf-8").strip()
        prompt = GROUP.format(k=len(text.splitlines()), lines=text)
        requests.append((f"group-{r}", params([{"type": "text", "text": prompt}]), len(prompt) + 4000))
        record.append({"run": r, "sha256": hashlib.sha256(text.encode()).hexdigest()})
    (out / f"{pool}-records" / "requests-group.json").write_text(json.dumps({"model": MODEL, "effort": EFFORT, "prompt": GROUP,
                                                                "runs": record}, indent=1) + "\n")
    submit(anthropic.Anthropic(), requests, out, pool, "group")


def answer(msg) -> dict:
    text = "".join(b.text for b in msg.content if b.type == "text")
    found = re.search(r"\{.*\}", text, flags=re.S)
    return json.loads(found.group(0)) if found else {}


def collect(out: Path, pool: str, kind: str) -> None:
    client = anthropic.Anthropic()
    usage = {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0}
    failed = []
    for bid in (out / f"{pool}-records" / f"batches-{kind}.txt").read_text().split():
        while client.messages.batches.retrieve(bid).processing_status != "ended":
            time.sleep(60)
        for res in client.messages.batches.results(bid):
            if res.result.type != "succeeded":
                failed.append({"id": res.custom_id, "type": res.result.type})
                continue
            msg = res.result.message
            u = msg.usage
            usage["input"] += u.input_tokens
            usage["output"] += u.output_tokens
            usage["cache_read"] += u.cache_read_input_tokens or 0
            usage["cache_write"] += u.cache_creation_input_tokens or 0
            try:
                body = answer(msg)
            except json.JSONDecodeError:
                body = {}
            if msg.stop_reason != "end_turn" or not body:
                failed.append({"id": res.custom_id, "type": f"stop {msg.stop_reason}" if body else "no json"})
                continue
            body["model"] = msg.model
            (out / pool / f"{res.custom_id}.json").write_text(json.dumps(body, indent=1) + "\n", encoding="utf-8")
    cost = 0.5 * (usage["input"] * 4 + usage["output"] * 20 + usage["cache_read"] * 0.2 + usage["cache_write"] * 5) / 1e6
    (out / f"{pool}-records" / f"collect-{kind}.json").write_text(json.dumps({"usage": usage, "usd_batch": cost,
                                                                 "failed": failed}, indent=1) + "\n")
    print(f"{kind}: {len(failed)} failed, usage {usage}, ~${cost:.2f}")


if __name__ == "__main__":
    import os
    key = Path.home() / ".anthropic-key"
    if not os.environ.get("ANTHROPIC_API_KEY") and key.exists():
        os.environ["ANTHROPIC_API_KEY"] = key.read_text().strip()
    cmd, *rest = sys.argv[1:]
    if cmd == "describe":
        describe(Path(rest[0]), Path(rest[1]), rest[2])
    elif cmd == "group":
        group(Path(rest[0]), rest[1])
    else:
        collect(Path(rest[0]), rest[1], rest[2])
