---
name: typer
description: Build typed Python command-line applications with Typer and its official skill. Use when scaffolding a CLI or changing commands, options, help, or CLI tests.
license: MIT
metadata:
  source: github.com/fmind/dot/tree/main/skills/typer
  created: "2026-09-06"
  updated: "2026-09-11"
---

# Typer

Use Typer for Python CLIs; [cli-contracts](../cli-contracts/SKILL.md) owns command behavior and [python-stack](../python-stack/SKILL.md) owns packaging.

## Workflow

1. For a new CLI, follow [bootstrap](references/bootstrap.md) after the shared Python foundation; it owns the application additions and qualification.
1. Inspect the locked Typer version and current entry point; add `typer` with `uv add typer` for a new CLI.
1. Load the official guidance, then implement the accepted arguments, options, output streams, and exit statuses.
1. Test help, successful execution, invalid arguments, and failure output using the project test harness; include the installed entry point when packaging changes.

## CLI resources

- [init-cli.py](references/init-cli.py) supplies the application; [main.py](references/main.py) supplies the module entry point.
- [test_smoke.py](references/test_smoke.py) and [test_cli.py](references/test_cli.py) exercise imports and command behavior.

## Gotchas

- The official skill lives inside the Python source package; `skills add fastapi/typer --list` discovers it without copying site-packages by hand.
- Install `typer` alone: `typer-slim` and `typer-cli` are deprecated, and Typer vendors Click since 0.26.0, so never add `click` or a Click extension and test with `typer.testing.CliRunner`.
- `Typer(no_args_is_help=True)` is inert until the app has a callback, a sub-app, or a second command; set it on `@app.command()` instead.

## Official Skills

Upstream: [fastapi/typer](https://github.com/fastapi/typer). Follow the shared [vendor-skill policy](../agent-project/references/vendor-skills.md) and select the Typer CLI guidance.

## Documentation

- [Typer documentation](https://typer.tiangolo.com/) · [Skills CLI](https://skills.sh/docs/cli)
