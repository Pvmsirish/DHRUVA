"""Day 3/4 — Skills: on-demand instruction packs.

Concept: a skill is a markdown file, not code.  The system prompt carries
only a one-line catalog; the agent loads a skill's full text through the
use_skill tool when the task calls for it.  Progressive disclosure keeps
the prompt small.

Design rules
 • Skills are data — discovered on disk, never imported or executed.
 • catalog() reads only the front-matter description, never the body.
 • A read_skill() miss lists what IS available — errors should teach.
"""

from __future__ import annotations

from pathlib import Path

SKILLS_DIR = "skills"


def catalog(workdir: str | Path) -> dict[str, dict[str, str]]:
    """Map skill name → {description, path} from skills/<name>/SKILL.md."""
    root = Path(workdir) / SKILLS_DIR
    found: dict[str, dict[str, str]] = {}
    for md in sorted(root.glob("*/SKILL.md")) if root.is_dir() else []:
        desc = "(no description)"
        # Permissive front-matter scan: first "description:" line wins.
        for line in md.read_text(encoding="utf-8").splitlines():
            if line.lower().startswith("description:"):
                desc = line.split(":", 1)[1].strip()
                break
        found[md.parent.name] = {"description": desc, "path": str(md)}
    return found


def catalog_prompt(workdir: str | Path) -> str:
    """One catalog line per skill for the system prompt; empty when none."""
    cat = catalog(workdir)
    if not cat:
        return ""
    return ("Skills available (load one with the use_skill tool when "
            "relevant):\n"
            + "\n".join(f"- {name}: {info['description']}"
                        for name, info in cat.items()))


def read_skill(workdir: str | Path, name: str) -> str:
    """Return a skill's full SKILL.md text, or a corrective error."""
    cat = catalog(workdir)
    if name not in cat:
        return (f"ERROR: no skill named {name}. "
                f"Available: {', '.join(cat) or '(none)'}")
    return Path(cat[name]["path"]).read_text(encoding="utf-8")
