"""Day 3 demo — a skill changes agent behavior with zero code changes.

The demo drops a brand-voice SKILL.md (pirate speak) into skills/, renders
it into the system prompt, and gives the agent a plain writing task.  The
voice of the output changes with no harness code modified.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from odysseus.loop import run_loop
from odysseus.provider import DEFAULT_MODEL
from odysseus.security import Policy
from odysseus.skills import render

SKILL = """# Brand voice

Every piece of prose you write must be in exaggerated pirate speak.
Say "Arr", "matey", and "ye"; use nautical metaphors; never break
character, whatever the topic.
"""

TASK = ("Write a three-sentence product description for a stainless "
        "steel coffee mug.")


def on_event(kind: str, payload: dict) -> None:
    """Print assistant text."""
    if kind == "assistant" and payload.get("text"):
        print(f"🤖 {payload['text']}")


def main() -> None:
    """Install the skill as data, then run a plain writing task."""
    workdir = Path(tempfile.mkdtemp(prefix="dhruva_day3skill_"))
    skill_file = workdir / "skills" / "brand-voice" / "SKILL.md"
    skill_file.parent.mkdir(parents=True)
    skill_file.write_text(SKILL, encoding="utf-8")

    system = "You are a copywriter." + render(workdir)
    print(f"📝 Task: {TASK}\n")
    answer = run_loop(DEFAULT_MODEL, system,
                      [{"role": "user", "text": TASK}],
                      {}, on_event, Policy("yolo").check)

    pirate = any(w in answer.lower() for w in ("arr", "matey", "ye "))
    print(f"\nPirate voice detected: {pirate}")


if __name__ == "__main__":
    main()
