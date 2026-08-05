"""Day 3 — Durable memory.

Concept: memory is a file, not a database.  Facts worth keeping across
conversations live in MEMORY.md inside the working directory; each new
session folds the file into the system prompt, so recall costs no tool
calls.

Design rules
 • remember() appends — history is never silently rewritten.
 • recall() returns raw markdown; the caller decides where it goes.
 • The memory tool is a thin closure over remember(), so agents can save
   facts mid-conversation.
"""

from __future__ import annotations

from pathlib import Path

from odysseus.tools import Tool, tool

MEMORY_FILE = "MEMORY.md"


def memory_path(workdir: str | Path) -> Path:
    """Return the path of the memory file inside *workdir*."""
    return Path(workdir) / MEMORY_FILE


def remember(workdir: str | Path, fact: str) -> str:
    """Append *fact* as one bullet to the memory file, creating it if needed."""
    path = memory_path(workdir)
    header = "" if path.exists() else "# Memory\n\n"
    with path.open("a", encoding="utf-8") as fh:
        fh.write(f"{header}- {fact.strip()}\n")
    return f"Remembered: {fact.strip()}"


def recall(workdir: str | Path) -> str:
    """Return the memory file contents, or an empty string when absent."""
    path = memory_path(workdir)
    return path.read_text(encoding="utf-8") if path.exists() else ""


def memory_tool(workdir: str | Path) -> Tool:
    """Build a tool that lets the agent persist facts for future sessions."""
    @tool("Save a fact to durable memory so future conversations know it",
          fact="The fact to remember, one short sentence")
    def remember_fact(fact: str) -> str:
        """Closure over remember() bound to this working directory."""
        return remember(workdir, fact)
    return remember_fact
