# Mise Task Conventions

## Task Vocabulary

| Task      | Alias | Purpose                                                                                                     |
| --------- | ----- | ----------------------------------------------------------------------------------------------------------- |
| `install` | `i`   | Sync deps and install Git hooks (`lefthook install`).                                                       |
| `format`  | `f`   | Format all sources (`format:*`).                                                                            |
| `check`   | `c`   | Run static checks in parallel (`check:*`).                                                                  |
| `test`    | `t`   | Run the test suite.                                                                                         |
| `build`   | `b`   | Build/package artifacts (`build:*`).                                                                        |
| `watch`   | `w`   | Live reload or watcher (omit when unused).                                                                  |
| `doctor`  | `do`  | Optional workstation/connector readiness check (offline by default; `--live` opt-in, never prints secrets). |
| `all`     | `a`   | `check`, `test`, `build` sequentially without rewriting.                                                    |

## Subtask Naming

Split `<task>:<x>` only when parts run independently (`format:<input>`: `format:python`, `format:dprint` per [dprint](dprint.md), `format:shell` via `shfmt -w`; `build:<output>`: `build:package`, `build:docs`, `build:image`). Keep cross-stack `check:<concern>` names fixed (avoid synonyms like `check:audit` or `check:dprint`; add repo-specific names like `check:docs`/`check:skills` only for distinct concerns):

- `check:deps` (`deptry`), `check:format` (`dprint check` + stack `--check`), `check:lint` (`ruff check`), `check:types` (`ty check`).
- `check:vuln` (`uv audit --preview-features audit-command --locked`), `check:leaks` ([betterleaks](../../code-security/references/betterleaks.md)), `check:scan` ([trivy](../../code-security/references/trivy/GUIDE.md)).
- `check:typos` (`typos`), `check:links` (`lychee --offline --no-progress`), `check:shell` (`shellcheck` + `shfmt`), `check:actions` ([jactionlint](../../github/references/jactionlint.md)).
- `check:tasks`: `mise tasks validate`, `mise lock --check` (when `mise.lock` exists), and `lefthook validate` (when `lefthook.yml` exists).

## Conventions

- **Parallelize offline vs network checks**: `check` depends on `check:local` (`pre-commit`) and `check:network` (`check:vuln`, optional `check:scan`—`pre-push`) per [lefthook](../../git-delivery/references/lefthook.md). Use `wait_for` for ordering without forcing execution.
- **Declare `sources` and `outputs`** on build tasks so unchanged inputs skip rebuilds.
- **Forward file args cleanly**: without `usage`, mise appends args to the last command (`format:dprint` takes `{staged_files}` directly). Multi-command formatters (`format:python`) declare `usage = 'arg "[files]..."'` and run `eval "set -- ${usage_files:-}"` (set multi-file defaults via `[ $# -gt 0 ] || set -- ...`—`default="a b"` quotes all words as one arg) so one task serves hooks and `mise run format`.

## Concise Output

Set `[settings.task]` `quiet = true` to hide echoes while keeping child stdout/stderr and prefixes (`MISE_TASK_QUIET=false` restores echoes; `mise run -n` dry-runs). Never use `silent`, drop stderr, or pipe through truncators. Keep counts, coverage, warnings, and findings visible (`--cov-report=` with `fail_under`; `--no-banner --verbose --redact=100` on Betterleaks) and verify both pass and fail runs.

## Tool Management

[tool-versions.md](tool-versions.md#select-exact-versions) owns pin selection; [upgrade-tools](upgrade-tools/GUIDE.md) owns upgrades.

## Additional task gotchas

- **Set `run_auto_install = false`** under `[settings.task]` so missing tools fail fast in hooks.
- **Never symlink project `mise.toml` into `~/.config/mise/conf.d/`**: mise treats `conf.d` files as global, breaking `mise lock` and leaking tasks.
- **Pin `[task_config] dir = "{{config_root}}"`** when parent configs exist; test from root and subdirs. After committing `mise.lock`, add `[tool_config] locked = true` (overrides global `locked_scopes = ["global"]`) so local and CI installs stay locked.
- **Set `raw = true` for interactive tasks redacting `.env`**: `_.file = { path = ".env", redact = true }` pipes output and nulls `stdin` once `.env` exists.
