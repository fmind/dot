---
name: mise
description: Configure pinned mise tools and the canonical install, format, check, test, build, and watch tasks shared by hooks and CI. Use for any mise.toml or task work.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/mise
  created: "2026-07-04"
  updated: "2026-09-05"
---

# Mise

One project `mise.toml` owns tool pins and commands; hooks and CI decide when to invoke them. Reuse the appropriate language stack's configuration instead of creating parallel command definitions.

## Workflow

1. **Inspect** the repository's existing tasks, lockfile, tool providers, hooks, and CI before changing the contract.
1. **Keep the shared vocabulary** below; read [task conventions](references/task-conventions.md) for subtask names, aliases, argument forwarding, dependency order, and tool updates.
1. **Pin and install** the project toolchain, then validate task definitions with `mise tasks validate`; use `mise run <task>` in automation.
1. **Verify** the changed task and its callers, then the required complete gate; record a concrete reason for held-back pins.

## Task Vocabulary

Every project exposes the same core tasks with short aliases so agents, hooks, and CI stay portable:

| Task      | Alias | Purpose                                                                                                                                                                                 |
| --------- | ----- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `install` | `i`   | Sync dependencies and install git hooks (`lefthook install`).                                                                                                                           |
| `format`  | `f`   | Format all sources (fans out to `format:*`).                                                                                                                                            |
| `check`   | `c`   | All static checks in parallel (fans out to `check:*`).                                                                                                                                  |
| `test`    | `t`   | Run the test suite.                                                                                                                                                                     |
| `build`   | `b`   | Compile or package artifacts (fans out to `build:*`).                                                                                                                                   |
| `watch`   | `w`   | Run the app with live reload, or re-run tests where there is no app to serve; omitted only by a stack with neither, such as [terraform-stack](../terraform-stack/references/mise.toml). |
| `all`     | `a`   | `format`, `check`, `test`, `build` in sequence: the full gate.                                                                                                                          |

Language stacks ship concrete files: [go-stack](../go-stack/references/mise.toml), [python-stack](../python-stack/references/mise.toml), and [angular](../angular/references/mise.toml) for TypeScript web applications.

## Gotchas

- **Local builds**: builds and checks must not publish, deploy, or spend by default; expose consequential operations only as explicit on-demand paths.
- **Dirty trees**: `all` includes formatters. Preserve unrelated work by materializing the current candidate in isolation; check that the tested files match before transferring proof.
- **Argument forwarding**: keep shell quoting and tool arguments intact; verify raw argument behavior with a small local example when adding wrapper tasks.
- **Tool ownership**: distinguish global interactive tools from project pins used by hooks and CI; inspect [provenance pilot](references/provenance-pilot.md) only for that optional provider experiment.

## Documentation

- [Provenance pilot and adoption boundary](references/provenance-pilot.md)
- [mise](https://mise.jdx.dev) · [Tasks](https://mise.jdx.dev/tasks/) · [Settings](https://mise.jdx.dev/configuration/settings.html)
- Companion skills: [lefthook](../lefthook/SKILL.md) (hooks call these tasks), [github-actions](../github-actions/SKILL.md) (CI installs the toolchain with `mise-action` and runs `mise run all`).
