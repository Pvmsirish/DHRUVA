"""Day 4 — The Harness: composition of the whole week.

Concept: every prior module is a part; the Harness is the assembled
machine.  Construction wires tools, memory, skills, security, and
sub-agents together; run() adds durable sessions and compaction around
the loop.

Design rules
 • The Harness owns composition only — no wire logic, no tool bodies.
 • Children are ephemeral (persist=False) so a child session log can
   never hijack --resume.
 • Recording is resilient: the recorded index clamps when compaction
   shrinks the message list.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable

from odysseus import context, memory, provider, session, skills
from odysseus.loop import run_loop
from odysseus.security import Policy
from odysseus.subagent import subagent_tool
from odysseus.tools import Tool, core_tools, tool


class Harness:
    """One agent over one working directory, fully wired."""

    def __init__(self, workdir: str = ".", model: str | None = None,
                 policy: Policy | None = None,
                 extra_tools: list[Tool] | None = None,
                 system_extra: str = "",
                 on_event: Callable[[str, dict], None] | None = None,
                 budget_tokens: int = 600_000, max_turns: int = 120,
                 session_path: Path | None = None,
                 enable_subagents: bool = True,
                 persist: bool = True, _depth: int = 0):
        self.workdir = Path(os.path.realpath(workdir))
        self.workdir.mkdir(parents=True, exist_ok=True)
        self.model = (model or os.environ.get("ODYSSEUS_MODEL")
                      or provider.DEFAULT_MODEL)
        self.policy = policy or Policy("yolo")
        self.user_on_event = on_event or (lambda kind, payload: None)
        self.budget_tokens = budget_tokens
        self.max_turns = max_turns
        self.session_path = session_path
        self.persist = persist
        self.messages: list[dict[str, Any]] = []
        self._recorded = 0

        self.tools = {t.name: t for t in core_tools(self.workdir)}

        @tool("Save a note to durable project memory "
              f"({memory.MEMORY_FILE}) for future sessions",
              note="The note to remember, one short sentence")
        def remember(note: str) -> str:
            """Bound to this harness's working directory."""
            return memory.remember(self.workdir, note)
        self.tools[remember.name] = remember

        if skills.catalog(self.workdir):
            @tool("Load the full instructions of a named skill",
                  name="The skill name from the catalog")
            def use_skill(name: str) -> str:
                """Bound to this harness's working directory."""
                return skills.read_skill(self.workdir, name)
            self.tools[use_skill.name] = use_skill

        if enable_subagents:
            def make_child(depth: int) -> "Harness":
                # Children are ephemeral: persist=False keeps their logs
                # out of the session dir so resume() can never pick one.
                return Harness(workdir=self.workdir, model=self.model,
                               policy=self.policy,
                               on_event=self.user_on_event,
                               budget_tokens=self.budget_tokens,
                               persist=False, _depth=depth)
            spawn = subagent_tool(make_child, depth=_depth)
            self.tools[spawn.name] = spawn

        for extra in (extra_tools or []):
            self.tools[extra.name] = extra

        prompt_extra = "\n\n".join(
            part for part in (skills.catalog_prompt(self.workdir),
                              system_extra) if part)
        self.system = memory.build_system_prompt(self.workdir, prompt_extra)

    def resume(self, path: Path | None = None) -> bool:
        """Load a prior session (the latest when *path* is None)."""
        path = path or session.latest(self.workdir)
        if path is None:
            return False
        self.messages = session.load(path)
        self.session_path = path
        self._recorded = len(self.messages)
        return bool(self.messages)

    def _record(self) -> None:
        """Persist any not-yet-recorded messages to the session file."""
        if not (self.persist and self.session_path):
            return
        # Compaction may have shrunk the list — clamp, then flush the tail.
        self._recorded = min(self._recorded, len(self.messages))
        for msg in self.messages[self._recorded:]:
            session.append(self.session_path, msg)
        self._recorded = len(self.messages)

    def run(self, task: str) -> str:
        """Run one task to completion and return the final text."""
        if self.persist and self.session_path is None:
            self.session_path = session.new_session(self.workdir, task[:32])
        self.messages.append({"role": "user", "text": task})
        self._record()

        def on_event(kind: str, payload: dict) -> None:
            self._record()
            self.user_on_event(kind, payload)

        def before_turn(msgs: list) -> list:
            out = context.compact(self.model, msgs, self.budget_tokens)
            self.messages = out  # keep our reference synced past compaction
            self._record()
            return out

        text = run_loop(self.model, self.system, self.messages, self.tools,
                        on_event, self.policy.check,
                        max_turns=self.max_turns, before_turn=before_turn)
        self._record()
        return text
