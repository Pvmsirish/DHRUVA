"""Day 1 — Agent loop (think → act → observe).

Concept: the loop is the heartbeat of every agent.  It calls the model, runs
any requested tools, feeds results back, and repeats until the model answers
in plain text or the turn budget expires.

Design rules
 • Tools never crash the loop — every exception becomes an ERROR result.
 • *before_tool* is a policy hook: return None to allow, or a reason string
   to block.  Security rules plug in here on day 2.
 • *before_turn* is a context hook: day 3 plugs compaction in here.
 • *on_event* is the sole observation channel — UIs and loggers attach here.
"""

from __future__ import annotations

from typing import Any, Callable

from odysseus import provider


def run_loop(
    model: str,
    system: str,
    messages: list[dict[str, Any]],
    tools: dict[str, Any],
    on_event: Callable[[str, dict[str, Any]], None],
    before_tool: Callable[[dict[str, Any]], str | None],
    max_turns: int = 80,
    before_turn: Callable[[list[dict[str, Any]]], list[dict[str, Any]]] | None = None,
) -> str:
    """Drive the think → act → observe loop and return the final text.

    *tools* maps names to objects exposing *.spec* (a ``{"schema": …}`` dict)
    and *.run(**kwargs)*.  The loop hands ``[t.spec for t in tools.values()]``
    to the provider.
    """
    specs = [t.spec for t in tools.values()]

    for _ in range(max_turns):
        if before_turn is not None:
            messages = before_turn(messages)

        reply = provider.complete(model, system, messages, specs)

        assistant_msg: dict[str, Any] = {
            "role": "assistant",
            "text": reply["text"],
            "tool_calls": reply["tool_calls"],
        }
        messages.append(assistant_msg)
        on_event("assistant", {**reply, "message": assistant_msg})

        if not reply["tool_calls"]:
            return reply["text"]

        for call in reply["tool_calls"]:
            on_event("tool_start", call)
            reason = before_tool(call)
            if reason is not None:
                result = f"BLOCKED: {reason}"
            elif call["name"] not in tools:
                result = f"ERROR: unknown tool {call['name']}"
            else:
                try:
                    result = str(tools[call["name"]].run(**call["args"]))
                except Exception as exc:
                    result = f"ERROR: {type(exc).__name__}: {exc}"
            # call_id round-trips the provider's tool-call id.
            messages.append({"role": "tool", "name": call["name"],
                             "text": result,
                             "call_id": call.get("signature")})
            on_event("tool_end", {"name": call["name"], "result": result})

    # Turn budget exhausted — ask the model to wrap up without tools.
    messages.append({"role": "user", "text": "Turn limit reached; wrap up now."})
    if before_turn is not None:
        messages = before_turn(messages)
    reply = provider.complete(model, system, messages, tools=[])
    final: dict[str, Any] = {
        "role": "assistant", "text": reply["text"], "tool_calls": [],
    }
    messages.append(final)
    on_event("assistant", {**reply, "message": final})
    return reply["text"]
