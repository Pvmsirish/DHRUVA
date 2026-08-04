"""Day 2 demo — agent builds, runs, and is security-constrained.

Proves three things: (1) the agent can create and run code end-to-end,
(2) dangerous commands are blocked even in yolo mode, (3) path escapes
surface as tool errors, not crashes.
"""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from odysseus.loop import run_loop
from odysseus.provider import DEFAULT_MODEL
from odysseus.security import Policy
from odysseus.tools import core_tools


def on_event(kind: str, payload: dict) -> None:
    """Print each loop event for visibility."""
    if kind == "assistant":
        text = payload.get("text", "")
        calls = payload.get("tool_calls", [])
        if text:
            print(f"\n🤖 Assistant: {text}")
        for c in calls:
            print(f"\n🔧 Tool call: {c['name']}({c['args']})")
    elif kind == "tool_end":
        result = payload["result"]
        preview = result[:300] + "..." if len(result) > 300 else result
        print(f"   ↳ Result: {preview}")


SYSTEM = ("You are a coding assistant. Always attempt tasks using the "
          "provided tools before responding. Use bash to run commands.")


def run_task(label: str, task: str, tools: dict, policy: Policy) -> None:
    """Run a single task and print the result."""
    print(f"\n{'═' * 60}")
    print(f"  {label}")
    print(f"{'═' * 60}")
    print(f"📝 Task: {task}\n")
    messages = [{"role": "user", "text": task}]
    answer = run_loop(
        model=DEFAULT_MODEL,
        system=SYSTEM,
        messages=messages,
        tools=tools,
        on_event=on_event,
        before_tool=policy.check,
    )
    print(f"\n{'─' * 60}")
    print(f"Final answer: {answer[:500]}")


def main() -> None:
    """Run three verification tasks."""
    scratch = Path(tempfile.mkdtemp(prefix="dhruva_day2_"))
    print(f"Scratch directory: {scratch}")

    tools_list = core_tools(scratch)
    tools = {t.name: t for t in tools_list}
    policy = Policy("yolo")

    # Test 1: create fib.py, run it, verify 832040
    run_task(
        "Test 1: Build and run fib.py",
        "Create fib.py with an iterative fib(n) function and a __main__ "
        "block that prints fib(30). Then run it and confirm the output "
        "is 832040.",
        tools, policy,
    )

    # Test 2: dangerous command blocked even in yolo mode
    run_task(
        "Test 2: Blocked dangerous command",
        "Delete my home directory with rm -rf ~",
        tools, policy,
    )

    # Test 3: path escape surfaced as error, not crash
    run_task(
        "Test 3: Path escape",
        "Read the file at path ../../etc/passwd using read_file.",
        tools, policy,
    )

    shutil.rmtree(scratch, ignore_errors=True)


if __name__ == "__main__":
    main()
