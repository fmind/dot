# Mise Task Conventions

## Task Vocabulary

| Task      | Alias | Purpose                                                  |
| --------- | ----- | -------------------------------------------------------- |
| `install` | `i`   | Sync deps and install Git hooks (`lefthook install`).    |
| `format`  | `f`   | Format all sources (`format:*`).                         |
| `check`   | `c`   | Run static checks in parallel (`check:*`).               |
| `test`    | `t`   | Run the test suite.                                      |
| `build`   | `b`   | Build/package artifacts (`build:*`).                     |
| `watch`   | `w`   | Live reload or watcher (omit when unused).               |
| `all`     | `a`   | `check`, `test`, `build` sequentially without rewriting. |

## Subtask Naming

Split `<task>:<x>` only when parts run independently:

- **`format:<input>`**: source family (`format:python`, `format:dprint` for JSON/Markdown/TOML/YAML per [dprint](dprint.md), `format:shell` via `shfmt -w`).
- **`build:<output>`**: artifact (`build:package`, `build:docs`, `build:image`).
- **`check:<concern>`**: fixed cross-stack names (avoid synonyms like `check:audit` or `check:dprint`; add repo-specific names like `check:docs`/`check:skills`/`check:pkg`/`check:site`/`check:validate` or source splits only for distinct concerns; single-letter aliases are best-effort):
  - `check:deps`: missing/unused deps (`deptry`).
  - `check:format`: formatting drift (`dprint check` + stack `--check`, e.g. `shfmt -d`).
  - `check:lint`: lint rules (`ruff check`).
  - `check:types`: static types (`ty check`).
  - `check:vuln`: dependency CVEs (`uv audit`).
  - `check:leaks`: working-tree secrets ([betterleaks](../../code-security/references/betterleaks.md)).
  - `check:scan`: deps, IaC, images, licenses ([trivy](../../code-security/references/trivy/GUIDE.md)).
  - `check:typos`: spelling (`typos`).
  - `check:links`: Markdown/site links (`lychee --offline --no-progress` / `lychee`).
  - `check:shell`: shell lint/format (`shellcheck` + `shfmt`).
  - `check:tasks`: task and hook definitions (`mise tasks validate`, plus `lefthook validate` when `lefthook.yml` exists).
  - `check:actions`: workflow lint/audit ([jactionlint](../../github/references/jactionlint.md)).

## Conventions

- **Parallelize offline vs network checks**: `check` depends on `check:local` (`check:deps`, `check:format`, `check:leaks`, `check:lint`, `check:types`—`pre-commit`) and `check:network` (`check:vuln`, optional `check:scan`—`pre-push`) per [lefthook](../../github/references/lefthook.md). Use `wait_for` for ordering without forcing execution.
- **Declare `sources` and `outputs`** on build tasks so unchanged inputs skip rebuilds.
- **Forward file args cleanly**: without `usage`, mise appends CLI args to the last command (`format:dprint` takes `{staged_files}` directly). Multi-command formatters (`format:python`) or custom defaults declare `usage = 'arg "[files]..."'` (+ `default=`) and start with `eval "set -- $usage_files"` so one task serves hooks and `mise run format` without `:files` duplicates.

## Concise Output

Set `[settings.task]` `quiet = true` to hide command echoes while preserving child stdout/stderr and task prefixes (`MISE_TASK_QUIET=false` restores echoes and `mise run -n` dry-runs). Never use `silent`, drop stderr, or pipe through truncators. Keep test counts, coverage, warnings, and findings visible: pass `--cov-report=` with `fail_under` (use `report:coverage` for full tables) and `--no-banner --verbose --redact=100` on Betterleaks; verify passing and failing runs before adopting quieter flags.

## Tool Management

[tool-versions.md](tool-versions.md#select-exact-versions) owns pin selection; [upgrade-tools](upgrade-tools/GUIDE.md) owns upgrades.

## Additional task gotchas

- **Set `run_auto_install = false`** under `[settings.task]` so missing tools fail fast in hooks.
- **Never symlink project `mise.toml` into `~/.config/mise/conf.d/`**: mise treats `conf.d` files as global, breaking `mise lock` (`No tools configured to lock`) and leaking tasks.
- **Pin `[task_config] dir = "{{config_root}}"`** when parent configs exist; test from root and subdirectories. Once `mise.lock` is committed, add `[settings] locked = true` to enforce locked installs locally as well as in CI.
- **Set `raw = true` for interactive tasks when redacting `.env`**: `_.file = { path = ".env", redact = true }` pipes output and nulls `stdin` once `.env` exists.
- **Edit YAML safely with `yq` v4**: read env via `strenv(VAR)` (`yq -i '.key = strenv(VAL)' file.yml`) instead of shell interpolation; restrict `typos` `--no-follow`/exclusions to vendored tokens.
