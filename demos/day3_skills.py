"""Day 3 demo — a skill changes agent behavior with zero code changes.

The demo drops a brand-voice SKILL.md (pirate speak) into skills/.  The
system prompt carries only the one-line catalog; the agent must load the
full skill through use_skill, then write in the demanded voice.  No harness
code changes.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from odysseus.loop import run_loop
from odysseus.memory import build_system_prompt
from odysseus.provider import DEFAULT_MODEL
from odysseus.security import Policy
from odysseus.skills import catalog_prompt, read_skill
from odysseus.tools import tool

SKILL = """---
description: Mandatory brand voice for every piece of written output
---

# Brand voice

Every piece of prose you write must be in exaggerated pirate speak.
Say "Arr", "matey", and "ye"; use nautical metaphors; never break
character, whatever the topic.
"""

TASK = ("Write a three-sentence product description for a stainless "
        "steel coffee mug.")


def on_event(kind: str, payload: dict) -> None:
    """Print assistant text and skill loads."""
    if kind == "assistant" and payload.get("text"):
        print(f"🤖 {payload['text']}")
    elif kind == "tool_start":
        print(f"🔧 {payload['name']}({payload['args']})")


def main() -> None:
    """Install the skill as data, then run a plain writing task."""
    workdir = Path(tempfile.mkdtemp(prefix="dhruva_day3skill_"))
    skill_file = workdir / "skills" / "brand-voice" / "SKILL.md"
    skill_file.parent.mkdir(parents=True)
    skill_file.write_text(SKILL, encoding="utf-8")

    @tool("Load the full instructions of a named skill",
          name="The skill name from the catalog")
    def use_skill(name: str) -> str:
        """Demo closure over read_skill() bound to this working directory."""
        return read_skill(workdir, name)

    system = build_system_prompt(workdir, extra=catalog_prompt(workdir))
    print(f"📝 Task: {TASK}\n")
    answer = run_loop(DEFAULT_MODEL, system,
                      [{"role": "user", "text": TASK}],
                      {use_skill.name: use_skill}, on_event,
                      Policy("yolo").check)

    pirate = any(w in answer.lower() for w in ("arr", "matey", "ye "))
    print(f"\nPirate voice detected: {pirate}")


if __name__ == "__main__":
    main()
