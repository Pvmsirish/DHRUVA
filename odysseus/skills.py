"""Day 3 — Skills.

Concept: a skill is a markdown file, not code.  Dropping a SKILL.md into
skills/<name>/ under the working directory changes agent behavior with zero
code changes — the harness folds every skill into the system prompt at
session start.

Design rules
 • Skills are data — discovered on disk, never imported or executed.
 • One folder per skill; the folder name is the skill name.
 • render() produces a single block the caller appends to the system prompt.
"""

from __future__ import annotations

from pathlib import Path

SKILLS_DIR = "skills"


def discover(workdir: str | Path) -> list[tuple[str, str]]:
    """Return (name, text) for every skills/<name>/SKILL.md under *workdir*.

    Sorted by folder name so the system prompt is deterministic.
    """
    root = Path(workdir) / SKILLS_DIR
    if not root.is_dir():
        return []
    return [(md.parent.name, md.read_text(encoding="utf-8"))
            for md in sorted(root.glob("*/SKILL.md"))]


def render(workdir: str | Path) -> str:
    """Render all discovered skills as one system-prompt block.

    Returns an empty string when no skills exist, so callers can append
    unconditionally.
    """
    skills = discover(workdir)
    if not skills:
        return ""
    blocks = [f"## Skill: {name}\n{text.strip()}" for name, text in skills]
    return ("\n\nYou have the following skills. Follow their instructions "
            "in everything you produce.\n\n" + "\n\n".join(blocks))
