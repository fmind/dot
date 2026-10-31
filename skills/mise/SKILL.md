---
name: mise
description: "Manage mise tool pins, lockfiles, environments, and tasks for hooks and CI."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/mise
  created: "2026-07-04"
  updated: "2026-10-31"
---

# Mise

One project `mise.toml` owns tool pins and commands; hooks and CI decide when to invoke them. Reuse the appropriate language stack's configuration instead of creating parallel command definitions.

## Workflow

1. **Inspect** the repository's existing tasks, lockfile, tool providers, hooks, and CI before changing the contract.
1. **Select versions** per the [tool version rules](references/tool-versions.md) before installing copied scaffold selectors; never copy tool binaries into projects.
1. **Keep tasks simple**: prefer direct commands, short sequential `run` arrays, and declarative dependencies; small setup/cleanup sequences are acceptable. Prefer native flags to conditions and explicit tasks to mode detection. Do not wrap commands in `bash -c` or `sh -c`, nest conditions, compress a program onto one line, or move a large shell block into TOML; keep unavoidable branching, retries, and response parsing in a small maintained script, preferably Python.
1. **Keep the shared vocabulary** below; [task conventions](references/task-conventions.md) own subtask names, concise output, argument forwarding, dependency order, and tool updates.
1. **Pin and install** the project toolchain, then validate task definitions with `mise tasks validate`; use `mise run <task>` in automation.
1. **Verify** the changed task and its callers, then the required complete gate; record a concrete reason for held-back pins.

## Task Vocabulary

Every project exposes the same core tasks with short aliases so agents, hooks, and CI stay portable:

| Task      | Alias | Purpose                                                                             |
| --------- | ----- | ----------------------------------------------------------------------------------- |
| `install` | `i`   | Sync dependencies and install git hooks (`lefthook install`).                       |
| `format`  | `f`   | Format all sources (fans out to `format:*`).                                        |
| `check`   | `c`   | All static checks in parallel (fans out to `check:*`).                              |
| `test`    | `t`   | Run the test suite.                                                                 |
| `build`   | `b`   | Compile or package artifacts (fans out to `build:*`).                               |
| `watch`   | `w`   | Live reload, or re-run tests; omitted by stacks with neither.                       |
| `all`     | `a`   | `check`, `test`, `build` in sequence without rewriting source files: the full gate. |

Python projects start from [python-stack](../python-stack/references/foundation/templates/mise.toml); specialized content and infrastructure projects use the task files owned by their stack skills, such as [infra-as-code](../infra-as-code/templates/mise.toml).

## Gotchas

- **Load `.env` only when needed**: `[env]` with `_.file = ".env"` loads dotenv values for tasks; use it only when the project needs that file. `_.source` expects a shell script.
- **Keep local builds free of side effects**: builds and checks must not publish, deploy, or spend by default; expose consequential operations only as explicit on-demand paths.
- **Isolate the full gate on dirty trees**: `mise run all` runs whole-tree checks, tests, and builds without rewriting source files, while `mise run format` writes the tree. When unrelated changes are present, use [git-worktree](../git-delivery/references/git-worktree/GUIDE.md) to materialize the current candidate in isolation and check that the tested files match before transferring proof.
- **Declare project tools in the project**: the workstation's global config serves agent coding (connectors, cross-project CLIs such as ruff, ty, lefthook, and dprint, and a few review and editor tools), and a global copy never replaces a project's pin. Declare every tool a project needs, such as kubectl, OpenTofu, or Typst, in the project's `mise.toml` with `mise use --pin <tool>` per the [tool version rules](references/tool-versions.md). In a client repository without mise, prefer the client's own toolchain and ask before adding a `mise.toml`.
- **Never bypass the locked global config**: the global config runs in locked mode, so `mise x <tool>` for a tool it does not list fails outside a project with `No lockfile URL found ... (--locked mode)`. Do not retry with `MISE_LOCKED=0`, which rewrites the deployed global lock; declare the tool in the project instead.

## Documentation

- [upgrade-tools](../upgrade-tools/SKILL.md) for per-repository upgrades
- [mise](https://mise.jdx.dev) · [Tasks](https://mise.jdx.dev/tasks/) · [Settings](https://mise.jdx.dev/configuration/settings.html)
- Releases: [mise](https://github.com/jdx/mise/releases) · [changelog](https://github.com/jdx/mise/blob/main/CHANGELOG.md)
- Companion skills: [lefthook](../github-actions/references/lefthook.md) (hooks call these tasks), [github-actions](../github-actions/references/ci-cd/GUIDE.md) (CI installs the toolchain with `mise-action` and runs `mise run all`).
