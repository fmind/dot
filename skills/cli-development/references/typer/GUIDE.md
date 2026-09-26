---
name: typer
description: "Typer application code, help, completion, and command tests."
---

# Typer

Use Typer for Python CLIs; [cli-contracts](../cli-contracts.md) owns command behavior and [python-stack](../../../python-stack/references/foundation/GUIDE.md) owns packaging.

## Workflow

1. For a new CLI, follow [bootstrap](references/bootstrap.md) after the shared Python foundation; it owns the application additions and qualification.
1. Inspect the locked Typer version and current entry point; add `typer` with `uv add typer` for a new CLI. Apply the [CLI defaults](../cli-contracts.md#defaults-for-new-clis) to new interfaces.
1. Load the official guidance, then implement the accepted arguments, options, output streams, and exit statuses.
1. Test help aliases, eager version output, successful execution, invalid arguments, separate streams, and failure output using the project test harness. Generate shell completions in fresh subprocesses so prior Typer initialization cannot hide failures; include the installed entry point when packaging changes. Add JSON, non-TTY prompts, and broken-configuration cases when those features exist.

## CLI resources

- [init-cli.py](templates/init-cli.py) supplies the application; [main.py](templates/main.py) supplies the module entry point.
- [test_smoke.py](templates/test_smoke.py) and [test_cli.py](templates/test_cli.py) exercise imports and command behavior.

## Gotchas

- The official skill lives inside the Python source package; `skills add fastapi/typer --list` discovers it without copying site-packages by hand.
- Install `typer` alone: `typer-slim` and `typer-cli` are deprecated. Typer vendors Click since 0.26.0, so use `typer.testing.CliRunner` and do not assume external Click classes or extensions interoperate with its command objects. An independent Click dependency can remain when another application component requires it; do not remove it as incidental CLI cleanup.
- `Typer(no_args_is_help=True)` is inert until the app has a callback, a sub-app, or a second command; set it on `@app.command()` instead.
- Typer promotes a sole command to the root unless a callback fixes the group shape. The packaged starter uses a callback so `tool greet` remains stable when commands are added; a focused single-command utility should deliberately use the other shape.
- Configure `context_settings={"help_option_names": ["-h", "--help"]}` and an eager `--version` callback; neither requires application configuration. `pretty_exceptions_show_locals=False` hides locals only, so sanitize expected application failures separately.

## Official Skills

Upstream: [fastapi/typer](https://github.com/fastapi/typer). Follow the shared [vendor-skill policy](../../../agent-project/references/vendor-skills.md) and select the Typer CLI guidance.

## Documentation

- [Typer documentation](https://typer.tiangolo.com/) · [Skills CLI](https://skills.sh/docs/cli)
- Releases: [Typer release notes](https://typer.tiangolo.com/release-notes/) · [GitHub releases](https://github.com/fastapi/typer/releases)
