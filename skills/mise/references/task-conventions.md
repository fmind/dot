# Mise Task Conventions

## Subtask Naming

Split a task into `<task>:<x>` when one piece must run alone; each family keys `<x>` off a different noun:

- **`format:<input>`**: the source family formatted — `format:python` for Python; `format:dprint` for JSON, Markdown, TOML, and YAML.
- **`build:<output>`**: the artifact produced — `build:package`, `build:docs`, or `build:image` (OCI image).
- **`check:<concern>`**: the property verified, identical across languages so `mise run check:lint` means the same everywhere; the names are fixed:

| Task            | Concern                          | Tool                                                          |
| --------------- | -------------------------------- | ------------------------------------------------------------- |
| `check:deps`    | missing or unused dependencies   | `deptry`                                                      |
| `check:format`  | formatting drift                 | `dprint check` plus the stack formatter's check mode          |
| `check:lint`    | lint rules                       | `ruff check`                                                  |
| `check:types`   | static types                     | `ty check`                                                    |
| `check:vuln`    | dependency CVEs                  | `uv audit`                                                    |
| `check:leaks`   | working-tree secrets             | [betterleaks](../../code-security/references/betterleaks.md)  |
| `check:scan`    | IaC and config misconfigurations | [trivy](../../code-security/references/trivy/GUIDE.md)        |
| `check:actions` | workflow lint and audit          | [jactionlint](../../github-actions/references/jactionlint.md) |

Reuse these names for their stated concerns instead of inventing synonyms such as `check:audit` or `check:dprint`. Add a repository-specific name when no existing concern fits, such as `check:docs`, `check:skills`, `check:pkg`, `check:site`, or `check:validate`; preserve established names unless a migration has a concrete benefit. A repository with multiple source families may split a repeated concern (`check:python`, `check:shell`), while a shared concern keeps its common name (`check:format` for the one dprint check). Aliases are best-effort: a repository that already spends `f`, `t`, or `i` keeps them; the task names are the contract.

## Conventions

- **Fan checks out in parallel**: `check` depends on `check:local` (offline checks such as `check:deps`, `check:format`, `check:leaks`, `check:lint`, `check:types`) and `check:network` (database downloads: `check:vuln`, `check:scan`); mise runs the subtasks concurrently, and the [lefthook](../../github-actions/references/lefthook.md) hooks, which own job naming and staged-file rules, run `check:local` in pre-commit and `check:network` in pre-push.
- **Skip unchanged tasks incrementally**: declare `sources` and `outputs` so mise skips a task whose inputs are unchanged (ideal for builds).
- **Forward arguments without dispatch wrappers**: without `usage`, mise appends CLI args to the last command (`format:dprint` passes `{staged_files}` directly without shell evaluation); verify raw argument behavior with a small local example when adding a wrapper task. When a formatter must run several commands on the same files (`format:python`) or supply a non-root default path, declare `usage = 'arg "[files]..."'` (plus `default=` for one path) and start its script with `eval "set -- $usage_files"`: mise passes variadic arguments as one shell-quoted string. One task then serves both the hook and ordinary formatting; never add per-hook `:files` variants.

## Concise Output

Prefer native output controls for frequently run tasks. Under `[settings.task]`, `quiet = true` suppresses mise's command echoes while preserving child stdout/stderr and task prefixes; `MISE_TASK_QUIET=false mise run <task>` restores execution messages. Quiet also hides the dry run of `mise run -n <task>`, so prefix it with `MISE_TASK_QUIET=false` to print the resolved command. Leave the output style unchanged so parallel diagnostics retain task attribution. Avoid `silent`, discarded stderr, and truncation pipelines that hide failures or change exit status.

Keep test counts, coverage totals and thresholds, warnings, and actionable findings visible. For pytest-cov with a positive `fail_under`, `--cov-report=` hides the per-file table while retaining the total and enforcing the threshold. Expose `report:coverage` to read the saved coverage data without rerunning tests; run tests again if those data are stale. For Betterleaks, `--no-banner` removes decoration; retain `--verbose --redact=100` for finding locations and redacted evidence.

Validate success and intentional failure cases before adopting quieter defaults, including coverage below its threshold and scanner findings. Compare output with the same tokenizer and record exit codes and diagnostic completeness; output-token reductions alone do not prove billing savings.

## Tool Management

The [tool version rules](tool-versions.md#select-exact-versions) own selecting and recording exact pins; [upgrade-tools](../../upgrade-tools/SKILL.md) owns upgrades.

## Additional task gotchas

- **Fail fast in hooks**: set `run_auto_install = false` under `[settings.task]` so a missing tool errors instead of installing silently.
- **Keep project config project-local**: never symlink a repository's `mise.toml` into `~/.config/mise/conf.d/`; mise then treats it as global, `mise lock` reports `No tools configured to lock`, and its tasks leak everywhere.
- **Task `dir`**: pin `[task_config] dir = "{{config_root}}"` when inherited configs could select another project root; verify tasks from both the repository root and a subdirectory.
- **Keep a TTY with redacted `.env`**: `_.file = { path = ".env", redact = true }` pipes `stdout`/`stderr` through the redactor and sets `stdin` to `Stdio::null()` once `.env` exists; set `raw = true` on interactive login and live TUI tasks so they keep the terminal.
