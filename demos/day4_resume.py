"""Day 4 demo — durable sessions survive a hard kill.

Three modes in one file:
  driver (default)  spawn phase "start", hard-kill it partway, then resume
  start <dir>       run the task; stall at the 3rd tool-calling turn so the
                    driver can kill us mid-tool — a deterministic "crash"
  (resume runs in-process in the driver)

The resumed transcript must show the synthesized interruption notice, and
all six files must exist at the end.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from odysseus import Harness

TASK = ("Create part1.txt through part5.txt one at a time, then "
        "SUMMARY.md describing each")
PYTHON = sys.executable


def phase_start(workdir: str) -> None:
    """Run the task, stalling on the 3rd tool-calling turn until killed."""
    seen = [0]

    def on_event(kind: str, payload: dict) -> None:
        if kind == "assistant" and payload.get("tool_calls"):
            seen[0] += 1
            print(f"turn {seen[0]}: {[c['name'] for c in payload['tool_calls']]}",
                  flush=True)
            if seen[0] == 3:
                # The assistant message is already recorded; its tool has
                # not run.  Stall so the driver's kill lands right here.
                print("### PAUSE", flush=True)
                time.sleep(120)

    Harness(workdir, on_event=on_event).run(TASK)


def driver() -> None:
    """Orchestrate: start, kill -9, resume, verify."""
    workdir = tempfile.mkdtemp(prefix="dhruva_day4res_")
    print(f"Workdir: {workdir}\n📝 Task: {TASK}\n")

    print("─── Phase 1: run until the 3rd tool turn, then hard-kill ───")
    proc = subprocess.Popen([PYTHON, __file__, "start", workdir],
                            stdout=subprocess.PIPE, text=True, bufsize=1)
    for line in proc.stdout:
        print(f"  child: {line.rstrip()}")
        if line.startswith("### PAUSE"):
            proc.kill()  # SIGKILL equivalent — no cleanup, no flush
            print("  💀 killed mid-tool")
            break
    proc.wait()

    print("\n─── Phase 2: fresh process, resume(), continue ───")
    h = Harness(workdir)
    assert h.resume(), "resume() found no session"
    notice = any(m["role"] == "tool" and "Interrupted" in (m.get("text") or "")
                 for m in h.messages)
    print(f"Interruption notice in transcript: {notice}")
    answer = h.run("continue the task")
    print(f"\nFinal answer: {answer[:300]}")

    files = ["part1.txt", "part2.txt", "part3.txt", "part4.txt",
             "part5.txt", "SUMMARY.md"]
    status = {f: (Path(workdir) / f).exists() for f in files}
    print(f"\nAll six files exist: {all(status.values())}  {status}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "start":
        phase_start(sys.argv[2])
    else:
        driver()
