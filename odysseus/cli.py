"""Day 5 — CLI: the front door.

Concept: the CLI is a thin shell over Harness.  Headless mode (-p) is for
scripts and CI; interactive mode is a REPL with human-in-the-loop approval.
Nothing here knows about providers, wire formats, or tools — only Harness.

Design rules
 • Headless defaults to yolo (no human present); interactive defaults to
   safe, where writes ask the approver.
 • Ctrl-C never loses work: the session log is already on disk, and
   --resume continues it.
"""

from __future__ import annotations

import argparse
import sys

from odysseus.harness import Harness
from odysseus.security import Policy

DIM, RESET = "\033[2m", "\033[0m"


def print_event(kind: str, payload: dict) -> None:
    """Render loop events: text plainly, calls one-line, results dimmed."""
    if kind == "assistant" and payload.get("text"):
        print(payload["text"])
    elif kind == "tool_start":
        print(f"* {payload['name']}({str(payload['args'])[:100]})")
    elif kind == "tool_end":
        first = ((payload["result"] or "").splitlines() or [""])[0]
        print(f"  {DIM}{first[:120]}{RESET}")


def approve(call: dict, reason: str) -> bool:
    """Show the pending call and ask the human for a y/N decision."""
    print(f"! {reason}\n  {call['name']}({str(call['args'])[:200]})")
    return input(f"approve {call['name']}? [y/N] ").strip().lower() == "y"


def main(argv: list[str] | None = None) -> int:
    """Parse arguments, then run headless or drop into the REPL."""
    ap = argparse.ArgumentParser(prog="odysseus",
                                 description="A minimal agent harness.")
    ap.add_argument("-p", "--prompt", help="run one task headless and exit")
    ap.add_argument("-d", "--workdir", default=".", help="jail directory")
    ap.add_argument("-m", "--model", default=None)
    ap.add_argument("--mode", choices=["safe", "yolo", "read-only"])
    ap.add_argument("--resume", action="store_true",
                    help="continue the latest session in this workdir")
    ap.add_argument("--max-turns", type=int, default=120)
    args = ap.parse_args(argv)

    # No human is present in headless mode, so it defaults to yolo.
    mode = args.mode or ("yolo" if args.prompt else "safe")
    harness = Harness(args.workdir, model=args.model,
                      policy=Policy(mode, approver=approve),
                      on_event=print_event, max_turns=args.max_turns)
    if args.resume:
        harness.resume()

    if args.prompt:
        harness.run(args.prompt)
        return 0

    print(f"Odysseus — model {harness.model} | mode {mode} | "
          f"jail {harness.workdir}")
    print("Ctrl-D exits. Ctrl-C interrupts a run; the session log is safe "
          "and --resume continues it.")
    while True:
        try:
            task = input("\n> ").strip()
        except EOFError:
            print()
            return 0
        except KeyboardInterrupt:
            print()
            continue
        if not task:
            continue
        try:
            harness.run(task)
        except KeyboardInterrupt:
            print(f"\nInterrupted — session log is safe at "
                  f"{harness.session_path}; restart with --resume to "
                  "continue.")
