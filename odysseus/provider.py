"""Day 1 — LLM provider adapter (Gemini REST).

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

API_ROOT = "https://generativelanguage.googleapis.com/v1beta/models"
DEFAULT_MODEL = "Fable 5"

_KEY_FILE = Path(r"C:\HarnessEnginerring\DHRUVA\CLAUDE_API_KEY.txt")

# Gemini model-id lookup — maps friendly names to API slugs.
_MODEL_IDS: dict[str, str] = {
    "Fable 5": "gemini-2.5-flash",
}


def api_key() -> str:
    """Return the API key from the key file.

    The file is expected to contain a line like ``ANTHROPIC_API_KEY = <key>``.
    Raises *RuntimeError* with an actionable message when the file is missing
    or the key line is absent.
    """
    if _KEY_FILE.exists():
        for line in _KEY_FILE.read_text().splitlines():
            if line.strip().startswith("ANTHROPIC_API_KEY"):
                _, _, value = line.partition("=")
                value = value.strip()
                if value:
                    return value
    raise RuntimeError(
        f"API key not found.  Create {_KEY_FILE} with a line "
        "'ANTHROPIC_API_KEY = <your-key>'."
    )


# ── wire translation ────────────────────────────────────────────────────────

def _to_wire(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert neutral messages to Gemini *contents* entries."""
    contents: list[dict[str, Any]] = []
    for msg in messages:
        role = msg["role"]

        if role == "user":
            contents.append({"role": "user",
                             "parts": [{"text": msg["text"]}]})

        elif role == "assistant":
            parts: list[dict[str, Any]] = []
            if msg.get("text"):
                parts.append({"text": msg["text"]})
            for tc in msg.get("tool_calls", []):
                fc: dict[str, Any] = {"functionCall": {
                    "name": tc["name"], "args": tc["args"]}}
                # Gemini 3 requires the thought signature to round-trip.
                if tc.get("signature"):
                    fc["thoughtSignature"] = tc["signature"]
                parts.append(fc)
            contents.append({"role": "model", "parts": parts})

        elif role == "tool":
            contents.append({
                "role": "user",
                "parts": [{"functionResponse": {
                    "name": msg["name"],
                    "response": {"result": msg["text"]},
                }}],
            })
    return contents


# ── response parsing ────────────────────────────────────────────────────────

def _parse_response(body: dict[str, Any]) -> dict[str, Any]:
    """Translate a Gemini response into the neutral format."""
    candidate = body["candidates"][0]["content"]
    texts: list[str] = []
    tool_calls: list[dict[str, Any]] = []

    for part in candidate.get("parts", []):
        # Skip thought parts — they are internal chain-of-thought.
        if part.get("thought"):
            continue
        if "text" in part:
            texts.append(part["text"])
        if "functionCall" in part:
            fc = part["functionCall"]
            tool_calls.append({
                "name": fc["name"],
                "args": fc.get("args", {}),
                "signature": part.get("thoughtSignature"),
            })

    usage_meta = body.get("usageMetadata", {})
    return {
        "text": "".join(texts),
        "tool_calls": tool_calls,
        "usage": {
            "input": usage_meta.get("promptTokenCount", 0),
            "output": usage_meta.get("candidatesTokenCount", 0),
        },
    }


# ── HTTP plumbing ───────────────────────────────────────────────────────────

def _post(url: str, body: dict[str, Any], retries: int = 5) -> dict[str, Any]:
    """POST JSON to *url* with exponential back-off on transient errors.

    Retries on HTTP 429 / 500 / 502 / 503 and on network-level errors
    (URLError, TimeoutError).  Other HTTP errors surface as RuntimeError
    with the status code and the first 400 characters of the response.
    """
    data = json.dumps(body).encode()
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(
                url, data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=600) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            err_body = exc.read().decode(errors="replace")[:400]
            if exc.code in (429, 500, 502, 503) and attempt < retries:
                time.sleep(2 ** attempt * 2)
                continue
            raise RuntimeError(
                f"HTTP {exc.code}: {err_body}"
            ) from exc
        except (urllib.error.URLError, TimeoutError):
            if attempt < retries:
                time.sleep(2 ** attempt * 2)
                continue
            raise


# ── public API ──────────────────────────────────────────────────────────────

def complete(
    model: str,
    system: str,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Send a chat completion request and return the neutral response dict.

    *tools* is a list of spec dicts, each containing a ``"schema"`` key whose
    value is a Gemini-compatible function declaration.
    """
    slug = _MODEL_IDS.get(model, model)
    key = api_key()
    url = f"{API_ROOT}/{slug}:generateContent?key={key}"

    payload: dict[str, Any] = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": _to_wire(messages),
        "generationConfig": {
            "temperature": 0.4,
            "maxOutputTokens": 65536,
        },
    }
    if tools:
        payload["tools"] = [{
            "functionDeclarations": [t["schema"] for t in tools],
        }]

    raw = _post(url, payload)
    return _parse_response(raw)
