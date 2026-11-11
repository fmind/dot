---
name: mise
description: "Manage mise pins, lockfiles, environments, and tasks; format docs and configs with dprint."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/mise
  created: "2026-07-04"
  updated: "2026-11-11"
---

# Mise

One project `mise.toml` owns tool pins and task commands; hooks and CI only choose when to invoke them.

## Workflow

1. **Pin exact versions** per [tool-versions.md](references/tool-versions.md) before installing copied scaffolds; never commit tool binaries.
1. **Keep tasks simple**: use direct commands, short `run` arrays, native CLI flags, and `depends`; never wrap commands in `bash -c`/`sh -c`, nest conditionals, cram scripts onto one line, or embed large shell blocks in TOML (put branching, retries, and response parsing in a small Python script).
1. **Follow the shared vocabulary** below and [task-conventions.md](references/task-conventions.md) for subtasks, concise output, argument forwarding, and ordering.
1. **Lock and validate**: install pinned tools, run `mise tasks validate`, and invoke `mise run <task>` in automation.
1. **Verify** modified tasks and their callers, documenting any held-back pin.

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

Start Python projects from [python-stack](../python-stack/references/foundation/templates/mise.toml) and OpenTofu projects from [infra-as-code](../infra-as-code/templates/mise.toml).

## Task guides

<!-- guides:start -->

- [dprint](references/dprint.md): Configure and format JSON, Markdown, TOML, and YAML with dprint.

<!-- guides:end -->

## Gotchas

- **Load `.env` only when needed**: `[env]` `_.file = ".env"` loads dotenv variables (`_.source` sources a shell script).
- **Keep gates side-effect-free**: `check`, `test`, `build`, and `all` must never publish, deploy, or spend; keep consequential tasks explicit.
- **Isolate `mise run all` on dirty trees**: `all` inspects the full tree without rewriting files while `format` mutates files; when unrelated edits exist, test a materialized snapshot via [git-worktree](../git-delivery/references/git-worktree/GUIDE.md).
- **Pin project tools in the project**: global workstation tools never replace project pins; declare every tool (`kubectl`, `opentofu`, etc.) in the project's `mise.toml` via `mise use --pin <tool>` ([tool-versions.md](references/tool-versions.md)), and ask before adding `mise.toml` to a non-mise client repo.
- **Never set `MISE_LOCKED=0`**: global mise runs locked, so `mise x <unlisted-tool>` outside a project fails (`No lockfile URL found ... (--locked mode)`); declare the tool in the project rather than mutating the global lock.

## Documentation

- [upgrade-tools](../upgrade-tools/SKILL.md) · [mise](https://mise.jdx.dev) · [Tasks](https://mise.jdx.dev/tasks/) · [Settings](https://mise.jdx.dev/configuration/settings.html) · [releases](https://github.com/jdx/mise/releases) · [changelog](https://github.com/jdx/mise/blob/main/CHANGELOG.md)
- Companions: [lefthook](../github-actions/references/lefthook.md), [github-actions](../github-actions/references/ci-cd/GUIDE.md).
