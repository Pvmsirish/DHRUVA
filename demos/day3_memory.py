"""Day 3 demo — durable memory across two independent conversations.

Conversation 1 saves a fact through the memory tool.  Conversation 2 starts
completely fresh over the same directory with NO tools at all — it can only
answer from the system prompt, proving recall() carries the fact across
sessions.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from odysseus.loop import run_loop
from odysseus.memory import memory_tool, recall
from odysseus.provider import DEFAULT_MODEL
from odysseus.security import Policy


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
    """Save a fact in session 1; recall it with no tools in session 2."""
    workdir = Path(tempfile.mkdtemp(prefix="dhruva_day3mem_"))
    policy = Policy("yolo")

    print("═" * 60)
    print("  Session 1 — agent saves a fact")
    print("═" * 60)
    tool = memory_tool(workdir)
    run_loop(DEFAULT_MODEL,
             "You are an assistant with durable memory. Use the "
             "remember_fact tool to store facts the user asks you to keep.",
             [{"role": "user", "text": "Remember that the launch codename "
               "is Aurora-9 and launch day is Friday."}],
             {tool.name: tool}, on_event, policy.check)

    print("\n" + "═" * 60)
    print("  Session 2 — fresh conversation, no tools, memory in system")
    print("═" * 60)
    system = ("You are an assistant with durable memory.\n\n"
              "# Durable memory\n" + recall(workdir))
    answer = run_loop(DEFAULT_MODEL, system,
                      [{"role": "user", "text": "What is the launch "
                        "codename, and when do we launch?"}],
                      {}, on_event, policy.check)

    ok = "Aurora-9" in answer and "Friday" in answer
    print(f"\nMemory recalled correctly: {ok}")


if __name__ == "__main__":
    main()
