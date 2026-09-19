---
name: dot-cli
description: "Operate dot workstation commands: agent context budgets, archives, usage, health, and cleanup."
license: MIT
metadata:
  kind: connector
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/dot-cli
  created: "2026-07-31"
  updated: "2026-09-19"
---

# Dot CLI

Use `dot` for bounded repository operations, local diagnostics, and agent-session archives. The installed command and its `--help` own the active interface. Dot also owns workstation login, setup, and cache workflows; native CLIs retain credentials and provider behavior. Skills own AI writing, release, and provider-source retention.

## Workflow

1. Inspect the installed command with `dot --version` and the relevant `--help`; global options precede subcommands.
1. Select the guide for the requested operation. Diagnostics and previews do not authorize login, cleanup, publication, or remote writes.
1. Verify the command result at the requested level; local checks and hosted outcomes are separate evidence.

## Task guides

<!-- guides:start -->

- [authentication](references/authentication.md): Inspect and apply configured provider login, OAuth scopes, and account policy.
- [context](references/context.md): Measure discovery and instruction budgets in source or installed skill catalogs.
- [contracts](references/contracts.md): Resolve configuration, JSON output, exit codes, and session archive compatibility.
- [operations](references/operations.md): Inspect repositories, diagnose workstation health, and manage session archives with dot.

<!-- guides:end -->

## Workflow ownership

Use [conventional-commit](../git-delivery/references/conventional-commit.md) for staged commits, [github-pull-request](../github-pull-request/SKILL.md) for PRs, and repository mise tasks for releases. Use `dot login` and `dot setup` for configured provider policy; inspect `gh auth`, `gcloud auth`, and `gws auth` directly for native diagnostics. `dot login google` excludes GitHub. Skip decisions require usable credentials and requested scope coverage; unknown status fails, and `--force` explicitly requests authentication. Skills own AI judgment; deterministic privacy and mutation boundaries still apply.

## Documentation

- [fmind/dot](https://github.com/fmind/dot) — setup, implementation, and repository tasks.
- [Daily workflows](references/daily-workflows.md) — command examples for repositories, sessions and statistics, cleanup, publication, and completions.
- [CLI migration](references/cli-migration.md) — command changes, date boundaries, JSON selectors.
- Releases: [fmind/dot](https://github.com/fmind/dot/releases) · [changelog](https://github.com/fmind/dot/blob/main/CHANGELOG.md)
- Companion skills: [agent-usage](../agent-usage/SKILL.md), [mise](../mise/SKILL.md), [gws](../gws/SKILL.md), [gcloud](../gcloud/SKILL.md).
