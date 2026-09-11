---
name: jules
description: Operate Google Jules remote coding tasks with current official guidance. Use when using the jules CLI, preparing its environment, or reviewing remote task results.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/jules
  created: "2026-09-09"
  updated: "2026-09-11"
---

# Jules

Operate Jules through its CLI and hosted task workflow. Its remote workspace does not inherit local user configuration or skills merely because they exist on this machine.

## Workflow

1. Inspect `jules --version` and `jules --help`; resolve the intended connected repository, branch, and existing task before starting another one.
1. Open the CLI reference and changelog before relying on commands, task capabilities, or limits. Keep service-specific behavior upstream and distinguish installed CLI support from hosted availability.
1. For an authorized remote task, supply a bounded request and repository setup instructions; inspect the generated plan and task state using the current interface.
1. Review the resulting diff and test evidence before applying or publishing changes. A completed remote task is not proof that a PR was merged or that local tests passed.

## Official Skills and Guidance

- [Official getting-started guide](https://jules.google/docs/): repository instructions through AGENTS.md; use [agent-project](../agent-project/SKILL.md) to prepare that contract.
- [Jules Awesome List](https://github.com/google-labs-code/jules-awesome-list): Google Labs' linked prompt collection, not an installable Agent Skills catalog.
- These sources do not establish a native Jules skill-installation interface. Recheck current docs when asked about skills; do not invent a CLI command or assume local skill directories are uploaded.

## Top Links

For session recovery, automation, and integration decisions, read the [operation links](references/features.md). Use the official documentation index for other capabilities.

- [CLI reference](https://jules.google/docs/cli/reference/) · [Changelog](https://jules.google/docs/changelog/)
- [Environment setup](https://jules.google/docs/environment/): remote dependencies and setup scripts.
- [Running tasks](https://jules.google/docs/running-tasks/) · [Reviewing code](https://jules.google/docs/code/)
- [API documentation](https://jules.google/docs/api/reference/): use when the task requires API integration rather than the CLI.
