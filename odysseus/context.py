"""Day 3 — Context engine (compaction).

Concept: the context window is finite.  When a transcript outgrows its token
budget, the old majority is compressed into one dense summary message and
only the recent tail is kept verbatim.  This plugs into run_loop's
before_turn socket.

Design rules
 • Token estimation is deliberately crude (chars / 4) — budgets are soft.
 • The summary must preserve task, files touched, decisions, open errors.
 • The kept tail never begins with an orphaned tool result.
"""

from __future__ import annotations

from typing import Any

from odysseus import provider

CHARS_PER_TOKEN = 4
KEEP_RECENT = 6

_SYSTEM = ("You compress agent transcripts. Preserve: the original task, "
           "every file created or edited and its purpose, key decisions, "
           "unresolved errors, and what remains to be done. Be dense and "
           "factual.")


def estimate_tokens(messages: list[dict[str, Any]]) -> int:
    """Crude token estimate: total stringified length over CHARS_PER_TOKEN."""
    return sum(len(str(m)) for m in messages) // CHARS_PER_TOKEN


def _render(msg: dict[str, Any]) -> str:
    """Render one message as a plain transcript line, clipped per message."""
    text = (msg.get("text") or "")[:1000]
    if msg["role"] == "tool":
        return f"tool[{msg.get('name')}]: {text}"
    line = f"{msg['role']}: {text}"
    if calls := msg.get("tool_calls"):
        line += "  [called: " + ", ".join(c["name"] for c in calls) + "]"
    return line


def compact(model: str, messages: list[dict[str, Any]],
            budget_tokens: int) -> list[dict[str, Any]]:
    """Return *messages* unchanged while within budget, else compacted.

    Compaction keeps the last KEEP_RECENT messages verbatim and replaces
    everything older with a single summary user message.
    """
    if (estimate_tokens(messages) <= budget_tokens
            or len(messages) <= KEEP_RECENT + 1):
        return messages
    old, recent = messages[:-KEEP_RECENT], messages[-KEEP_RECENT:]
    # A tool result at the head of the tail would be orphaned from its
    # call — fold such messages into the summarized portion instead.
    while recent and recent[0]["role"] == "tool":
        old.append(recent.pop(0))
    transcript = "\n".join(_render(m) for m in old)
    summary = provider.complete(
        model, _SYSTEM, [{"role": "user", "text": transcript}])["text"]
    return ([{"role": "user",
              "text": f"[Conversation so far, compacted]\n{summary}"}]
            + recent)
