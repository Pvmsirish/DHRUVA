"""Day 4 — CLI (stub; day 5 completes it).

Concept: the CLI is a thin shell over Harness.  Today it runs one task so
``python -m odysseus "<task>"`` already works end-to-end; day 5 adds flags
for model, policy mode, resume, and fleet runs.
"""

from __future__ import annotations

import sys

from odysseus.harness import Harness


def _print_event(kind: str, payload: dict) -> None:
    """Minimal terminal renderer for loop events."""
    if kind == "assistant" and payload.get("text"):
        print(payload["text"])
    elif kind == "tool_start":
        print(f"→ {payload['name']}({str(payload['args'])[:100]})")


def main(argv: list[str] | None = None) -> int:
    """Run one task in the current directory (stub — day 5 expands)."""
    args = sys.argv[1:] if argv is None else argv
    if not args:
        print('usage: python -m odysseus "<task>"')
        return 2
    Harness(on_event=_print_event).run(" ".join(args))
    return 0
