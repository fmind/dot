---
name: typer
description: "Typer application code, help, completion, and command tests."
---

# Typer

Use Typer for Python CLIs; [cli-contracts](../cli-contracts.md) owns command behavior and [foundation](../foundation/GUIDE.md) owns packaging.

## Workflow

1. **Start from the locked version**: an existing CLI keeps its locked Typer and entry point; a new CLI follows [bootstrap](references/bootstrap.md) after the shared Python foundation and applies the [CLI defaults](../cli-contracts.md#defaults-for-new-clis).
1. **Cover help, streams, and completions**: test help aliases, eager version output, successful execution, invalid arguments, separate streams, and failure output using the project test harness. Generate shell completions in fresh subprocesses so prior Typer initialization cannot hide failures; include the installed entry point when packaging changes. Add JSON, non-TTY prompts, and broken-configuration cases when those features exist.

## CLI resources

- [init-cli.py](templates/init-cli.py) supplies the application; [main.py](templates/main.py) supplies the module entry point.
- [test_smoke.py](templates/test_smoke.py) and [test_cli.py](templates/test_cli.py) exercise imports and command behavior.

## Gotchas

- **Read the locked release's bundled skill**: Typer 0.25.1+ wheels ship the official skill at `typer/.agents/skills/typer/SKILL.md` in the installed package; read that version-matched copy, and start from `DISABLE_TELEMETRY=1 skills add fastapi/typer --list` only when the project needs a reviewed project-scope install. Where its `no_args_is_help` advice differs, follow the gotcha below.
- **Install `typer` alone**: `typer-slim` and `typer-cli` are deprecated. Typer vendors Click since 0.26.0, so use `typer.testing.CliRunner` and do not assume external Click classes or extensions interoperate with its command objects. An independent Click dependency can remain when another application component requires it; do not remove it as incidental CLI cleanup.
- **Set `no_args_is_help` on the command**: `Typer(no_args_is_help=True)` is inert until the app has a callback, a sub-app, or a second command; set it on `@app.command()` instead.
- **Fix the group shape with a callback**: Typer promotes a sole command to the root unless a callback fixes the group shape. The packaged starter uses a callback so `tool greet` remains stable when commands are added; a focused single-command utility should deliberately use the other shape.
- **Keep agent-invoked startup cheap**: profile imports with `uv run python -X importtime -c 'import <package>' 2> importtime.log` and import heavy SDKs inside the commands that use them; on Python 3.15+ a module-level `__lazy_modules__ = ["<module>", ...]` defers those imports and older interpreters ignore it, whereas `lazy import` syntax fails to parse before 3.15.
- **Parse help panels when walking commands**: default Typer help draws boxed `Options` and `Commands` panels even when piped (verified on Typer 0.27.3); only `rich_markup_mode=None` prints Click's plain `Commands:` list. Recursive help walks, such as a smoke test, must parse the panel or the app must set that mode.
- **Configure help, version, and error sanitizing**: configure `context_settings={"help_option_names": ["-h", "--help"]}` and an eager `--version` callback; neither requires application configuration. `pretty_exceptions_show_locals=False` hides locals only; sanitize errors per [CLI contracts](../cli-contracts.md#defaults-for-new-clis).

## Official Skills

Upstream: [fastapi/typer](https://github.com/fastapi/typer). Follow the shared [vendor-skill policy](../../../agent-project/references/vendor-skills.md) and select the Typer CLI guidance.

## Documentation

- [Typer documentation](https://typer.tiangolo.com/) · [Skills CLI](https://skills.sh/docs/cli)
- Releases: [Typer release notes](https://typer.tiangolo.com/release-notes/) · [GitHub releases](https://github.com/fastapi/typer/releases)
