---
name: dot-cli
description: "Run dot workstation commands: doctor, login, setup, cleanup, disk space, orphans, context budgets, archives."
license: MIT
metadata:
  kind: connector
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/dot-cli
  created: "2026-07-31"
  updated: "2026-10-04"
---

# Dot CLI

Use `dot` for bounded repository operations, local diagnostics, and agent-session archives. The installed command and its `--help` own the active interface. Dot also owns workstation login, setup, and cache workflows; native CLIs retain credentials and provider behavior.

## Workflow

1. Run documented commands directly; read the relevant `--help` only for an unfamiliar subcommand or after a usage error. Global options precede subcommands.
1. Select the guide for the requested operation. Diagnostics and previews do not authorize login, cleanup, publication, or remote writes.
1. Verify the command result at the requested level; local checks and hosted outcomes are separate evidence.

## Task guides

<!-- guides:start -->

- [authentication](references/authentication.md): Inspect and apply configured provider login, OAuth scopes, and account policy.
- [context](references/context.md): Measure discovery and instruction budgets in source or installed skill catalogs.
- [contracts](references/contracts.md): Resolve configuration, JSON output, exit codes, and session archive compatibility.
- [disk-space](references/disk-space.md): Audit workstation disk headroom, cache growth and shared tool versions before large downloads or builds.
- [operations](references/operations.md): Inspect repositories, diagnose workstation health, and manage session archives with dot.
- [orphans](references/orphans.md): Find files chezmoi deployed but no longer manages, then decide per path whether to keep, remove, or forget them.

<!-- guides:end -->

## Workflow ownership

Use [conventional-commit](../git-delivery/references/conventional-commit.md) for staged commits, [github-pull-request](../github-pull-request/SKILL.md) for PRs, and repository mise tasks for releases. Use `dot login` and `dot setup` for configured provider policy ([authentication](references/authentication.md)); inspect `gh auth`, `gcloud auth`, and `gws auth` directly for native diagnostics, and use [auth-status](../auth-status/SKILL.md) for a read-only login and expiry sweep. Skills own AI judgment; deterministic privacy and mutation boundaries still apply.

## Documentation

- [fmind/dot](https://github.com/fmind/dot) — setup, implementation, and repository tasks.
- [Daily workflows](references/daily-workflows.md) — command examples for repositories, sessions and statistics, cleanup, publication, and completions.
- Releases: [fmind/dot](https://github.com/fmind/dot/releases) · [changelog](https://github.com/fmind/dot/blob/main/CHANGELOG.md)
- Companion skills: [agent-usage](../agent-usage/SKILL.md) (usage and cost reports), [mise](../mise/SKILL.md), [gws](../gws/SKILL.md), [gcloud](../gcloud/SKILL.md).
