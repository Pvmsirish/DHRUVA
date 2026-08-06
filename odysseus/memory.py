"""Day 3/4 — Durable memory and the base system prompt.

Concept: memory is a plain file the user can read and edit — DHRUVA.md in
the working directory.  The system prompt is rebuilt each session and folds
the file in, so recall costs no tool calls.

Design rules
 • remember() appends — history is never silently rewritten.
 • MEMORY_FILE is the single name; prompts and returns quote the constant.
 • build_system_prompt() is the one place the system prompt is assembled.
"""

from __future__ import annotations

import platform
from pathlib import Path

MEMORY_FILE = "DHRUVA.md"

BASE_PROMPT = (
    "You are Odysseus, a small sharp coding agent working inside one "
    "directory with the tools provided. Act, don't narrate. Inspect before "
    "assuming. Prefer edit_file for small changes. Verify after building by "
    "running or re-reading. Never repeat a failing call unchanged. When "
    "complete, reply with a short summary and stop calling tools."
)


def build_system_prompt(workdir: str | Path, extra: str = "") -> str:
    """Assemble the system prompt: base, environment, project memory, extra.

    Sections are joined by blank lines; absent sections are simply omitted.
    """
    parts = [BASE_PROMPT,
             f"Platform: {platform.system()}. "
             f"Working directory: {Path(workdir).resolve()}"]
    mem = Path(workdir) / MEMORY_FILE
    if mem.exists():
        parts.append(f"Project memory ({MEMORY_FILE}):\n"
                     + mem.read_text(encoding="utf-8"))
    if extra:
        parts.append(extra)
    return "\n\n".join(parts)


def remember(workdir: str | Path, note: str) -> str:
    """Append *note* as one bullet line to the memory file."""
    path = Path(workdir) / MEMORY_FILE
    with path.open("a", encoding="utf-8") as fh:
        fh.write(f"- {note}\n")
    return f"Remembered in {MEMORY_FILE}"
