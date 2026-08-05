"""Day 3 demo — compaction under a tight token budget.

A deliberately chatty task (five writes, five read-backs, a manifest) is run
with budget_tokens=1500 wired through before_turn, so compaction must fire
mid-run.  The demo prints a marker each time it does, then verifies the
files on disk afterward.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from odysseus.context import compact, estimate_tokens
from odysseus.loop import run_loop
from odysseus.provider import DEFAULT_MODEL
from odysseus.security import Policy
from odysseus.tools import core_tools

BUDGET = 1500

TASK = ("Create five files one.txt through five.txt, each with 20 lines of "
        "the word ping, one write_file at a time with a read back after "
        "each; then MANIFEST.md listing each file and its line count "
        "verified with wc -l")


def on_event(kind: str, payload: dict) -> None:
    """Print each loop event compactly."""
    if kind == "assistant":
        if payload.get("text"):
            print(f"\n🤖 {payload['text'][:200]}")
        for c in payload.get("tool_calls", []):
            print(f"🔧 {c['name']}({str(c['args'])[:80]})")
    elif kind == "tool_end":
        print(f"   ↳ {payload['result'][:100]}")


def main() -> None:
    """Run the manifest task under a 1500-token budget."""
    scratch = Path(tempfile.mkdtemp(prefix="dhruva_day3_"))
    print(f"Scratch: {scratch}\n📝 Task: {TASK}")

    tools = {t.name: t for t in core_tools(scratch)}
    compactions: list[int] = []

    def before_turn(msgs: list) -> list:
        out = compact(DEFAULT_MODEL, msgs, BUDGET)
        if out is not msgs:  # compact() returns the same list when idle
            compactions.append(len(msgs))
            print(f"\n♻️  COMPACTION #{len(compactions)}: {len(msgs)} msgs "
                  f"→ {len(out)} msgs (~{estimate_tokens(out)} tokens)")
        return out

    answer = run_loop(DEFAULT_MODEL,
                      "You are a careful coding assistant. Use the tools.",
                      [{"role": "user", "text": TASK}], tools,
                      on_event, Policy("yolo").check,
                      before_turn=before_turn)

    print(f"\n{'═' * 60}\nFinal answer: {answer[:400]}")
    print(f"\nCompactions fired: {len(compactions)}")

    # Independent verification of the artifacts on disk.
    for name in ["one.txt", "two.txt", "three.txt", "four.txt", "five.txt"]:
        p = scratch / name
        n = len(p.read_text().splitlines()) if p.exists() else "MISSING"
        print(f"  {name}: {n} lines")
    print(f"  MANIFEST.md exists: {(scratch / 'MANIFEST.md').exists()}")


if __name__ == "__main__":
    main()
