---
name: marimo
description: "Create, debug, convert, and export reactive marimo Python notebooks and apps, including agent pairing."
---

# Marimo Notebooks

Use marimo for reactive Python notebooks and apps; configure agent pairing and harness workflows, and install upstream skills through [agent-project](../../agent-project/references/vendor-skills.md).

## Workflow

1. **Edit with disk reload**: `marimo edit --watch notebook.py` lets the running notebook reload agent edits; prefer `uv run marimo` when the project declares marimo and preserve existing PEP 723 metadata. Keep the default loopback host and token authentication: cell execution can access local files, network services, and credentials.
1. **Check before fixing**: `marimo check --strict notebook.py` fails on warnings. Apply `marimo check --fix notebook.py` only to the intended file, review the diff, then rerun the strict check; `--unsafe-fixes` can change behavior.
1. **Export deliberately**: `marimo export html` executes the notebook, and outputs and source may contain private data; `marimo run` hides editing controls but still executes Python on the server.

## Agent pairing

marimo 0.25+ ships an agent-facing `marimo pair` CLI, so pairing no longer needs the vendor skill's `bash`, `curl`, and `jq` scripts. Its subcommands and flags still change between releases, so follow `marimo pair --help` for the installed version: list sessions with `marimo pair notebook list`, then run code with `marimo pair execute`, which prints JSON with a `next` recovery command. A headless server has no session until the notebook is open in a browser. For token authentication, write the token to a private file, start the server with `marimo edit --token-password-file <token-file>`, and pass `--token-file <token-file>` (or `MARIMO_TOKEN`) to pair commands; never put the token in arguments, and keep the server log private because it prints the tokenized URL. Keep `--no-token`, which the help suggests, an explicit choice for a controlled local session.

Pairing executes code in the notebook kernel, and `ctx.packages.add` changes project dependencies, so both need the task's authority. Do not change global harness settings merely to use a notebook.

An optional edit hook can run `marimo check --strict --ignore-scripts <edited-file>`; quote the path, limit it to the edited notebook, and surface failures. Keep mutation with `--fix` an explicit operation to avoid edit-hook loops.

## Official Skills

Upstream: [marimo-team/skills](https://github.com/marimo-team/skills), for notebook authoring, conversion, widgets, and WASM compatibility; [marimo-team/marimo-pair](https://github.com/marimo-team/marimo-pair) wraps pairing in `curl` and `jq` scripts that the native `marimo pair` commands make optional. List with `DISABLE_TELEMETRY=1 skills add marimo-team/skills --list`, then review and install only the needed selection from an immutable snapshot per the [vendor-skill policy](../../agent-project/references/vendor-skills.md). For browser execution with `marimo export html-wasm`, verify Pyodide dependency compatibility and server-only capabilities before promising parity.

## Documentation

- [marimo documentation](https://docs.marimo.io) · [Agent pairing](https://docs.marimo.io/guides/generate_with_ai/marimo_pair/) · [Agent customization guide](https://docs.marimo.io/guides/generate_with_ai/customize_your_agent/) · [Skills CLI](https://skills.sh/docs/cli)
- Releases: [marimo](https://github.com/marimo-team/marimo/releases)
- Companion skills: [python-stack](../../python-stack/references/foundation/GUIDE.md), [agent-project](../../agent-project/SKILL.md), [duckdb](../../duckdb/SKILL.md).
