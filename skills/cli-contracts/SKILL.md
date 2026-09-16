---
name: cli-contracts
description: Design a CLI's command, flag, stream, exit-code, and JSON contract before coding it. Use when adding or changing a CLI surface.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/cli-contracts
  created: "2026-08-30"
  updated: "2026-09-16"
---

# CLI Contracts

Define a command-line interface as a stable human and machine contract before implementing it. [typer](../typer/SKILL.md) owns Python CLI implementation; [systematic-debugging](../systematic-debugging/SKILL.md) owns unknown failures.

## Workflow

1. **Name the jobs**: one purpose per command, a predictable noun-verb hierarchy, and aliases only when they cannot trigger a different class of action.
1. **Specify inputs**: positional arguments, flags, environment variables, config precedence, defaults, validation, and mutual exclusions. Avoid secrets in command arguments because shell history and process listings can expose them; use a credential store, protected file, hidden interactive prompt, or explicit stdin input appropriate to the command.
1. **Make automation explicit**: provide non-interactive inputs for every required value; when prompting is disabled or stdin is not a TTY, fail clearly on missing inputs without reading prompts from piped data. `--no-input` disables prompts; it never implies consent. `--yes` confirms only the documented action and does not bypass validation or authorization.
1. **Separate streams**: requested data to stdout, diagnostics and progress to stderr; `--json` stays machine-readable, schema-stable, and free of decoration.
1. **Specify machine output**: choose one JSON document or an explicitly documented record stream; define stdout and stderr for empty results, partial results, and failures, including failures before command execution. Specify whether failures leave stdout empty or emit structured errors, how partial data is marked, and how consumers identify breaking schema changes.
1. **Adapt terminal output**: detect TTY status independently for stdout and stderr; disable color and animations on redirected streams by default, honor nonempty `NO_COLOR` and `TERM=dumb`, and document any explicit color override. Never decorate machine output; keep pagers interactive and provide a way to disable them.
1. **Define outcomes**: map success, usage errors, authentication failures, remote failures, partial results, and cancellation to documented exit codes; never turn an error into an empty success.
1. **Make help reliable**: derive root and subcommand help, examples, deprecations, and shell completions from the same command definition. Help and `--version` must work without credentials, network access, or valid application configuration, and without operational side effects. Explicit help exits successfully; help accompanying a usage error keeps a nonzero exit status.
1. **Protect sensitive context**: errors show safe command and argument context, never collected values, tokens, provider response bodies, or unredacted stderr.
1. **Handle process behavior**: respect signals, cancellation, timeouts, piping, broken pipes, and cleanup; a destructive command needs a confirmation or an explicit non-interactive opt-in such as `--yes`.
1. **Preserve compatibility deliberately**: command names, flags, JSON fields, exit codes, and script-consumed stdout are public API; prefer deprecation and migration guidance over silent changes.
1. **Test the contract**: cover parsing, validation, streams, exit codes, JSON schema, cancellation, and representative success and failure paths. Include help with broken configuration and no credentials, non-TTY missing inputs, `--no-input` without consent, redirected and color-disabled output, and empty, partial, and failed JSON results; then run `mise run check` and `mise run test`.
1. **Exercise the installed binary**: from a clean shell, piped and non-TTY; direct function tests alone do not prove the contract.

## Documentation

- [Command Line Interface Guidelines](https://clig.dev)
- [NO_COLOR convention](https://no-color.org/)
- Companion skills: [typer](../typer/SKILL.md) (Python CLIs), [systematic-debugging](../systematic-debugging/SKILL.md) (failures of unknown cause).
