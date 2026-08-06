"""Day 3 demo — durable memory across two independent conversations.

Conversation 1 saves facts through a remember tool.  Conversation 2 starts
completely fresh over the same directory with NO tools at all — it can only
answer from build_system_prompt(), proving DHRUVA.md carries facts across
sessions.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from odysseus.loop import run_loop
from odysseus.memory import build_system_prompt, remember
from odysseus.provider import DEFAULT_MODEL
from odysseus.security import Policy
from odysseus.tools import tool


def on_event(kind: str, payload: dict) -> None:
    """Print each loop event compactly."""
    if kind == "assistant":
        if payload.get("text"):
            print(f"🤖 {payload['text']}")
        for c in payload.get("tool_calls", []):
            print(f"🔧 {c['name']}({c['args']})")
    elif kind == "tool_end":
        print(f"   ↳ {payload['result']}")


def main() -> None:
    """Save facts in session 1; recall them with no tools in session 2."""
    workdir = Path(tempfile.mkdtemp(prefix="dhruva_day3mem_"))
    policy = Policy("yolo")

    @tool("Save a note to durable project memory for future conversations",
          note="The note to remember, one short sentence")
    def remember_note(note: str) -> str:
        """Demo closure over remember() bound to this working directory."""
        return remember(workdir, note)

    print("═" * 60)
    print("  Session 1 — agent saves a fact")
    print("═" * 60)
    run_loop(DEFAULT_MODEL, build_system_prompt(workdir),
             [{"role": "user", "text": "Remember that the launch codename "
               "is Aurora-9 and launch day is Friday."}],
             {remember_note.name: remember_note}, on_event, policy.check)

    print("\n" + "═" * 60)
    print("  Session 2 — fresh conversation, no tools, memory in system")
    print("═" * 60)
    answer = run_loop(DEFAULT_MODEL, build_system_prompt(workdir),
                      [{"role": "user", "text": "What is the launch "
                        "codename, and when do we launch?"}],
                      {}, on_event, policy.check)

    ok = "Aurora-9" in answer and "Friday" in answer
    print(f"\nMemory recalled correctly: {ok}")


if __name__ == "__main__":
    main()
