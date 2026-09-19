---
name: python-script
description: "Standalone single-file utilities with PEP 723 inline metadata run by uv run --script."
---

# PEP 723 Standalone Python Scripts

Single-file Python CLI scripts with inline dependency metadata (PEP 723) run by `uv run` — no virtualenv, no `pyproject.toml`; a script that outgrows one file moves to [foundation](../foundation/GUIDE.md).

## Workflow

1. **Start from the template**: copy [script.py](templates/script.py); its shebang (`#!/usr/bin/env -S uv run --quiet --script`) and `# /// script` block declare `requires-python` and dependency lower bounds.
1. **Parse arguments with Typer**: `Annotated[..., typer.Argument/Option(...)]` with help text; Rich `Console()` for stdout results and `Console(stderr=True)` for logs and errors.
1. **Handle errors at the boundary**: catch in the command, `err.print_exception(show_locals=False)` (locals can hold secrets), then `raise typer.Exit(code=1) from None`; elsewhere let errors propagate.
1. **Run**: `chmod +x script.py && ./script.py input.txt`, or `uv run script.py input.txt`; uv resolves and caches the dependencies on first run.
1. **Lock a durable script**: `uv lock --script script.py`, then `uv run --locked --script script.py`; lower bounds alone are not reproducible.

For recurring execution of the finished command, use [scheduled-jobs](../../../scheduled-jobs/SKILL.md); keep scheduling outside the script.

## Gotchas

- **Agent scratch scripts** live in `.agents/tmp/`.
- **One file**: past ~200 lines or a second module, switch to a full project.

## Documentation

- [PEP 723](https://peps.python.org/pep-0723/) · [uv scripts](https://docs.astral.sh/uv/guides/scripts/) · [Typer](https://typer.tiangolo.com/)
- Releases: [uv](https://github.com/astral-sh/uv/releases) · [changelog](https://github.com/astral-sh/uv/blob/main/CHANGELOG.md)
- Companion guides: [foundation](../foundation/GUIDE.md) (full projects), [uv](../uv.md) (script and lock modes), [cli-contracts](../../../cli-development/references/cli-contracts.md) (flags, streams, exit codes).
