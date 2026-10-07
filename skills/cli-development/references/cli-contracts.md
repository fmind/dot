---
name: cli-contracts
description: "Command, flag, stream, exit-code, and JSON interface design."
---

# CLI Contracts

Define a command-line interface as a stable human and machine contract before implementing it. [typer](typer/GUIDE.md) owns Python CLI implementation; [systematic-debugging](../../systematic-debugging/SKILL.md) owns unknown failures.

## Defaults for new CLIs

Apply these defaults where the feature exists; a small utility does not need configuration, JSON, or prompting just to fill a checklist. Existing public contracts take precedence for command shape, streams, exit statuses, and output formats; the Help and version side-effect rules, Interaction consent rules, markup escaping, and Errors redaction apply to every CLI, existing or new.

- **Command shape**: an explicit group for a growing toolbox; a single command for one focused job. Decide before publishing because Typer otherwise changes syntax when a second command appears.
- **Help and version**: `-h` / `--help` at root and subcommands; eager root `--version`. Derive help, examples, deprecations, and shell completions from the same command definition. Both work before application setup: without credentials, network access, or valid configuration, and without operational side effects. Explicit help exits 0; help accompanying a usage error keeps a nonzero status (empty Typer groups show help on stdout and exit 2).
- **Streams**: requested data to stdout; progress, diagnostics, and safe errors to stderr. Quiet success is appropriate for commands with nothing to return.
- **Verbosity**: `-v` / `--verbose` adds progress details to stderr; it never enables raw exception dumps or changes stdout's data contract.
- **Configuration**: explicit flags > application-prefixed environment variables > configuration file > built-in defaults. Validate only when the selected command needs configuration.
- **Machine output**: `--json` emits one documented, schema-stable JSON object with no Rich rendering or decoration. On failure, leave stdout empty, print a safe error to stderr, and exit nonzero. Define partial-result and schema-version behavior before adding them.
- **Exit statuses**: 0 success, 2 invalid usage, 1 operational failure. Document cancellation and any additional codes; keep them consistent across commands.
- **Terminal behavior**: detect TTY status independently for stdout and stderr; disable color and animations on redirected streams by default, honor nonempty `NO_COLOR` and `TERM=dumb`, and document any explicit color override. Keep pagers interactive and provide a way to disable them. Print external text literally, including brackets and emoji-like names: escape it before interpolating into markup, or disable markup and emoji interpretation, and apply styles separately.
- **Interaction**: provide non-interactive inputs for every required value. Never prompt on non-TTY input; when prompting is disabled or stdin is not a TTY, fail clearly on missing inputs without reading prompts from piped data. When prompts exist, `--no-input` disables them and never implies consent; `--yes` confirms only the documented action and does not bypass validation or authorization. A destructive command needs a confirmation or an explicit non-interactive opt-in such as `--yes`.
- **Errors**: actionable, sanitized messages by default, showing safe command and argument context, never collected values, tokens, provider response bodies, or unredacted stderr. Catch expected failures at the command boundary with specific recovery advice; preserve causes internally without displaying raw exception strings. Hidden locals do not sanitize exception text, source excerpts, causes, or provider responses. Tracebacks require an explicit diagnostic mode and a redaction policy.
- **Completion**: packaged tools keep shell completion enabled and test generation in fresh processes. Standalone scratch scripts may disable it.

## Workflow

1. **Specify inputs**: positional arguments, flags, environment variables, config precedence, defaults, validation, and mutual exclusions. Avoid secrets in command arguments because shell history and process listings can expose them; use a credential store, protected file, hidden interactive prompt, or explicit stdin input appropriate to the command.
1. **Apply the defaults** above for help, streams, terminal output, interaction, and errors; enforce the consent and redaction rules even when preserving an existing contract.
1. **Bound result volume**: for large listings, support focused filters, field selection, and explicit limits where useful; retain counts, continuation tokens, and incomplete-result status. Make detail opt-in and provide file export for large reports. Compact JSON alone does not reduce the number of records; quiet modes must retain actionable errors and exit codes.
1. **Test the contract**: cover parsing, validation, streams, exit codes, JSON schema, cancellation, and representative success and failure paths. Include help with broken configuration and no credentials, non-TTY missing inputs, `--no-input` without consent, redirected and color-disabled output, and empty, partial, and failed JSON results; then run `mise run check` and `mise run test`.
1. **Exercise the installed binary**: from a clean shell, piped and non-TTY; direct function tests alone do not prove the contract.

## Documentation

- [Command Line Interface Guidelines](https://clig.dev)
- [NO_COLOR convention](https://no-color.org/)
- Companion skills: [typer](typer/GUIDE.md) (Python CLIs), [systematic-debugging](../../systematic-debugging/SKILL.md) (failures of unknown cause).
