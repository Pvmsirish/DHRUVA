# Changelog

## 1.1.0

- Add `--json` output mode to `list` and `stats` for scripting/composition.
- Add `-v/--verbose` flag to `list` to surface the `COMPLETED` timestamp column.
- Rename the cryptic `S` table column to `DONE`.
- Add usage examples and store-resolution notes to `--help` output.
- Clarify `--tag` help text (comma is a separator, not a literal char).
- Add README, LICENSE, pyproject.toml packaging, .gitignore, and this changelog.
- Expand test suite: whitespace-only title rejection, help exit codes for
  every subcommand, and `--json` output validation for `list`/`stats`.

## 1.0.0

- Initial release: `add`, `list`, `done`, `rm`, `stats` subcommands with
  atomic JSON persistence and an aligned table renderer.
