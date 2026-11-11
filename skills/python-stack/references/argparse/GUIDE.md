---
name: argparse
description: "Design CLI contracts (commands, flags, streams, exit codes, JSON) and build Python argparse or Typer CLIs."
---

# CLI Contracts & Python CLIs

Define a stable human + machine CLI contract in any language, and build Python CLIs with `argparse` (starter templates below) or [Typer](#typer-clis) when typed command trees and rich help fit better ([foundation](../foundation/GUIDE.md) owns packaging; existing CLIs keep their framework).

## Defaults for new CLIs

Existing public contracts govern shape, streams, exit codes, and formats; side-effect-free help/version, consent, markup escaping, and error redaction apply to every CLI:

- **Command shape, help, & version**: explicit subcommands for growing toolboxes, single command for one focused job. `-h`/`--help` (root + subcommands) and eager root `--version` work without credentials, network, valid config, or side effects (`0` on explicit help; `2` + stderr usage on invalid args or bare command groups unless defined as help).
- **Streams, exits, & JSON**: requested data on stdout; progress, diagnostics, and sanitized recovery errors on stderr (`-v`/`--verbose` adds stderr progress only, never raw tracebacks or secret/token values). Exit codes: `0` success, `2` invalid usage, `1` operational failure. `--json` emits one schema-stable JSON object on stdout (empty stdout + stderr error + non-zero exit on failure); bound large outputs via filters, limits, cursors, or file export.
- **Secrets, config, & TTY**: never pass secrets in CLI args (use credential stores, protected files, hidden TTY prompts, or stdin); precedence is flags > `<APP>_*` env vars > config file > defaults (validated lazily per command). Detect stdout/stderr TTY separately, honor non-empty `NO_COLOR` and `TERM=dumb`, disable spinners/pagers on pipes, escape untrusted markup, provide flags for every required input, never prompt on non-TTY stdin (`--no-input` disables prompts without consent), and require confirmation or `--yes` on destructive actions.

## Workflow

1. **Bootstrap**: follow [bootstrap](references/bootstrap.md) for packaged CLIs, or [python-script](../python-script/GUIDE.md) for single-file scripts.
1. **Isolate `Namespace` at the boundary**: build the parser tree in `build_parser()`, bind subparsers via `set_defaults(handler=...)`, and unpack untyped `args` into typed handler arguments (`lambda args: greet(name=args.name)`) or a typed dataclass so `ty check` verifies call sites. Pass `allow_abbrev=False` and `suggest_on_error=True` (`3.14+`) on every parser.
1. **Fail invalid input with exit `2`**: use `choices`, `type`, `nargs`, `required`, and `parser.error("--since: must not be after --until")` (prints usage to stderr and exits `2`, never `1`).
1. **Test streams & exit codes**: assert stdout, stderr, and exit codes (`0`/`1`/`2`) across `-h`/`--help` (root + subcommand, including broken config / no credentials), `--version`, happy paths, usage errors, non-TTY/`--no-input`, piped/`NO_COLOR`, and JSON schemas via in-process `main([...])` + `capsys` + `pytest.raises(SystemExit)`, plus one subprocess `python -m <package>` smoke test (and fresh-shell completions when shipped).

## CLI resources

- [init-cli.py](templates/init-cli.py) and [main.py](templates/main.py): CLI implementation and module entry point.
- [test_smoke.py](templates/test_smoke.py) and [test_cli.py](templates/test_cli.py): import and CLI contract tests.

## Gotchas

- **`help` vs `description` & subparsers**: `add_parser(name, help=...)` populates parent list summaries (omit `help` to hide internal commands; `description` renders on `<cmd> --help`). `add_subparsers(title="commands", metavar="COMMAND", required=True)` avoids `{a,b,c}` noise and exits `2` on bare group calls; never reuse a root option's `dest` on a subcommand.
- **Flags, env defaults, & colors**: pass `"-n", "--limit"` with `metavar` (`--since WHEN`), and build parsers inside `main()` reading `os.environ.get("APP_CONFIG") or None` (named in `help`). Python `3.14+` colors TTY help/errors (`NO_COLOR`, `FORCE_COLOR`, `PYTHON_COLORS`) — set `NO_COLOR=1` and strip forcing vars in tests.
- **Formatting, TUIs, & startup**: use `RawDescriptionHelpFormatter` for multi-paragraph help; add `argcomplete` or `rich`/`textual` (markup/highlighting/emoji disabled on untrusted text) only for interactive human UIs, never agent CLIs. Profile startup via `uv run python -X importtime -c 'import <package>'` and lazy-import heavy SDKs inside handlers (or module-level `__lazy_modules__ = [...]` on `3.15+`).

## Typer CLIs

When building or maintaining a Typer CLI:

- **Bundled skill & minor pin**: read `typer/.agents/skills/typer/SKILL.md` from `.venv/` (`0.25.1+`) and pin `typer>=0.N,<0.N+1` (`0.x` minors break APIs; `typer-slim`/`typer-cli` are deprecated, and Click is vendored since `0.26.0` — use `typer.testing.CliRunner`).
- **Group callback & plain help**: add `@app.callback()` so single-command apps keep subcommand shape and `no_args_is_help=True` works; set `rich_markup_mode=None` when plain piped help is required (`GITHUB_ACTIONS`/`FORCE_COLOR`/`PY_COLORS` override `NO_COLOR` on Rich panels).

## Documentation

- [argparse](https://docs.python.org/3/library/argparse.html) · [Command Line Interface Guidelines](https://clig.dev) · [NO_COLOR](https://no-color.org/) · [Typer releases](https://typer.tiangolo.com/release-notes/)
