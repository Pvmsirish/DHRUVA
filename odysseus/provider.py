"""Day 1 — LLM provider adapter (Anthropic Messages API).

Concept: isolate every vendor-specific detail behind one function, *complete()*,
so the rest of the harness speaks only the neutral message format.

Design rules
 • One module owns the wire protocol; nothing else imports urllib here.
 • The neutral format (user / assistant / tool dicts) is the harness lingua
   franca — _to_wire translates out, response parsing translates back.
 • Retries live next to the HTTP call, nowhere else.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

# ── constants ────────────────────────────────────────────────────────────────

API_ROOT = "https://api.anthropic.com/v1/messages"
DEFAULT_MODEL = "Fable 5"

_KEY_FILE = Path(r"C:\HarnessEnginerring\DHRUVA\CLAUDE_API_KEY.txt")

# Friendly name → Anthropic model-id.
_MODEL_IDS: dict[str, str] = {"Fable 5": "claude-fable-5"}


def api_key() -> str:
    """Return the API key from the key file or ANTHROPIC_API_KEY env var.

    Raises *RuntimeError* with an actionable message when neither is set.
    """
    if key := os.environ.get("ANTHROPIC_API_KEY"):
        return key
    if _KEY_FILE.exists():
        for line in _KEY_FILE.read_text().splitlines():
            if line.strip().startswith("ANTHROPIC_API_KEY"):
                _, _, value = line.partition("=")
                if (value := value.strip()):
                    return value
    raise RuntimeError(
        f"Set ANTHROPIC_API_KEY env var or create {_KEY_FILE} with "
        "'ANTHROPIC_API_KEY = <your-key>'."
    )


# ── wire translation ────────────────────────────────────────────────────────

def _to_wire(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert neutral messages to Anthropic *messages* entries.

    Anthropic requires strict user/assistant alternation, so consecutive
    same-role entries are merged via *_merge*.
    """
    wire: list[dict[str, Any]] = []
    for msg in messages:
        role = msg["role"]
        if role == "user":
            _merge(wire, "user", [{"type": "text", "text": msg["text"]}])
        elif role == "assistant":
            # The stored signature is the Anthropic tool_use id — it must
            # round-trip verbatim so results can be matched to calls.
            parts: list[dict[str, Any]] = []
            if msg.get("text"):
                parts.append({"type": "text", "text": msg["text"]})
            parts += [{"type": "tool_use", "id": tc.get("signature", ""),
                       "name": tc["name"], "input": tc["args"]}
                      for tc in msg.get("tool_calls", [])]
            _merge(wire, "assistant", parts)
        elif role == "tool":
            # Tool results ride in a user message; tool_use_id round-trips
            # the id so Anthropic can match results to calls.
            _merge(wire, "user", [{"type": "tool_result",
                                    "tool_use_id": msg.get("call_id", ""),
                                    "content": msg["text"]}])
    return wire


def _merge(wire: list, role: str, content: list) -> None:
    """Append content to the last message if roles match, else start a new one."""
    if wire and wire[-1]["role"] == role:
        wire[-1]["content"].extend(content)
    else:
        wire.append({"role": role, "content": content})


# ── response parsing ────────────────────────────────────────────────────────

def _parse_response(body: dict[str, Any]) -> dict[str, Any]:
    """Translate an Anthropic response into the neutral format."""
    texts: list[str] = []
    tool_calls: list[dict[str, Any]] = []
    for block in body.get("content", []):
        if block["type"] == "text":
            texts.append(block["text"])
        elif block["type"] == "tool_use":
            tool_calls.append({"name": block["name"], "args": block["input"],
                                "signature": block["id"]})
    # Policy refusals arrive with empty content and stop_reason "refusal" —
    # surface them as text so the loop never returns silently empty.
    if not texts and not tool_calls and body.get("stop_reason") == "refusal":
        detail = body.get("stop_details", {}).get("explanation",
                                                   "no reason given")
        texts.append(f"[Request refused by the provider: {detail}]")
    usage = body.get("usage", {})
    return {"text": "".join(texts), "tool_calls": tool_calls,
            "usage": {"input": usage.get("input_tokens", 0),
                       "output": usage.get("output_tokens", 0)}}


# ── HTTP plumbing ───────────────────────────────────────────────────────────

def _post(url: str, body: dict[str, Any], headers: dict[str, str],
          retries: int = 5) -> dict[str, Any]:
    """POST JSON with exponential back-off on transient errors.

    Retries on HTTP 429/500/502/503 and on network-level URLError/TimeoutError.
    Other HTTP errors surface as RuntimeError with the status and first 400
    characters of the error body.
    """
    data = json.dumps(body).encode()
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, data=data, headers=headers,
                                         method="POST")
            with urllib.request.urlopen(req, timeout=600) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            err_body = exc.read().decode(errors="replace")[:400]
            if exc.code in (429, 500, 502, 503) and attempt < retries:
                time.sleep(2 ** attempt * 2)
                continue
            raise RuntimeError(f"HTTP {exc.code}: {err_body}") from exc
        except (urllib.error.URLError, TimeoutError):
            if attempt < retries:
                time.sleep(2 ** attempt * 2)
                continue
            raise


# ── public API ──────────────────────────────────────────────────────────────

def complete(model: str, system: str, messages: list[dict[str, Any]],
             tools: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Send a chat completion and return the neutral response dict.

    *tools* is a list of spec dicts, each with a ``"schema"`` key whose value
    contains ``name``, ``description``, and ``parameters``.
    """
    slug = _MODEL_IDS.get(model, model)
    hdrs = {"Content-Type": "application/json", "x-api-key": api_key(),
            "anthropic-version": "2023-06-01"}
    payload: dict[str, Any] = {
        "model": slug, "max_tokens": 65536,
        "system": system, "messages": _to_wire(messages),
    }
    # Thinking models (Fable 5) reject explicit temperature.
    if slug not in ("claude-fable-5",):
        payload["temperature"] = 0.4
    if tools:
        specs = [t["schema"] for t in tools]
        payload["tools"] = [
            {"name": s["name"], "description": s.get("description", ""),
             "input_schema": s.get("parameters", {})}
            for s in specs
        ]
    return _parse_response(_post(API_ROOT, payload, hdrs))
