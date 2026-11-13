---
name: marimo
description: "Create, debug, convert, and export reactive marimo Python notebooks and apps, including agent pairing."
---

# Marimo Notebooks

Author reactive Python notebooks and apps; install upstream skills via [vendor-skills](../../agent-project/references/vendor-skills.md).

## Workflow

1. **Edit with disk reload**: run `marimo edit --watch notebook.py` (via `uv run marimo` when project-declared, else the `mise`-locked workstation CLI; preserve PEP 723 metadata). Keep loopback binding and token auth enabled because cells can access local files, networks, and credentials.
1. **Check before fixing**: run `marimo check --strict notebook.py` (fails on warnings). Scope `marimo check --fix notebook.py` to the target file, inspect the diff, and re-run `--strict`; avoid `--unsafe-fixes` without review.
1. **Export deliberately**: `marimo export html` executes cells (source and outputs may carry private data), and `marimo run` still executes Python server-side.

## Agent pairing

marimo `0.25+` includes native `marimo pair` (replacing `curl`/`jq` wrapper scripts). Check `marimo pair --help` for installed flags: list open browser sessions via `marimo pair notebook list`, and run cells via `marimo pair execute` (returns JSON with a `next` recovery command; headless servers have no session until opened in a browser). Keep tokens in private files (`marimo edit --token-password-file <file>`, `marimo pair ... --token-file <file>`, or `MARIMO_TOKEN`), never CLI args, and treat server logs as sensitive (they print tokenized URLs). Use `--no-token` only for isolated local work.

Pairing executes kernel code and `ctx.packages.add` mutates project dependencies — both require task authority. Optional edit hooks should run read-only `marimo check --strict --ignore-scripts "<edited-file>"`, keeping `--fix` manual to prevent hook loops.

## Official Skills

Review upstream `marimo-team/skills` per [vendor-skills](../../agent-project/references/vendor-skills.md) (`marimo-team/marimo-pair` is superseded by `marimo pair`). Verify Pyodide package support before proposing `marimo export html-wasm`.

## Documentation

- [marimo docs](https://docs.marimo.io) · [Agent pairing](https://docs.marimo.io/guides/generate_with_ai/marimo_pair/) · [Releases](https://github.com/marimo-team/marimo/releases)
- Companion skills: [python-stack](../../python-stack/references/foundation/GUIDE.md), [agent-project](../../agent-project/SKILL.md), [duckdb](../../duckdb/SKILL.md).
