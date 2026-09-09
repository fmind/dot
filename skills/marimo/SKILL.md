---
name: marimo
description: Author, edit, run, and check reactive Python notebooks and apps with marimo, configure agent harness pairing, and install official skills. Use for marimo notebooks, apps, or pairing.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/marimo
  created: "2026-09-08"
  updated: "2026-09-08"
---

# marimo

Use marimo for reactive Python notebooks and apps; configure agent pairing and harness workflows, and install upstream skills through [agent-project](../agent-project/references/vendor-skills.md).

## Workflow

1. **Inspect the environment**: use `marimo --version` and the installed command help; prefer `uv run marimo` when the project declares marimo. Preserve the notebook's dependency model, including existing PEP 723 metadata.
1. **Edit with disk reload**: `marimo edit --watch notebook.py` lets the running notebook reload agent edits. Keep the default loopback host and token authentication; cell execution can access local files, network services, and credentials.
1. **Respect reactivity**: each global name belongs to one cell; use `_name` for cell-local intermediates. Preserve `@app.cell` structure and make side effects deliberate because dependent cells can rerun after upstream edits.
1. **Check before fixing**: `marimo check --strict notebook.py` reports notebook diagnostics and fails on warnings. Apply `marimo check --fix notebook.py` only to the intended file, review the diff, then rerun the strict check. Fixes do not automatically repair every dependency or syntax problem; `--unsafe-fixes` can change behavior.
1. **Exercise behavior**: run representative inputs and inspect outputs and exceptions in the notebook. Lint success alone does not prove cell execution, data correctness, or app behavior.
1. **Convert or export**: use the commands below, review conversion diagnostics, and validate the result. HTML export executes the notebook unless an installed option says otherwise; outputs and source may contain private data. `marimo run` hides editing controls but still executes Python on the server.

## Commands

```bash
marimo edit --watch notebook.py
marimo check --strict notebook.py
marimo run notebook.py
marimo convert notebook.ipynb -o notebook.py
marimo export html notebook.py -o notebook.html
marimo pair prompt --url http://127.0.0.1:2718 --with-token
```

## Agent pairing

Use `marimo pair prompt --help` to select the installed harness validation flag (`--claude`, `--codex`, or `--opencode`). `--with-token` prompts for the existing server token and stores it temporarily; pass it privately rather than logging it. The reviewed `marimo-pair` scripts also support `MARIMO_TOKEN`. Keep `--no-token` an explicit choice for a controlled local session, not the pairing default.

Pairing scripts require `bash`, `curl`, and `jq` plus authority to execute code in the selected notebook. Review scripts and any harness permission entries through the [vendor-skill policy](../agent-project/references/vendor-skills.md); authorize the needed script paths rather than all shell commands. Do not change global harness settings merely to use a notebook.

An optional edit hook can run `marimo check --strict --ignore-scripts <edited-file>`; quote the path, limit it to the edited notebook, and surface failures. Keep mutation with `--fix` an explicit operation to avoid edit-hook loops.

## Official Skills

Upstream: [marimo-team/skills](https://github.com/marimo-team/skills), for notebook authoring, conversion, widgets, and WASM compatibility; interactive pairing lives in [marimo-team/marimo-pair](https://github.com/marimo-team/marimo-pair). List with `skills add marimo-team/skills --list` or `skills add marimo-team/marimo-pair --list`, review the needed selection, and install at project scope with `skills add <source> --skill <name> -y`. For browser execution with `marimo export html-wasm`, verify Pyodide dependency compatibility and server-only capabilities before promising parity.

## Documentation

- [marimo documentation](https://docs.marimo.io) · [Agent customization guide](https://docs.marimo.io/guides/generate_with_ai/customize_your_agent/) · [Skills CLI](https://skills.sh/docs/cli)
- Companion skills: [python-stack](../python-stack/SKILL.md), [agent-project](../agent-project/SKILL.md), [duckdb](../duckdb/SKILL.md).
