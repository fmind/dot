---
name: typer
description: Build typed Python command-line applications with Typer and its official skill. Use when adding commands, arguments, options, help, or CLI tests.
license: MIT
metadata:
  source: github.com/fmind/dot/tree/main/skills/typer
  created: "2026-09-06"
  updated: "2026-09-06"
---

# Typer

Use Typer for Python CLIs; [cli-contracts](../cli-contracts/SKILL.md) owns command behavior and [python-stack](../python-stack/SKILL.md) owns packaging.

## Workflow

1. Inspect the locked Typer version and current entry point; add `typer` with `uv add typer` for a new CLI.
1. Load the official guidance, then implement the accepted arguments, options, output streams, and exit statuses.
1. Test help, successful execution, invalid arguments, and failure output using the project test harness; include the installed entry point when packaging changes.

## Gotchas

- The official skill lives inside the Python source package; `skills add fastapi/typer --list` discovers it without copying site-packages by hand.
- Install `typer`; the old `typer-slim` and `typer-cli` distributions are deprecated.

## Official Skills

Upstream: [fastapi/typer](https://github.com/fastapi/typer). Follow the shared [vendor-skill policy](../agent-project/references/vendor-skills.md) and select the Typer CLI guidance.

## Documentation

- [Typer documentation](https://typer.tiangolo.com/) · [Skills CLI](https://skills.sh/docs/cli)
