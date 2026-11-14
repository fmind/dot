# Mise Task Conventions

## Task Vocabulary

| Task      | Alias | Purpose                                                                    |
| --------- | ----- | -------------------------------------------------------------------------- |
| `install` | `i`   | Sync dependencies and install Git hooks (`lefthook install`).              |
| `format`  | `f`   | Format all sources (`format:*`).                                           |
| `check`   | `c`   | Run all static checks in parallel (`check:*`).                             |
| `test`    | `t`   | Run the test suite.                                                        |
| `build`   | `b`   | Build or package artifacts (`build:*`).                                    |
| `watch`   | `w`   | Live reload or test watcher (omit when inapplicable).                      |
| `all`     | `a`   | `check`, `test`, `build` sequentially without rewriting files (full gate). |

## Subtask Naming

Split `<task>:<x>` only when parts run independently:

- **`format:<input>`**: source family (`format:python`, `format:dprint` for JSON/Markdown/TOML/YAML per [dprint](dprint.md), `format:shell` via `shfmt -w`).
- **`build:<output>`**: artifact (`build:package`, `build:docs`, `build:image`).
- **`check:<concern>`**: fixed cross-stack property names:

| Task            | Concern                                 | Tool                                                          |
| --------------- | --------------------------------------- | ------------------------------------------------------------- |
| `check:deps`    | missing or unused dependencies          | `deptry`                                                      |
| `check:format`  | formatting drift                        | `dprint check` plus stack formatter `--check` (`shfmt -d`)    |
| `check:lint`    | lint rules                              | `ruff check`                                                  |
| `check:types`   | static types                            | `ty check`                                                    |
| `check:vuln`    | dependency CVEs                         | `uv audit`                                                    |
| `check:leaks`   | working-tree secrets                    | [betterleaks](../../code-security/references/betterleaks.md)  |
| `check:scan`    | dependencies, IaC, images, and licenses | [trivy](../../code-security/references/trivy/GUIDE.md)        |
| `check:typos`   | source and doc spelling                 | `typos`                                                       |
| `check:links`   | broken Markdown or site links           | `lychee --offline --no-progress` (local) / `lychee`           |
| `check:shell`   | shell lint and formatting               | `shellcheck` + `shfmt`                                        |
| `check:actions` | workflow lint and audit                 | [jactionlint](../../github-actions/references/jactionlint.md) |

Reuse these exact names rather than synonyms (`check:audit`, `check:dprint`); add repo-specific names (`check:docs`, `check:skills`, `check:pkg`, `check:site`, `check:validate`) or source-family splits (`check:python`, `check:shell`) only for distinct concerns, and treat single-letter aliases as best-effort.

## Conventions

- **Parallelize offline vs network checks**: `check` depends on `check:local` (`check:deps`, `check:format`, `check:leaks`, `check:lint`, `check:types` — run in `pre-commit`) and `check:network` (`check:vuln`, plus `check:scan` when enabled — run in `pre-push`) per [lefthook](../../github-actions/references/lefthook.md).
- **Declare `sources` and `outputs`** on build tasks so unchanged inputs skip rebuilds.
- **Forward file arguments cleanly**: without `usage`, mise appends CLI args to the last command (`format:dprint` receives `{staged_files}` directly). Multi-command formatters (`format:python`) or custom default paths declare `usage = 'arg "[files]..."'` (plus `default=`) and begin with `eval "set -- $usage_files"` so one task serves both hooks and `mise run format` without `:files` duplicates.

## Concise Output

Set `[settings.task]` `quiet = true` to suppress command echoes while keeping child stdout/stderr and task prefixes (`MISE_TASK_QUIET=false` restores echoes and `mise run -n` dry-run output). Never use `silent`, discard stderr, or pipe through truncators that mask exit codes or diagnostics.

Keep test counts, coverage totals/thresholds, warnings, and findings visible: pass `--cov-report=` when `fail_under` is set (add `report:coverage` for full tables) and `--no-banner --verbose --redact=100` on Betterleaks. Verify both passing and failing runs (below-threshold coverage, intentional findings) before adopting quieter flags.

## Tool Management

[tool-versions.md](tool-versions.md#select-exact-versions) owns pin selection; [upgrade-tools](../../upgrade-tools/SKILL.md) owns upgrades.

## Additional task gotchas

- **Set `run_auto_install = false`** under `[settings.task]` so missing tools fail fast in hooks.
- **Never symlink project `mise.toml` into `~/.config/mise/conf.d/`**: mise treats `conf.d` files as global, breaking `mise lock` (`No tools configured to lock`) and leaking tasks globally.
- **Pin `[task_config] dir = "{{config_root}}"`** when parent configs exist, and test from both repo root and subdirectories.
- **Set `raw = true` for interactive tasks when redacting `.env`**: `_.file = { path = ".env", redact = true }` pipes output and nulls `stdin` once `.env` exists.
- **Query/edit YAML cleanly with `yq` v4**: read env safely via `strenv(VAR)` (`yq -i '.key = strenv(VAL)' file.yml`) rather than shell-interpolating expressions; add `--no-follow` / exclusions in `typos` only for vendored tokens.
