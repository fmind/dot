---
name: python-script
description: "Standalone single-file utilities with PEP 723 inline metadata run by uv run --script."
---

# PEP 723 Standalone Python Scripts

Single-file Python CLI scripts with inline dependency metadata (PEP 723) run by `uv run`; uv manages the environment without a `pyproject.toml` or manual virtualenv setup. A script that needs reusable modules moves to [foundation](../foundation/GUIDE.md).

## Workflow

1. **Start from the template**: copy [script.py](templates/script.py); its shebang (`#!/usr/bin/env -S uv run --quiet --script`) and `# /// script` block declare `requires-python` and dependency lower bounds.
1. **Parse arguments with Typer**: use `Annotated[..., typer.Argument/Option(...)]` with help text and the [CLI defaults](../../../cli-development/references/cli-contracts.md#defaults-for-new-clis). The template stays a single command with `-h` / `--help` and an eager `--version` that works without an input file. Packaged toolboxes use the explicit-group [Typer starter](../../../cli-development/references/typer/references/bootstrap.md).
1. **Render values literally**: stdout carries results and stderr carries progress/errors. The template disables Rich markup, highlighting, and emoji conversion so external paths remain literal; apply styles separately and avoid wrapping path values. Use `typer.echo` or a serializer directly for machine data.
1. **Handle errors at the boundary**: catch failures around application work, give specific sanitized recovery advice for expected errors, and preserve the cause with `raise typer.Exit(code=1) from exc`. Keep CLI exits outside the protected operation. Never print raw exception messages or tracebacks by default: `show_locals=False` does not redact exception text, causes, or source lines. `--verbose` adds progress only; add opt-in diagnostic tracebacks only with a tested redaction policy.
1. **Run**: `chmod +x script.py && ./script.py input.txt`, or `uv run script.py input.txt`; uv resolves and caches the dependencies on first run.
1. **Lock a durable script**: `uv lock --script script.py`, then `uv run --locked --script script.py`; lower bounds alone are not reproducible.
1. **Verify the interface**: run help and version without inputs; check usage errors, stdout/stderr separation, bracket-containing paths, and sanitized failures with verbosity both enabled and disabled. Add JSON and non-interactive cases only when those features exist.

For recurring execution of the finished command, use [scheduled-jobs](../../../scheduled-jobs/SKILL.md); keep scheduling outside the script.

## Gotchas

- **Agent scratch scripts** live in `.agents/tmp/`.
- **One file**: past ~200 lines or a second module, switch to a full project.

## Documentation

- [PEP 723](https://peps.python.org/pep-0723/) · [uv scripts](https://docs.astral.sh/uv/guides/scripts/) · [Typer](https://typer.tiangolo.com/)
- Releases: [uv](https://github.com/astral-sh/uv/releases) · [changelog](https://github.com/astral-sh/uv/blob/main/CHANGELOG.md)
- Companion guides: [foundation](../foundation/GUIDE.md) (full projects), [uv](../uv.md) (script and lock modes), [cli-contracts](../../../cli-development/references/cli-contracts.md) (flags, streams, exit codes).
