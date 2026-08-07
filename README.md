# Odysseus (project DHRUVA)

The smallest agent harness that is still a real one: **ten working files,
zero dependencies**, Python 3.10+ standard library only. Built in five days
as a reference implementation — every file teaches one concept and carries
its design rules in its docstring.

An agent here is exactly four things: a model behind one function, a loop
that runs tools until the model stops asking, a security gate in front of
every tool call, and files for everything that must outlive the process
(sessions, memory, skills).

## Running it

Put an Anthropic API key in the environment (or in `CLAUDE_API_KEY.txt` as
`ANTHROPIC_API_KEY = sk-ant-...`):

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

Three CLI forms:

```bash
# 1. Interactive REPL — safe mode, writes ask for y/N approval
python3 -m odysseus

# 2. Headless — one task, yolo mode, exit when done
python3 -m odysseus -p "Create a fib.py and verify fib(30)" -d ./scratch

# 3. Resume — continue the latest session after Ctrl-C or a crash
python3 -m odysseus --resume
```

## Anatomy, day by day

| Day | File          | Teaches                                                        |
|-----|---------------|----------------------------------------------------------------|
| 1   | `provider.py` | One neutral message format; all vendor detail behind `complete()` |
| 1   | `loop.py`     | Think → act → observe; tools can fail, the loop cannot          |
| 2   | `tools.py`    | `@tool` from a signature; a path jail every file op passes through |
| 2   | `security.py` | Deny patterns always; modes read-only/safe/yolo; human approver |
| 3   | `context.py`  | Compaction: summarize the old, keep the recent tail verbatim    |
| 3/4 | `memory.py`   | DHRUVA.md folded into the system prompt; `remember()` appends   |
| 3/4 | `skills.py`   | Progressive disclosure: a one-line catalog, full text on demand |
| 4   | `session.py`  | Append-only JSONL; torn-tail tolerance; crash repair            |
| 4   | `subagent.py` | Delegation as a tool; fresh context; depth cap                  |
| 4   | `harness.py`  | Composition of everything above; durable `run()` and `resume()` |
| 5   | `cli.py`      | Headless and interactive front door                             |
| 5   | `fleet.py`    | Many harnesses in parallel; failures become rows, not crashes   |

## Composing it

Everything is ordinary Python. Register an extra tool by decorating a
function and handing it to the Harness:

```python
from odysseus import Harness, tool

@tool("Get the current UTC time", fmt="strftime format to use")
def utc_now(fmt: str = "%Y-%m-%d %H:%M") -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime(fmt)

report = Harness("./scratch", extra_tools=[utc_now]).run(
    "What UTC time is it? Answer in one line.")
print(report)
```

The same pattern scales down (a `Policy("read-only")` harness for audits)
and up (`run_fleet` over a list of jobs, one directory each — see
`demos/day5_fleet.py`, which ships three real products in parallel).
