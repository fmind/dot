---
name: cli-contracts
description: "Design any CLI's commands, flags, streams, exit codes, and JSON output, in any language."
---

# CLI Contracts

Define a stable human + machine CLI contract before coding, in any language; [argparse](argparse/GUIDE.md) owns Python implementation.

## Defaults for new CLIs

Apply where relevant (small tools need no forced config, JSON, or prompts). Existing public contracts take precedence for shape, streams, exit codes, and formats, while side-effect-free help/version, consent, markup escaping, and error redaction apply to every CLI.

- **Command shape**: explicit subcommand group for growing toolboxes; single command for one focused job (adding subcommands later breaks single-command syntax).
- **Help & version**: `-h`/`--help` (root + subcommands) and eager root `--version` derived from one definition, working without credentials, network, valid config, or side effects. Explicit help exits `0`; usage errors (including bare command groups unless defined as help) print usage to stderr and exit `2`.
- **Streams & verbosity**: requested data on stdout; progress, diagnostics, and sanitized errors on stderr (quiet success when nothing is returned). `-v`/`--verbose` adds stderr progress only — never raw tracebacks or altered stdout contracts.
- **Secrets & config**: never pass secrets in CLI args (visible in history/`ps`); read credential stores, protected files, hidden TTY prompts, or explicit stdin. Precedence: flags > `<APP>_*` env vars > config file > defaults (validated lazily per command).
- **Machine output & exits**: `--json` prints one schema-stable JSON object on stdout (empty stdout + stderr error + non-zero exit on failure; define partial/version fields upfront). Exit codes: `0` success, `2` invalid usage, `1` operational failure (document cancellation/extra codes).
- **TTY, escaping, & prompts**: detect stdout/stderr TTY separately, disable color/spinners on pipes, honor non-empty `NO_COLOR` and `TERM=dumb`, make pagers disableable, and escape or disable markup/emoji before rendering external strings. Provide flags for every required input; never prompt on non-TTY stdin; `--no-input` disables prompts without implying consent; destructive actions require confirmation or explicit `--yes` (which never bypasses validation/auth).
- **Sanitized errors & completions**: print actionable recovery context without secret values, tokens, provider bodies, or raw stderr (opt-in diagnostic tracebacks require a redaction policy). Add shell completions only for human-typed CLIs, tested in a fresh shell.

## Workflow

1. **Apply defaults** above (enforcing consent and redaction even on legacy CLIs).
1. **Bound output volume**: offer filters, field projection, limits, counts/cursors, incomplete-result markers, and file export for large outputs; keep errors and exit codes intact in quiet modes.
1. **Verify**: test parsing, streams, exit codes (`0`/`1`/`2`), JSON schema, cancellation, broken-config/no-credential `--help`, non-TTY missing inputs, `--no-input`, piped/`NO_COLOR` output, and clean-shell invocation (`mise run check && mise run test`).

## Documentation

- [Command Line Interface Guidelines](https://clig.dev) · [NO_COLOR](https://no-color.org/) · Companion: [argparse](argparse/GUIDE.md).
