"""Day 4 demo — sub-agents with ephemeral sessions.

The parent delegates two file-writing tasks to children via spawn_agent,
then runs the tests itself.  Children run with persist=False, so afterward
.odysseus/sessions must contain exactly ONE file — the parent's.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from odysseus import Harness

TASK = ("Use spawn_agent twice: delegate writing utils.py with a "
        "slugify(text) function to one child, and test_utils.py with five "
        "asserts to another; then run python3 test_utils.py yourself and "
        "report")


def main() -> None:
    """Run the delegation task and verify the session-file invariant."""
    workdir = Path(tempfile.mkdtemp(prefix="dhruva_day4sub_"))
    print(f"Workdir: {workdir}\n📝 Task: {TASK}\n")

    def on_event(kind: str, payload: dict) -> None:
        if kind == "assistant" and payload.get("text"):
            print(f"🤖 {payload['text'][:250]}")
        elif kind == "tool_start":
            print(f"🔧 {payload['name']}({str(payload['args'])[:90]})")
        elif kind == "tool_end":
            print(f"   ↳ {payload['result'][:150]}")

    answer = Harness(workdir, on_event=on_event).run(TASK)
    print(f"\nFinal answer: {answer[:400]}")

    # The parent's session file is authoritative: child messages are never
    # recorded there, so a bash test_utils call in it belongs to the parent.
    sessions = list((workdir / ".odysseus" / "sessions").glob("*.jsonl"))
    log = sessions[0].read_text(encoding="utf-8") if sessions else ""
    ran_tests = '"bash"' in log and "test_utils" in log
    print(f"\nutils.py exists:      {(workdir / 'utils.py').exists()}")
    print(f"test_utils.py exists: {(workdir / 'test_utils.py').exists()}")
    print(f"tests run via bash:   {ran_tests}")
    print(f"session files:        {len(sessions)} (must be exactly 1)")


if __name__ == "__main__":
    main()
