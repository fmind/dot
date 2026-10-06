# Mise Task Conventions

## Subtask Naming

Split a task into `<task>:<x>` when one piece must run alone; each family keys `<x>` off a different noun:

- **`format:<input>`**: the source family formatted — `format:python` for Python; `format:dprint` for JSON, Markdown, TOML, and YAML.
- **`build:<output>`**: the artifact produced — `build:package`, `build:docs`, or `build:image` (OCI image).
- **`check:<concern>`**: the property verified, identical across languages so `mise run check:lint` means the same everywhere; the names are fixed:

| Task            | Concern                          | Tool                                                               |
| --------------- | -------------------------------- | ------------------------------------------------------------------ |
| `check:format`  | formatting drift                 | `dprint check` plus the stack formatter's check mode               |
| `check:lint`    | lint rules                       | `ruff check`                                                       |
| `check:types`   | static types                     | `ty check`                                                         |
| `check:vuln`    | dependency CVEs                  | `uv audit`                                                         |
| `check:leaks`   | working-tree secrets             | [gitleaks](../../code-security/references/gitleaks.md)             |
| `check:scan`    | IaC and config misconfigurations | [trivy](../../code-security/references/trivy/GUIDE.md)             |
| `check:actions` | workflow lint and audit          | `actionlint` + [zizmor](../../github-actions/references/zizmor.md) |

Reuse these names for their stated concerns instead of inventing synonyms such as `check:audit` or `check:dprint`. Add a repository-specific name when no existing concern fits, such as `check:docs`, `check:skills`, `check:pkg`, `check:site`, or `check:validate`; preserve established names unless a migration has a concrete benefit. A repository with multiple source families may split a repeated concern (`check:python`, `check:shell`), while a shared concern keeps its common name (`check:format` for the one dprint check). Aliases are best-effort: a repository that already spends `f`, `t`, or `i` keeps them; the task names are the contract.

## Conventions

- **Run hooks through mise tasks**: see [lefthook](../../github-actions/references/lefthook.md); each hook command is `mise run <task>` and its name mirrors the task.
- **Fan checks out in parallel**: `check` fans out with `depends = ["check:format", "check:lint", "check:types", "check:vuln"]`; mise runs the subtasks concurrently.
- **Skip unchanged tasks incrementally**: declare `sources` and `outputs` so mise skips a task whose inputs are unchanged (ideal for builds).
- **Limit staged files to formatters**: only formatters take `{staged_files}`; `check` and `test` always run on the whole tree.
- **Forward arguments without dispatch wrappers**: mise appends CLI args to the last command. When two tools need the same staged files, give each a direct task and invoke them sequentially from hooks; keep a whole-tree aggregate for ordinary formatting. Use `usage` only for a real argument contract; do not add shell argument dispatch.
- **Keep complex logic out of TOML**: short command arrays and small setup/cleanup sequences are acceptable. Prefer native flags to conditions and explicit tasks to mode detection. Do not wrap commands in `bash -c` or `sh -c`, compress a program onto one line, or relocate a large shell block into TOML. Keep unavoidable branching, retries, and response parsing in maintained source.

## Concise Output

Prefer native output controls for frequently run tasks. Under `[settings.task]`, `quiet = true` suppresses mise's command echoes while preserving child stdout/stderr and task prefixes; `MISE_TASK_QUIET=false mise run <task>` restores execution messages. Leave the output style unchanged so parallel diagnostics retain task attribution. Avoid `silent`, discarded stderr, and truncation pipelines that hide failures or change exit status.

Keep test counts, coverage totals and thresholds, warnings, and actionable findings visible. For pytest-cov with a positive `fail_under`, `--cov-report=` hides the per-file table while retaining the total and enforcing the threshold. Expose `report:coverage` to read the saved coverage data without rerunning tests; run tests again if those data are stale. For Gitleaks, `--no-banner` removes decoration; retain `--verbose --redact=100` for finding locations and redacted evidence.

Validate success and intentional failure cases before adopting quieter defaults, including coverage below its threshold and scanner findings. Compare output with the same tokenizer and record exit codes and diagnostic completeness; output-token reductions alone do not prove billing savings. Extend to other repositories after measuring the first adoption.

## Tool Management

The [tool version rules](tool-versions.md#select-exact-versions) own selecting and recording exact pins; [upgrade-tools](../../upgrade-tools/SKILL.md) owns upgrades.

```bash
mise registry <name>     # discover the tool's backend id
mise install             # install everything pinned
mise lock                # refresh metadata for the locked versions
mise lock --bump         # advance lock selectors without installing
mise lock --upgrade      # migrate legacy locks; retain and validate generated dependency files
mise upgrade --bump      # explicit upgrade of this project's pins
```

## Additional task gotchas

- **Dotenv and dirty trees**: the [mise gotchas](../SKILL.md#gotchas) own dotenv loading and the full gate on a tree with unrelated changes.
- **Run `mise trust` only when needed**: in normal mode `mise run`, `mise install`, `mise exec`, and `mise watch` trust the active config automatically; `mise trust` is only needed for other commands or in paranoid mode.
- **Fail fast in hooks**: set `run_auto_install = false` under `[settings.task]` so a missing tool errors instead of installing silently.
- **Non-interactive scripts**: pass `-y` (`mise install -y`) in scripts and CI steps that would otherwise prompt.
- **Keep project config project-local**: never symlink a repository's `mise.toml` into `~/.config/mise/conf.d/`; mise then treats it as global, `mise lock` reports `No tools configured to lock`, and its tasks leak everywhere.
- **Task `dir`**: pin `[task_config] dir = "{{config_root}}"` when inherited configs could select another project root; verify tasks from both the repository root and a subdirectory.
