"""Day 2 — Security policy for tool calls.

Concept: before_tool is a gate that every tool call passes through.  The
Policy class applies deny-patterns, mode-based access, and an optional
human-in-the-loop approver.

Design rules
 • Deny patterns are always enforced, even in yolo mode.
 • Read tools are always allowed — they cannot mutate state.
 • The approver callback is the extension point for interactive prompts.
"""

from __future__ import annotations

import re
from typing import Any, Callable

READ_TOOLS = {"read_file", "list_files", "grep"}

# Dangerous commands blocked regardless of mode.
DENY_PATTERNS: list[str] = [
    r"\brm\s+-\S+.*\s+(/|~|\$HOME)",       # rm -rf targeting / or ~ or $HOME
    r"\bsudo\b",                             # sudo
    r"\bmkfs\b",                             # mkfs
    r"\bdd\s+.*\bif=",                      # dd if=
    r"\bcurl\b.*\|\s*sh\b",                 # curl piped to sh
    r"\bgit\s+push\s+.*--force",            # git push --force
    r">\s*/dev/sd",                          # redirection onto /dev/sd devices
    r"\b(rmdir|rd)\s+.*(/[sS]|\\[sS])\b",  # Windows recursive delete
]


class Policy:
    """Tool-call gate with three modes: read-only, safe, yolo.

    *approver* is a callback ``(call, reason) -> bool``; when absent the
    default is to refuse.
    """

    def __init__(self, mode: str = "safe",
                 approver: Callable[[dict, str], bool] | None = None):
        self.mode = mode
        self.approver = approver

    def check(self, call: dict[str, Any]) -> str | None:
        """Return None to allow, or a reason string to block."""
        # Deny-pattern bash commands are always blocked, even in yolo mode.
        if call["name"] == "bash":
            cmd = call["args"].get("command", "")
            for pat in DENY_PATTERNS:
                if re.search(pat, cmd):
                    # Name the pattern so a blocked agent (and its user)
                    # can see exactly which rule fired.
                    return f"command matches deny pattern {pat!r}"

        # Read tools and yolo mode always pass.
        if call["name"] in READ_TOOLS or self.mode == "yolo":
            return None

        # Read-only blocks everything else.
        if self.mode == "read-only":
            return "read-only mode — write operations are blocked"

        # Safe mode: ask the approver, default to refuse.
        reason = f"{call['name']} requires approval in safe mode"
        if self.approver is not None and self.approver(call, reason):
            return None
        return reason
