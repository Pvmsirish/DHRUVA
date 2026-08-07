# taskman

A tiny, dependency-free CLI task manager. Tasks are stored as plain JSON so
you can back them up, diff them, or pipe them into other tools.

## Install

Requires Python 3.8+. No third-party dependencies.

```bash
git clone <this-repo> taskman
cd taskman
python taskman.py --help
```

Or install it as a console script:

```bash
pip install -e .
taskman --help
```

## Quick start

```bash
taskman add "write the docs" -p high -t work,urgent
taskman add "buy milk" -p low -t home
taskman list
taskman done 1
taskman list --all --sort priority
taskman stats
```

## Commands

| Command | Purpose |
| --- | --- |
| `add TITLE... [-p PRIORITY] [-t TAG]` | Create a task. `-t` may be repeated or comma-separated. |
| `list [-a] [-d] [-t TAG] [-p PRIORITY] [-s SORT] [-v] [--json]` | List tasks. Open tasks only by default; `-a` shows everything, `-d` shows only completed. `--json` emits machine-readable output. |
| `done ID [ID ...]` | Mark one or more tasks complete. |
| `rm ID [ID ...]` | Delete one or more tasks. |
| `stats [--json]` | Show totals, completion percentage, open counts per priority, and per-tag counts. |

Run `taskman <command> -h` for full flag documentation, or `taskman --help`
for a top-level overview with examples.

## Where tasks are stored

Resolution order, first match wins:

1. `--store PATH`
2. `$TASKMAN_STORE`
3. `~/.taskman.json`

The store is a single JSON file, written atomically (write to a temp file,
then rename) so a crash mid-write can't corrupt it.

## Exit codes

- `0` success
- `1` a user-facing error (bad task id, corrupt store, empty title, ...);
  message goes to stderr
- `2` argument parsing error (from argparse) or no subcommand given

## Development

Run the test suite (20+ cases, each driving `taskman.py` as a real
subprocess against an isolated temp store):

```bash
python -m unittest test_taskman -v
```

## License

MIT, see [LICENSE](LICENSE).
