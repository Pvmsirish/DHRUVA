"""Day 2 — Tool framework and core tools.

Concept: tools are the agent's hands.  A minimal Tool dataclass wraps a name,
a provider-ready spec, and a callable.  The @tool decorator builds specs from
function signatures.  core_tools() provides a sandboxed file-system and shell
toolkit.

Design rules
 • Every tool parameter is string-typed on the wire — tools parse internally.
 • Path tools share one resolve() that enforces the sandbox boundary.
 • edit_file requires the old snippet to appear exactly once (the uniqueness
   rule) so edits never silently land at the wrong call-site.
"""

from __future__ import annotations

import fnmatch
import inspect
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


@dataclass
class Tool:
    """A tool the agent can invoke: name, provider spec, and callable."""

    name: str
    spec: dict[str, Any]
    run: Callable[..., str]


def tool(description: str, **params: str):
    """Decorator that turns a plain function into a Tool.

    All parameters are declared as string-typed on the wire.  Parameters with
    defaults in the function signature become optional in the spec.
    """
    def decorator(fn: Callable) -> Tool:
        sig = inspect.signature(fn)
        properties: dict[str, Any] = {}
        required: list[str] = []
        for pname, param in sig.parameters.items():
            properties[pname] = {
                "type": "string",
                "description": params.get(pname, pname),
            }
            if param.default is inspect.Parameter.empty:
                required.append(pname)
        spec = {"schema": {
            "name": fn.__name__,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        }}
        return Tool(name=fn.__name__, spec=spec, run=fn)
    return decorator


_IGNORE = {".git", "node_modules", "__pycache__", ".venv"}


def core_tools(workdir: str | Path) -> list[Tool]:
    """Return the six core tools, sandboxed to *workdir*."""
    root = Path(workdir).resolve()

    def resolve(path: str) -> Path:
        """Resolve *path* against the sandbox root, rejecting escapes."""
        resolved = (root / path).resolve()
        if not resolved.is_relative_to(root):
            raise PermissionError(f"{path!r} escapes the working directory")
        return resolved

    # ── file tools ───────────────────────────────────────────────────────

    @tool("Read file contents with line numbers", path="File path to read")
    def read_file(path: str) -> str:
        """Return numbered lines; truncate past 4 000 lines."""
        p = resolve(path)
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        total = len(lines)
        if total > 4000:
            lines = lines[:4000]
            lines.append(f"... truncated ({total} total lines)")
        return "\n".join(f"{i + 1}\t{ln}" for i, ln in enumerate(lines))

    @tool("Write content to a file, creating parent directories",
          path="File path", content="File content to write")
    def write_file(path: str, content: str) -> str:
        """Create or overwrite a file."""
        p = resolve(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"Wrote {len(content)} chars to {path}"

    # The uniqueness rule: the old snippet must appear exactly once so an
    # edit never silently lands at the wrong call-site.
    @tool("Replace a unique snippet in a file",
          path="File path", old="Exact existing text", new="Replacement text")
    def edit_file(path: str, old: str, new: str) -> str:
        """Replace *old* with *new* exactly once."""
        p = resolve(path)
        text = p.read_text(encoding="utf-8")
        count = text.count(old)
        if count == 0:
            return ("ERROR: snippet not found — read the file and "
                    "copy it exactly")
        if count > 1:
            return (f"ERROR: snippet appears {count} times — include "
                    "more context to make it unique")
        p.write_text(text.replace(old, new, 1), encoding="utf-8")
        return f"Edited {path}"

    # ── shell tool ───────────────────────────────────────────────────────

    @tool("Run a shell command",
          command="Shell command to run", timeout="Timeout in seconds")
    def bash(command: str, timeout: str = "120") -> str:
        """Execute *command* in a subprocess, capturing output."""
        t = int(timeout)
        try:
            proc = subprocess.run(
                command, shell=True, cwd=root,
                capture_output=True, text=True, timeout=t,
            )
        except subprocess.TimeoutExpired:
            return f"ERROR: timed out after {t}s"
        out = (proc.stdout or "") + (proc.stderr or "")
        if not out.strip():
            return f"(exit {proc.returncode}, no output)"
        # Past 12 000 chars, keep the first and last 6 000.
        if len(out) > 12000:
            out = out[:6000] + "\n\n... truncated ...\n\n" + out[-6000:]
        return out

    # ── search tools ─────────────────────────────────────────────────────

    def _walk() -> list[tuple[str, str]]:
        """Walk the tree yielding (relative_path, basename) pairs."""
        entries: list[tuple[str, str]] = []
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in _IGNORE]
            for fname in filenames:
                full = Path(dirpath) / fname
                rel = str(full.relative_to(root)).replace("\\", "/")
                entries.append((rel, fname))
        return entries

    @tool("List files matching a glob pattern",
          pattern="Glob pattern (default **/*)")
    def list_files(pattern: str = "**/*") -> str:
        """Return sorted file list, capped at 500 entries."""
        matches = sorted(
            rel for rel, base in _walk()
            if fnmatch.fnmatch(rel, pattern) or fnmatch.fnmatch(base, pattern)
        )
        if len(matches) > 500:
            rest = len(matches) - 500
            matches = matches[:500]
            matches.append(f"... and {rest} more")
        return "\n".join(matches)

    @tool("Search file contents with a regex",
          regex="Regular expression", pattern="File glob filter")
    def grep(regex: str, pattern: str = "*") -> str:
        """Return matching lines as path:lineno: text, capped at 200 hits."""
        compiled = re.compile(regex)
        hits: list[str] = []
        for rel, base in _walk():
            if not (fnmatch.fnmatch(rel, pattern)
                    or fnmatch.fnmatch(base, pattern)):
                continue
            try:
                text = (root / rel).read_text(encoding="utf-8",
                                              errors="replace")
            except OSError:
                continue
            for lineno, line in enumerate(text.splitlines(), 1):
                if compiled.search(line):
                    hits.append(f"{rel}:{lineno}: {line[:200]}")
                    if len(hits) >= 200:
                        return "\n".join(hits)
        return "\n".join(hits) if hits else "No matches."

    return [read_file, write_file, edit_file, bash, list_files, grep]
