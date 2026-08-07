"""Day 5 — Fleet: parallel harnesses.

Concept: scaling out is just running more harnesses.  Each job gets its own
harness over its own directory; threads are enough because the work is
API-bound, not CPU-bound.

Design rules
 • A job failure becomes a result row, never a fleet crash.
 • Results return in input order regardless of finish order.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable


def run_fleet(jobs: list[dict[str, str]], make_harness: Callable,
              max_workers: int = 4) -> list[dict[str, Any]]:
    """Run one harness per job in parallel and gather their reports.

    *jobs* is [{"name", "workdir", "task"}]; *make_harness(workdir)*
    returns a ready Harness.  Each result is {"name", "ok", "report"} —
    the final text on success, "<ExceptionType>: <message>" on failure.
    """
    def one(job: dict[str, str]) -> dict[str, Any]:
        try:
            report = make_harness(job["workdir"]).run(job["task"])
            return {"name": job["name"], "ok": True, "report": report}
        except Exception as exc:
            return {"name": job["name"], "ok": False,
                    "report": f"{type(exc).__name__}: {exc}"}

    # pool.map preserves input order even when jobs finish out of order.
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        return list(pool.map(one, jobs))
