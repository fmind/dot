---
name: argparse
description: "Design CLI contracts (streams, exits, JSON) and build argparse or Cyclopts CLIs."
---

# CLI Contracts & Python CLIs

Define a stable human + machine CLI contract in any language, and build Python CLIs with `argparse` or [Cyclopts](references/cyclopts.md) when typed command trees outgrow stdlib boilerplate ([foundation](../foundation/GUIDE.md) owns packaging; existing CLIs keep their framework).

## Defaults for new CLIs

Existing public contracts govern shape, streams, exit codes, and formats; side-effect-free help/version, consent, markup escaping, and error redaction apply universally:

- **Shape, help, & version**: explicit subcommands for toolboxes, single command for one focused job. `-h`/`--help` (root + subcommands) and eager `--version` work without credentials, network, config, or side effects (`0` on explicit help; `2` + stderr usage on invalid args or bare command groups unless defined as help).
- **Streams, exits, & JSON**: data on stdout; progress, diagnostics, and sanitized recovery errors on stderr (`-v`/`--verbose` adds stderr progress only, never raw tracebacks or secrets). Exits: `0` success, `2` usage, `1` operational failure, `130` on `SIGINT`/`KeyboardInterrupt` (exit cleanly on `BrokenPipeError` under `| head`). `--json` emits one schema-stable JSON object on stdout (empty stdout + stderr error + non-zero exit on failure); bound large output via filters/limits/cursors and support `-` for stdin/stdout where natural.
- **Secrets, config, & XDG**: pass secrets via stores, protected files, hidden TTY prompts, or stdin (never CLI args); precedence is flags > `<APP>_*` env > project config > user config > defaults (validated lazily per command). Store user state under XDG directories (`XDG_CONFIG_HOME`, `XDG_STATE_HOME`, `XDG_CACHE_HOME`; add `platformdirs` only when cross-platform paths outgrow a small stdlib helper).
- **TTY, color, & safety**: detect stdout/stderr TTY separately, honor `NO_COLOR`/`TERM=dumb`, disable spinners/pagers on pipes, escape untrusted markup, expose flags for all required inputs, never prompt on non-TTY stdin (`--no-input`), and require `-n`/`--dry-run` plus confirmation or `--yes` on destructive/mutating actions.

## Workflow

1. **Bootstrap**: follow [bootstrap](references/bootstrap.md) for packaged CLIs, or [script](../script/GUIDE.md) for single-file scripts.
1. **Isolate `Namespace` at the boundary**: build parsers in `build_parser()`, bind subparsers via `set_defaults(handler=...)`, and unpack untyped `args` into typed handler arguments (`lambda args: greet(name=args.name)`) or a dataclass so `ty check` verifies call sites. Pass `allow_abbrev=False` and `suggest_on_error=True` (`3.14+`) on every parser.
1. **Fail invalid input with exit `2`**: use `choices`, `type`, `nargs`, `required`, and `parser.error(...)` (exits `2` with stderr usage, never `1`).
1. **Test streams & exit codes**: assert stdout, stderr, and exits (`0`/`1`/`2`) across `-h`/`--help` (including broken config / no credentials), `--version`, happy paths, usage errors, non-TTY/`--no-input`, piped/`NO_COLOR`, and JSON schemas via in-process `main([...])` + `capsys` + `pytest.raises(SystemExit)`, plus one `python -m <package>` subprocess smoke test (and fresh-shell completions when shipped).

## Gotchas

- **`help` vs `description` & subparsers**: `add_parser(name, help=...)` fills parent summaries (omit `help` to hide internal commands; `description` renders on `<cmd> --help`). `add_subparsers(title="commands", metavar="COMMAND", required=True)` avoids `{a,b,c}` noise and exits `2` on bare groups; never reuse a root option's `dest` on a subcommand.
- **Flags, env defaults, & colors**: pass `"-n", "--limit"` with `metavar`, and build parsers inside `main()` reading `os.environ.get("APP_CONFIG") or None` (named in `help`). Python `3.14+` colors TTY help/errors (`NO_COLOR`, `FORCE_COLOR`, `PYTHON_COLORS`)—set `NO_COLOR=1` and strip forcing vars in tests.
- **Formatting, TUIs, & startup**: use `RawDescriptionHelpFormatter` for multi-paragraph help; add `argcomplete` or `rich`/`textual` (markup/highlighting/emoji disabled on untrusted text) only for interactive human UIs, never agent CLIs. Profile startup via `uv run python -X importtime -c 'import <package>'` and lazy-import heavy SDKs in handlers (or `__lazy_modules__ = [...]` on `3.15+`).

## Documentation

- [argparse](https://docs.python.org/3/library/argparse.html) · [Command Line Interface Guidelines](https://clig.dev) · [NO_COLOR](https://no-color.org/) · [Cyclopts](references/cyclopts.md)
