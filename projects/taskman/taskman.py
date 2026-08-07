#!/usr/bin/env python3
"""taskman - a small JSON-backed CLI task manager.

Store location resolution order:
  1. --store PATH
  2. $TASKMAN_STORE
  3. ~/.taskman.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone

VERSION = "1.1.0"
SCHEMA = 1
PRIORITIES = ("low", "med", "high")
_PRIO_RANK = {"high": 0, "med": 1, "low": 2}

DEFAULT_STORE = os.path.join(os.path.expanduser("~"), ".taskman.json")


# --------------------------------------------------------------------------
# errors
# --------------------------------------------------------------------------
class TaskmanError(Exception):
    """User-facing error; results in exit code 1."""


# --------------------------------------------------------------------------
# storage
# --------------------------------------------------------------------------
def store_path(args) -> str:
    return getattr(args, "store", None) or os.environ.get("TASKMAN_STORE") or DEFAULT_STORE


def _empty_db() -> dict:
    return {"version": SCHEMA, "next_id": 1, "tasks": []}


def load(path: str) -> dict:
    if not os.path.exists(path):
        return _empty_db()
    try:
        with open(path, "r", encoding="utf-8") as fh:
            text = fh.read().strip()
    except OSError as exc:
        raise TaskmanError("cannot read store %s: %s" % (path, exc))
    if not text:
        return _empty_db()
    try:
        data = json.loads(text)
    except ValueError as exc:
        raise TaskmanError("corrupt store %s: %s" % (path, exc))
    if not isinstance(data, dict) or not isinstance(data.get("tasks"), list):
        raise TaskmanError("corrupt store %s: unexpected structure" % path)
    data.setdefault("version", SCHEMA)
    data.setdefault("next_id", max([t.get("id", 0) for t in data["tasks"]] or [0]) + 1)
    return data


def save(path: str, db: dict) -> None:
    parent = os.path.dirname(os.path.abspath(path))
    if parent and not os.path.isdir(parent):
        os.makedirs(parent, exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(db, fh, indent=2, sort_keys=True)
        fh.write("\n")
    os.replace(tmp, path)


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def find(db: dict, tid: int) -> dict:
    for task in db["tasks"]:
        if task.get("id") == tid:
            return task
    raise TaskmanError("no such task: %d" % tid)


# --------------------------------------------------------------------------
# table rendering
# --------------------------------------------------------------------------
def render_table(headers, rows, aligns=None) -> str:
    cols = len(headers)
    aligns = aligns or ["<"] * cols
    cells = [[("" if c is None else str(c)) for c in row] for row in rows]
    widths = [len(str(h)) for h in headers]
    for row in cells:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    def line(values):
        out = []
        for i, val in enumerate(values):
            out.append(("%-*s" if aligns[i] == "<" else "%*s") % (widths[i], val))
        return "  ".join(out).rstrip()

    parts = [line(headers), "  ".join("-" * w for w in widths)]
    parts.extend(line(r) for r in cells)
    return "\n".join(parts)


def fmt_tags(task) -> str:
    return ",".join(task.get("tags") or [])


def print_json(obj, out) -> None:
    print(json.dumps(obj, indent=2, sort_keys=True), file=out)


# --------------------------------------------------------------------------
# commands
# --------------------------------------------------------------------------
def cmd_add(args, out) -> int:
    title = " ".join(args.title).strip()
    if not title:
        raise TaskmanError("title must not be empty")
    tags = []
    for chunk in args.tag or []:
        for piece in chunk.split(","):
            piece = piece.strip()
            if piece and piece not in tags:
                tags.append(piece)
    path = store_path(args)
    db = load(path)
    task = {
        "id": db["next_id"],
        "title": title,
        "priority": args.priority,
        "tags": tags,
        "done": False,
        "created": now(),
        "completed": None,
    }
    db["tasks"].append(task)
    db["next_id"] += 1
    save(path, db)
    print("added task %d: %s" % (task["id"], task["title"]), file=out)
    return 0


def cmd_list(args, out) -> int:
    db = load(store_path(args))
    tasks = list(db["tasks"])

    if args.done_only:
        tasks = [t for t in tasks if t["done"]]
    elif not args.all:
        tasks = [t for t in tasks if not t["done"]]

    if args.tag:
        want = args.tag.strip()
        tasks = [t for t in tasks if want in (t.get("tags") or [])]
    if args.priority:
        tasks = [t for t in tasks if t.get("priority") == args.priority]

    if args.sort == "priority":
        tasks.sort(key=lambda t: (_PRIO_RANK.get(t.get("priority"), 9), t["id"]))
    elif args.sort == "title":
        tasks.sort(key=lambda t: (t["title"].lower(), t["id"]))
    else:
        tasks.sort(key=lambda t: t["id"])

    if args.json:
        print_json(tasks, out)
        return 0

    if not tasks:
        print("no tasks", file=out)
        return 0

    if args.verbose:
        headers = ["ID", "DONE", "PRI", "TITLE", "TAGS", "COMPLETED"]
        aligns = [">", "<", "<", "<", "<", "<"]
        rows = [
            [
                t["id"],
                "x" if t["done"] else " ",
                t.get("priority", "med"),
                t["title"],
                fmt_tags(t),
                t.get("completed") or "-",
            ]
            for t in tasks
        ]
    else:
        headers = ["ID", "DONE", "PRI", "TITLE", "TAGS"]
        aligns = [">", "<", "<", "<", "<"]
        rows = [
            [
                t["id"],
                "x" if t["done"] else " ",
                t.get("priority", "med"),
                t["title"],
                fmt_tags(t),
            ]
            for t in tasks
        ]
    print(render_table(headers, rows, aligns), file=out)
    return 0


def cmd_done(args, out) -> int:
    path = store_path(args)
    db = load(path)
    changed = []
    for tid in args.id:
        task = find(db, tid)
        if task["done"]:
            print("task %d already done" % tid, file=out)
            continue
        task["done"] = True
        task["completed"] = now()
        changed.append(task)
    if changed:
        save(path, db)
    for task in changed:
        print("completed task %d: %s" % (task["id"], task["title"]), file=out)
    return 0


def cmd_rm(args, out) -> int:
    path = store_path(args)
    db = load(path)
    removed = []
    for tid in args.id:
        task = find(db, tid)
        db["tasks"].remove(task)
        removed.append(task)
    save(path, db)
    for task in removed:
        print("removed task %d: %s" % (task["id"], task["title"]), file=out)
    return 0


def cmd_stats(args, out) -> int:
    db = load(store_path(args))
    tasks = db["tasks"]
    total = len(tasks)
    done = sum(1 for t in tasks if t["done"])
    open_ = total - done
    pct = (100.0 * done / total) if total else 0.0

    open_by_priority = {
        prio: sum(1 for t in tasks if t.get("priority") == prio and not t["done"])
        for prio in PRIORITIES
    }
    tag_counts = {}
    for t in tasks:
        for tag in t.get("tags") or []:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1

    if args.json:
        print_json(
            {
                "total": total,
                "open": open_,
                "done": done,
                "percent_done": round(pct, 1),
                "open_by_priority": open_by_priority,
                "tags": tag_counts,
            },
            out,
        )
        return 0

    rows = [
        ["total", total],
        ["open", open_],
        ["done", done],
        ["percent done", "%.1f%%" % pct],
    ]
    for prio in PRIORITIES:
        rows.append(["open/" + prio, open_by_priority[prio]])
    for tag in sorted(tag_counts):
        rows.append(["tag/" + tag, tag_counts[tag]])

    print(render_table(["METRIC", "VALUE"], rows, ["<", ">"]), file=out)
    return 0


# --------------------------------------------------------------------------
# cli
# --------------------------------------------------------------------------
EPILOG = """\
examples:
  taskman add "write the docs" -p high -t work,urgent
  taskman list --all --sort priority
  taskman list --tag work --json
  taskman done 1 2
  taskman rm 3
  taskman stats

store location is chosen in this order: --store PATH, $TASKMAN_STORE,
then ~/.taskman.json
"""


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="taskman",
        description="A tiny JSON-backed task manager.",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--version", action="version", version="taskman " + VERSION)
    p.add_argument("--store", metavar="PATH", help="path to the JSON store")
    sub = p.add_subparsers(dest="command", metavar="COMMAND")

    a = sub.add_parser("add", help="add a task")
    a.add_argument("title", nargs="+", help="task title")
    a.add_argument("-p", "--priority", choices=PRIORITIES, default="med",
                   help="priority level (default: med)")
    a.add_argument("-t", "--tag", action="append", metavar="TAG",
                   help="tag to attach; repeat -t or separate with commas "
                        "(a tag itself cannot contain a comma)")
    a.set_defaults(func=cmd_add)

    l = sub.add_parser("list", help="list tasks")
    l.add_argument("-a", "--all", action="store_true", help="include completed tasks")
    l.add_argument("-d", "--done-only", action="store_true", help="only completed tasks")
    l.add_argument("-t", "--tag", help="filter by tag")
    l.add_argument("-p", "--priority", choices=PRIORITIES, help="filter by priority")
    l.add_argument("-s", "--sort", choices=("id", "priority", "title"), default="id",
                    help="sort order (default: id)")
    l.add_argument("-v", "--verbose", action="store_true",
                    help="also show the COMPLETED timestamp column")
    l.add_argument("--json", action="store_true", help="emit machine-readable JSON instead of a table")
    l.set_defaults(func=cmd_list)

    d = sub.add_parser("done", help="mark tasks complete")
    d.add_argument("id", nargs="+", type=int, help="task id(s) to complete")
    d.set_defaults(func=cmd_done)

    r = sub.add_parser("rm", help="remove tasks")
    r.add_argument("id", nargs="+", type=int, help="task id(s) to remove")
    r.set_defaults(func=cmd_rm)

    s = sub.add_parser("stats", help="show statistics")
    s.add_argument("--json", action="store_true", help="emit machine-readable JSON instead of a table")
    s.set_defaults(func=cmd_stats)
    return p


def main(argv=None, out=None, err=None) -> int:
    out = out or sys.stdout
    err = err or sys.stderr
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help(out)
        return 2
    try:
        return args.func(args, out)
    except TaskmanError as exc:
        print("taskman: error: %s" % exc, file=err)
        return 1


if __name__ == "__main__":
    sys.exit(main())
