"""Day 4 — Durable sessions and crash repair.

Concept: every conversation is an append-only JSONL file, one message per
line.  A crash mid-write leaves at most one torn line at the tail; load()
tolerates it, and repair restores the tool call/response pairing the
provider requires.

Design rules
 • Append-only — session files are never rewritten in place.
 • A torn tail costs one line of history, never a crash.
 • Repaired gaps stay visible to the model ("Interrupted before this ran").
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

SESSION_DIR = ".odysseus/sessions"


def new_session(workdir: str | Path, label: str = "session") -> Path:
    """Create the session directory and return a fresh timestamped path."""
    d = Path(workdir) / SESSION_DIR
    d.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^A-Za-z0-9-]+", "-", label).strip("-")[:40] or "session"
    return d / f"{int(time.time())}-{slug}.jsonl"


def append(path: str | Path, message: dict[str, Any]) -> None:
    """Append one message as one JSON line."""
    with Path(path).open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(message, ensure_ascii=False) + "\n")


def load(path: str | Path) -> list[dict[str, Any]]:
    """Parse messages line by line, tolerating a torn tail, then repair."""
    messages: list[dict[str, Any]] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        try:
            messages.append(json.loads(line))
        except json.JSONDecodeError:
            break  # torn tail from a crash mid-write — keep what parsed
    return _repair(messages)


def latest(workdir: str | Path) -> Path | None:
    """Return the newest session file in *workdir*, or None."""
    d = Path(workdir) / SESSION_DIR
    files = sorted(d.glob("*.jsonl")) if d.is_dir() else []
    return files[-1] if files else None


def _repair(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Fill tool results lost to a crash so call/response pairing holds."""
    for i in range(len(messages) - 1, -1, -1):
        if messages[i]["role"] != "assistant":
            continue
        have = sum(1 for m in messages[i + 1:] if m["role"] == "tool")
        for call in messages[i].get("tool_calls", [])[have:]:
            # call_id keeps the provider's call/result matching intact.
            messages.append({"role": "tool", "name": call["name"],
                             "text": "Interrupted before this ran "
                                     "(process restarted).",
                             "call_id": call.get("signature")})
        break
    return messages
