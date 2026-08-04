"""Day 1 demo — roll dice with a hand-built tool.

Concept: prove the full think → act → observe cycle end-to-end with the
simplest possible tool.  The demo constructs a tool object by hand (no
framework), wires a printing *on_event*, and asks the model a question that
requires a tool call followed by arithmetic.
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

# Ensure the repo root is importable when run as ``python demos/day1_dice.py``.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from odysseus.loop import run_loop
from odysseus.provider import DEFAULT_MODEL


# ── hand-built tool ─────────────────────────────────────────────────────────

class RollDiceTool:
    """A minimal tool object — .spec for the schema, .run for execution."""

    spec = {"schema": {
        "name": "roll_dice",
        "description": "Roll count six-sided dice",
        "parameters": {
            "type": "object",
            "properties": {
                "count": {"type": "string", "description": "How many dice"},
            },
            "required": ["count"],
        },
    }}

    def run(self, *, count: str) -> str:
        """Roll *count* six-sided dice and return the results."""
        n = int(count)
        rolls = [random.randint(1, 6) for _ in range(n)]
        return f"Rolled {n} dice: {rolls}"


# ── event printer ───────────────────────────────────────────────────────────

def on_event(kind: str, payload: dict) -> None:
    """Print each loop event so the transcript is visible."""
    if kind == "assistant":
        text = payload.get("text", "")
        calls = payload.get("tool_calls", [])
        if text:
            print(f"\n🤖 Assistant: {text}")
        if calls:
            for c in calls:
                print(f"\n🔧 Tool call: {c['name']}({c['args']})")
    elif kind == "tool_start":
        pass  # tool_end carries the interesting part
    elif kind == "tool_end":
        print(f"   ↳ Result: {payload['result']}")


def before_tool(_call: dict) -> str | None:
    """Allow every tool call — day 2 adds real policy here."""
    return None


# ── main ────────────────────────────────────────────────────────────────────

def main() -> None:
    """Run the dice demo."""
    print("═" * 60)
    print("Day 1 Demo — Dice Roll")
    print("═" * 60)

    task = "Roll 3 dice and tell me whether the total beats 10."
    print(f"\n📝 Task: {task}")

    messages = [{"role": "user", "text": task}]
    tools = {"roll_dice": RollDiceTool()}

    answer = run_loop(
        model=DEFAULT_MODEL,
        system="You are a helpful assistant. Use tools when needed.",
        messages=messages,
        tools=tools,
        on_event=on_event,
        before_tool=before_tool,
    )

    print(f"\n{'═' * 60}")
    print(f"Final answer: {answer}")
    print("═" * 60)


if __name__ == "__main__":
    main()
