"""Package entry point — ``python -m odysseus`` defers to the CLI."""

from odysseus.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
