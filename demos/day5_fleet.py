"""Day 5 demo — prove the harness by shipping three real products.

run_fleet builds artisan-coffee, taskman, and viper in parallel, one fresh
directory each, in two phases per project: the build, then a
design-director review pass resumed into the SAME session.  Mechanical
verification follows — file existence, green tests, greps, word counts —
and a results table closes the week.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from odysseus import Harness, run_fleet

ROOT = Path(__file__).resolve().parent.parent / "projects"

# The quality bar, verbatim, installed as a skill in every project workdir.
SKILL = """---
description: Design-engineering quality bar for any web page or UI work
---

# Design Engineering

Hold every page you ship to this bar:

- a real design system as CSS custom properties
- at least 9 distinct sections for a landing page
- at least 1,200 words of real copy, no lorem ipsum
- at least 4 hand-drawn inline SVG illustrations, one being a product
  artifact in the hero
- at least 3 working interactive behaviors
- responsive at 360, 768, and 1280
- semantic HTML with focus states
- a self-review pass before finishing that counts sections, words, SVGs,
  and interactions against these minimums and fixes any shortfall
"""

BUILDS = {
    "artisan-coffee":
        "Load the design-engineering skill and meet its full quality bar. "
        "Build a self-contained index.html for a specialty coffee roaster "
        "in Goa — sticky nav, hero with a drawn product artifact, six "
        "origin cards with prices, a three-tier subscription table with a "
        "working monthly/annual toggle, brew-guide tabs, an FAQ accordion, "
        "a dark-mode toggle persisted to localStorage.",
    "taskman":
        "Build taskman, a python CLI task manager: argparse subcommands "
        "add, list, done, rm, stats; JSON persistence; aligned table "
        "output; a unittest suite of 10+ cases run via subprocess against "
        "a temp store; run the suite yourself and make all tests green.",
    "viper":
        "Load the design-engineering skill where it applies. Build a "
        "canvas snake game in one index.html — grid movement on "
        "requestAnimationFrame, food, speed-up every 5 foods, score, "
        "pause, restart, high score in localStorage.",
}

REVIEW = ("Review every file you produced against the skill bar as a "
          "demanding design director; list 12 concrete deficiencies; fix "
          "them all; verify again.")


def make_event(name: str):
    """A compact per-project event printer for parallel output."""
    def on_event(kind: str, payload: dict) -> None:
        if kind == "tool_start":
            print(f"[{name}] * {payload['name']}", flush=True)
    return on_event


def build_harness(workdir: str) -> Harness:
    """Fresh harness for the build phase."""
    return Harness(workdir, on_event=make_event(Path(workdir).name))


def review_harness(workdir: str) -> Harness:
    """Harness resumed into the build session for the review phase."""
    h = build_harness(workdir)
    h.resume()
    return h


def visible_words(html: str) -> int:
    """Count words in the rendered text of an HTML document."""
    html = re.sub(r"<(script|style)[\s\S]*?</\1>", " ", html, flags=re.I)
    return len(re.sub(r"<[^>]+>", " ", html).split())


def turns(workdir: Path) -> int:
    """Count assistant turns recorded in the project's session log."""
    total = 0
    for f in (workdir / ".odysseus" / "sessions").glob("*.jsonl"):
        total += sum(1 for line in f.read_text(encoding="utf-8").splitlines()
                     if '"role": "assistant"' in line)
    return total


def verify(name: str) -> tuple[bool, str]:
    """Mechanical checks per project; returns (pass, one-line summary)."""
    wd = ROOT / name
    if name == "artisan-coffee":
        f = wd / "index.html"
        if not f.exists():
            return False, "index.html missing"
        html = f.read_text(encoding="utf-8", errors="replace")
        words = visible_words(html)
        ok = ("localStorage" in html and words > 1200
              and re.search(r"accordion|<details", html, re.I) is not None)
        return ok, (f"{words} visible words, localStorage "
                    f"{'localStorage' in html}, accordion present")
    if name == "taskman":
        tests = sorted(wd.glob("test*.py"))
        if not tests:
            return False, "no test file"
        proc = subprocess.run([sys.executable, tests[0].name], cwd=wd,
                              capture_output=True, text=True, timeout=120)
        out = (proc.stdout + proc.stderr).strip().splitlines()
        return proc.returncode == 0, (out[-1] if out else "no output")
    if name == "viper":
        f = wd / "index.html"
        if not f.exists():
            return False, "index.html missing"
        html = f.read_text(encoding="utf-8", errors="replace")
        ok = "requestAnimationFrame" in html and "localStorage" in html
        return ok, "requestAnimationFrame + localStorage present"
    return False, "unknown project"


def main() -> None:
    """Install skills, run both fleet phases, verify, print the table."""
    for name in BUILDS:
        skill = ROOT / name / "skills" / "design-engineering" / "SKILL.md"
        skill.parent.mkdir(parents=True, exist_ok=True)
        skill.write_text(SKILL, encoding="utf-8")

    jobs = [{"name": n, "workdir": str(ROOT / n), "task": t}
            for n, t in BUILDS.items()]
    print("=== Phase 1: build ===", flush=True)
    for r in run_fleet(jobs, build_harness, max_workers=3):
        print(f"[{r['name']}] ok={r['ok']}: {r['report'][:150]}", flush=True)

    print("\n=== Phase 2: design-director review, same session ===",
          flush=True)
    jobs = [{**j, "task": REVIEW} for j in jobs]
    for r in run_fleet(jobs, review_harness, max_workers=3):
        print(f"[{r['name']}] ok={r['ok']}: {r['report'][:150]}", flush=True)

    print("\n=== Mechanical verification ===")
    print(f"{'project':<16} {'result':<6} {'turns':>5}  contents")
    for name in BUILDS:
        ok, note = verify(name)
        print(f"{name:<16} {'PASS' if ok else 'FAIL':<6} "
              f"{turns(ROOT / name):>5}  {note}")


if __name__ == "__main__":
    main()
