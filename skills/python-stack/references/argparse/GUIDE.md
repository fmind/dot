---
name: argparse
description: "Python CLI code with standard-library argparse: commands, help, usage errors, tests; existing Typer CLIs."
---

# Python CLIs With argparse

Build Python CLIs on stdlib `argparse` with zero runtime dependencies. [cli-contracts](../cli-contracts.md) owns command behavior and [foundation](../foundation/GUIDE.md) owns packaging; existing Typer/Click CLIs stay on their framework (see [Existing Typer CLIs](#existing-typer-clis)).

## Workflow

1. **Bootstrap**: follow [bootstrap](references/bootstrap.md) + [CLI defaults](../cli-contracts.md#defaults-for-new-clis) for packaged CLIs, or [python-script](../python-script/GUIDE.md) for single-file scripts.
1. **Isolate `Namespace` at the boundary**: build the parser tree in `build_parser()`, bind subparsers via `set_defaults(handler=...)`, and unpack untyped `args` into typed handler arguments (`lambda args: greet(name=args.name)`) or a typed dataclass so `ty check` verifies call sites. Pass `allow_abbrev=False` and `suggest_on_error=True` (`3.14+`) on every parser.
1. **Fail invalid input with exit `2`**: use `choices`, `type`, `nargs`, `required`, and `parser.error("--since: must not be after --until")` (prints usage to stderr and exits `2`, never `1`).
1. **Test streams & exit codes**: assert stdout, stderr, and exit codes separately across `-h`/`--help` (root + subcommand), `--version`, happy paths, and usage errors via in-process `main([...])` + `capsys` + `pytest.raises(SystemExit)`, plus one subprocess `python -m <package>` smoke test (and JSON, non-TTY, or bad-config cases when supported).

## CLI resources

- [init-cli.py](templates/init-cli.py) and [main.py](templates/main.py): CLI implementation and module entry point.
- [test_smoke.py](templates/test_smoke.py) and [test_cli.py](templates/test_cli.py): import and CLI contract tests.

## Gotchas

- **`help` vs `description`**: `add_parser(name, help=...)` populates parent list summaries (omit `help` to hide internal commands); `description` renders on `<cmd> --help`.
- **Subparser slot**: `add_subparsers(title="commands", metavar="COMMAND", required=True)` replaces `{a,b,c}` noise and exits `2` on bare group calls (use `required=False` + help handler if bare group should exit `0`).
- **Distinct `dest` names**: subparsers overwrite parent namespace keys — never reuse a root option's `dest` on a subcommand.
- **Short flags & `metavar`**: pass `"-n", "--limit"` (`dest` derives from `--limit`) and set `metavar` (`--since WHEN`).
- **Env defaults & colors**: build parsers inside `main()` reading `os.environ.get("APP_CONFIG") or None` (named in `help`). Python `3.14+` colors TTY help/errors (`NO_COLOR`, `FORCE_COLOR`, `PYTHON_COLORS`) — set `NO_COLOR=1` and strip forcing vars in tests.
- **Formatting, completions, & TUIs**: use `RawDescriptionHelpFormatter` (or paragraph-splitting `_fill_text`) for multi-paragraph text. Add `argcomplete` or `rich`/`textual` (with markup/highlighting/emoji disabled on untrusted text) only for interactive human UIs, never agent CLIs.
- **Fast startup**: profile via `uv run python -X importtime -c 'import <package>' 2> importtime.log` and lazy-import heavy SDKs inside handlers (or declare module-level `__lazy_modules__ = [...]` on Python `3.15+`, ignored safely on `<3.15`, unlike `lazy import` syntax).

## Existing Typer CLIs

Keep locked Typer unless asked to migrate:

- **Bundled skill (`0.25.1+`)**: read `typer/.agents/skills/typer/SKILL.md` from `.venv/`.
- **Pin minor (`typer>=0.N,<0.N+1`)**: `0.x` minors break APIs (`0.29` changed `get_error_hint()`); install `typer` directly (`typer-slim`/`typer-cli` deprecated; Click vendored since `0.26.0`, so use `typer.testing.CliRunner`).
- **Group callback & plain help**: add `@app.callback()` so single-command apps keep subcommand shape and `no_args_is_help=True` works; set `rich_markup_mode=None` when plain piped help is required (`GITHUB_ACTIONS`/`FORCE_COLOR`/`PY_COLORS` override `NO_COLOR` on Rich panels).

## Documentation

- [argparse](https://docs.python.org/3/library/argparse.html) · [tutorial](https://docs.python.org/3/howto/argparse.html) · [CPython changelog](https://docs.python.org/3/whatsnew/changelog.html) · [Typer releases](https://typer.tiangolo.com/release-notes/)
