# Mise Task Conventions

## Subtask Naming

Split a task into `<task>:<x>` when one piece must run alone; each family keys `<x>` off a different noun:

- **`format:<input>`**: the source family formatted — `format:go`, `format:python`, `format:templ`; `format:dprint` for JSON, Markdown, TOML, and YAML.
- **`build:<output>`**: the artifact produced — `build:go` (binary), `build:templ` (Templ to Go), `build:css`, `build:js`, `build:docs`, `build:image` (OCI image).
- **`check:<concern>`**: the property verified, identical across languages so `mise run check:lint` means the same everywhere; the names are fixed:

| Task            | Concern                          | Tool                                                            |
| --------------- | -------------------------------- | --------------------------------------------------------------- |
| `check:format`  | formatting drift                 | `dprint check` plus the stack formatter's check mode            |
| `check:lint`    | lint rules                       | `golangci-lint`, `ruff`, Biome                                  |
| `check:types`   | static types                     | `ty`, `tsc --noEmit`                                            |
| `check:vuln`    | dependency CVEs                  | `govulncheck`, `uv audit`, `pnpm audit`                         |
| `check:leaks`   | committed secrets                | [gitleaks](../gitleaks/SKILL.md)                                |
| `check:scan`    | IaC and config misconfigurations | [trivy](../trivy/SKILL.md)                                      |
| `check:actions` | workflow lint and audit          | `actionlint` + [zizmor](../zizmor/SKILL.md)                     |
| `check:sast`    | insecure code patterns (opt-in)  | [opengrep](../opengrep/SKILL.md), only when a project adopts it |

Those names are reserved: never respell one (`check:audit`, `check:dprint`) when the table already covers the concern. A stack adds a name only for a concern the table has none for, and the shipped set is closed: `check:deps` (unused files and dependencies), `check:doc` (document compiles), `check:pkg` (publishable surface), `check:site` (site builds clean), `check:validate` (configuration syntax). In a polyglot repository such as the dot repository root, a concern that repeats per language may split by language (`check:go`, `check:python`, `check:shell`), while a genuinely shared concern keeps its cross-language name (`check:format` for the one dprint check). Aliases are best-effort: a repository that already spends `f`, `t`, or `i` keeps them; the task names are the contract.

## Conventions

- **Hooks**: see [lefthook](../lefthook/SKILL.md); each hook command is `mise run <task>` and its name mirrors the task.
- **Parallel checks**: `check` fans out with `depends = ["check:format", "check:lint", "check:types", "check:vuln"]`; mise runs the subtasks concurrently.
- **Incremental tasks**: declare `sources` and `outputs` so mise skips a task whose inputs are unchanged (ideal for builds).
- **Staged vs whole-tree**: only formatters take `{staged_files}`; `check` and `test` always run on the whole tree.
- **Argument passthrough**: mise appends CLI args to the last command; use `raw_args = true` and a script forwarding `"$@"` when several commands consume the same file list, or `usage` for structured arguments.
- **Dotenv**: `[env]` with `_.file = ".env"` auto-loads the file.

## Tool Management

```bash
mise registry <name>     # discover the tool's backend id
mise use <tool>@latest   # pin into [tools] and install
mise install             # install everything pinned
mise lock                # refresh metadata for the locked versions
mise lock --bump         # advance fuzzy selectors without installing
mise lock --upgrade      # migrate legacy locks to request-specific bindings
mise upgrade --bump      # bump pinned versions (updates mise.lock too)
```

## Additional task gotchas

- **Full gate on a dirty tree**: `mise run all` write-formats the whole tree; when unrelated changes are present, run it in an isolated working-tree copy containing the candidate edits or fall back to `mise run check` and `mise run test`.
- **Trust**: in normal mode `mise run`, `mise install`, `mise exec`, and `mise watch` trust the active config automatically; `mise trust` is only needed for other commands or in paranoid mode.
- **Fail fast in hooks**: set `run_auto_install = false` under `[settings.task]` so a missing tool errors instead of installing silently.
- **Non-interactive scripts**: pass `-y` (`mise install -y`) in scripts and CI steps that would otherwise prompt.
- **Keep project config project-local**: never symlink a repository's `mise.toml` into `~/.config/mise/conf.d/`; mise then treats it as global, `mise lock` reports `No tools configured to lock`, and its tasks leak everywhere.
- **Task `dir`**: pin `[task_config] dir = "{{config_root}}"` when inherited configs could select another project root; verify tasks from both the repository root and a subdirectory.

