---
name: argparse
description: "Python CLI code with standard-library argparse: commands, help, usage errors, tests; existing Typer CLIs."
---

# Python CLIs With argparse

Build Python CLIs on `argparse`: a CLI parses arguments and prints text, so it needs no runtime dependency. [cli-contracts](../cli-contracts.md) owns command behavior and [foundation](../foundation/GUIDE.md) owns packaging. An existing Typer or Click CLI keeps its framework; see [Existing Typer CLIs](#existing-typer-clis).

## Workflow

1. **Start from the starter**: a new packaged CLI follows [bootstrap](references/bootstrap.md) after the shared Python foundation and applies the [CLI defaults](../cli-contracts.md#defaults-for-new-clis); a single file follows [python-script](../python-script/GUIDE.md).
1. **Define the tree in one function and keep `Namespace` at the edge**: `build_parser()` creates the root parser, one subparser per command, and binds each handler with `set_defaults(handler=...)`; `main()` parses, then calls `args.handler(args)`. Because `argparse.Namespace` attributes are untyped `Any`, unpack `args` at the handler boundary into typed function parameters (`lambda args: greet(name=args.name)`) or a typed dataclass so `ty check` verifies parameter names and types. Construct every parser with `allow_abbrev=False` (a prefix such as `--ver` must not match silently) and `suggest_on_error=True` (Python 3.14+: a typo names the closest command or choice).
1. **Validate at the parser**: declare `choices`, `type`, `nargs`, and `required` so argparse rejects bad input with exit 2 before any work starts. Report a combination argparse cannot express with `parser.error("--since: must not be after --until")`, which prints the usage line and exits 2; never return 1 for a usage mistake.
1. **Cover help, streams, and exit codes**: test `-h` and `--help` at the root and on a command, `--version`, a successful command, an unknown option, a missing value, and a missing command, asserting stdout, stderr, and the exit code separately. Call `main([...])` in-process with `capsys` and `pytest.raises(SystemExit)`; run the module entry point once in a subprocess. Add JSON, non-TTY prompt, and broken-configuration cases when those features exist.

## CLI resources

- [init-cli.py](templates/init-cli.py) supplies the application; [main.py](templates/main.py) supplies the module entry point.
- [test_smoke.py](templates/test_smoke.py) and [test_cli.py](templates/test_cli.py) exercise imports and command behavior.

## Gotchas

- **Give every command `help` and `description`**: `add_parser(name, help=...)` sets the one-line summary in the parent's list; the command's own `--help` shows `description`. A command without `help` is hidden from the list but still runs, which suits internal commands.
- **Name the command slot**: `add_subparsers(title="commands", metavar="COMMAND", required=True)` prints `COMMAND` in usage instead of the whole `{a,b,c}` set and makes a bare group a usage error (exit 2, usage on stderr). Use `required=False` plus a default handler that prints help when a bare group should exit 0.
- **Keep parent and command destinations distinct**: a subparser copies its whole namespace over the parent's, so a command option with the same `dest` as a root option hides the root value, even when only the root one was passed.
- **Put short flags first**: `add_argument("-n", "--limit")` prints `-n, --limit`; the destination still comes from the first long flag. Set `metavar` on value options (`--since WHEN`), or help shows the upper-cased destination.
- **Read environment defaults yourself**: argparse has no environment binding. Use `default=os.environ.get("APP_CONFIG") or None`, name the variable in the help text, and build the parser inside `main()` so tests can change the environment.
- **Colors follow the terminal**: Python 3.14 colors help and errors on a TTY and honors `NO_COLOR`, `FORCE_COLOR`, and `PYTHON_COLORS`. Tests set `NO_COLOR=1` and drop the forcing variables, or assertions on help text fail in CI.
- **Wrap help for the reader**: argparse wraps at the terminal width (80 columns when piped) and joins a multi-paragraph `description` or `epilog` into one. Pass `formatter_class=argparse.RawDescriptionHelpFormatter` to keep preformatted line breaks, or override `HelpFormatter._fill_text` on `text.split("\n\n")` to keep paragraph breaks while wrapping lines.
- **Add completion only for people**: argparse generates no shell completion. Agents do not need it; when people use the tool interactively, add `argcomplete` or answer a completion callback from the same parser.
- **Add Rich or Textual only for human interfaces**: standard and agent-facing CLIs stay on plain stdout/stderr and JSON. Add `rich` (with markup, highlighting, and emoji disabled on external data) or `textual` only when a human-facing tool requires live tables, progress bars, or an interactive TUI.
- **Keep agent-invoked startup cheap**: profile imports with `uv run python -X importtime -c 'import <package>' 2> importtime.log` and import heavy SDKs inside the handlers that use them; on Python 3.15+ a module-level `__lazy_modules__ = ["<module>", ...]` defers those imports and older interpreters ignore it, whereas `lazy import` syntax fails to parse before 3.15.

## Existing Typer CLIs

Keep Typer where it is already locked; migrate to argparse only when the owner asks. While it stays:

- **Read the locked release's bundled skill**: Typer 0.25.1+ wheels ship the official skill at `typer/.agents/skills/typer/SKILL.md` in the installed package; read that version-matched copy.
- **Cap the minor**: Typer is 0.x and removes APIs in minors (0.29 dropped the context argument of `get_error_hint()`); pin `typer>=0.N,<0.N+1` and review each bump.
- **Install `typer` alone**: `typer-slim` and `typer-cli` are deprecated. Typer vendors Click since 0.26.0, so use `typer.testing.CliRunner` and do not assume external Click classes or extensions interoperate with its command objects.
- **Fix the group shape with a callback**: Typer promotes a sole command to the root unless a callback fixes the group shape, and `Typer(no_args_is_help=True)` is inert until the app has a callback, a sub-app, or a second command.
- **Parse help panels when walking commands**: default Typer help draws boxed panels even when piped, and `GITHUB_ACTIONS`, `FORCE_COLOR`, or `PY_COLORS` force color despite `NO_COLOR`; only `rich_markup_mode=None` prints plain help.

## Documentation

- [argparse](https://docs.python.org/3/library/argparse.html) · [argparse tutorial](https://docs.python.org/3/howto/argparse.html)
- Releases: [CPython changelog](https://docs.python.org/3/whatsnew/changelog.html) · [Typer release notes](https://typer.tiangolo.com/release-notes/)
