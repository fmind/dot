---
name: python-script
description: "Standalone single-file utilities with PEP 723 inline metadata run by uv run --script."
---

# PEP 723 Standalone Python Scripts

Single-file CLIs with inline `# /// script` metadata executed via `uv run --script`. Prefer `dependencies = []` (instant startup, zero supply chain); promote to [foundation](../foundation/GUIDE.md) past ~200 lines or a second module, and keep agent scratch scripts in `.agents/tmp/`.

## Workflow

1. **Template**: start from [script.py](templates/script.py) (`#!/usr/bin/env -S uv run --quiet --script`, `requires-python`, `dependencies`), adding lower bounds only when needed; multi-command toolboxes use [argparse bootstrap](../argparse/references/bootstrap.md).
1. **CLI & output**: parse with `argparse` (`metavar`, validating `type`, eager `-h`/`--help` and `--version`) per [CLI defaults](../cli-contracts.md#defaults-for-new-clis). Emit results on stdout and diagnostics on stderr as literal text (if Rich is added, disable markup, highlighting, and emoji on consoles).
1. **Sanitized errors**: keep usage errors in the parser (exit `2`); catch operational failures, print specific redacted recovery advice to stderr, and `raise SystemExit(1) from error` (no raw exception strings/tracebacks by default; `--verbose` adds progress only).
1. **Run, lock, & audit**: execute via `chmod +x script.py && ./script.py input.txt` or `uv run script.py input.txt`. Lock durable scripts with `uv lock --script script.py`, run with `uv run --locked --script script.py`, and scan via `uv audit --preview-features audit-command --locked --script script.py` (schedule externally via [scheduled-jobs](../../../scheduled-jobs/SKILL.md)).
1. **Lint, type-check, & test**: run `ruff check script.py`, `uv sync --script script.py`, and `ty check --python "$(uv python find --script script.py)" script.py`, then test `--help`/`--version` without inputs, exit `2` usage errors, stream separation, bracketed paths, and redacted errors.

## Documentation

- [PEP 723](https://peps.python.org/pep-0723/) · [uv scripts](https://docs.astral.sh/uv/guides/scripts/) · [argparse](https://docs.python.org/3/library/argparse.html) · [uv releases](https://github.com/astral-sh/uv/releases) ([changelog](https://github.com/astral-sh/uv/blob/main/CHANGELOG.md)) · Companions: [foundation](../foundation/GUIDE.md), [uv](../uv.md), [cli-contracts](../cli-contracts.md).
