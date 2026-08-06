"""Day 4 — Sub-agents.

Concept: a sub-agent is just another harness run in a fresh context.  The
parent pays only the task and the final report; the child's transcript
never enters the parent's window.  Depth is capped so agents cannot fork
endlessly.
"""

from __future__ import annotations

from odysseus.tools import Tool, tool


def subagent_tool(make_harness, depth: int = 0, max_depth: int = 2) -> Tool:
    """Build the spawn_agent tool; *make_harness(depth)* returns a Harness."""
    @tool("Delegate a self-contained task to a fresh sub-agent with its own "
          "clean context. The sub-agent cannot see this conversation, so "
          "spell out everything it needs in the task. Returns the child's "
          "final report.",
          task="Complete, self-contained task description")
    def spawn_agent(task: str) -> str:
        """Run the task in a child harness one level deeper."""
        if depth >= max_depth:
            return "ERROR: sub-agent depth limit reached; do this task yourself"
        return make_harness(depth + 1).run(task)
    return spawn_agent
