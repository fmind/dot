---
name: dot-cli
description: "Operate dot: doctor, login, setup, status, pull, trust, secrets, caches, orphans, context, and session stats."
license: MIT
metadata:
  kind: connector
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/dot-cli
  created: "2026-07-31"
  updated: "2026-11-11"
---

# Dot CLI

Use `dot` for bounded repository checks, workstation diagnostics, provider login/setup, cache maintenance, and agent-session archives. Installed `--help` owns exact flags; native CLIs own stored credentials.

## Workflow

1. **Run documented commands directly**: check `--help` only for unfamiliar subcommands or usage errors. Global options precede subcommands.
1. **Select the guide; previews authorize nothing**: diagnostics and `--dry-run` never authorize login, cleanup, publication, or remote writes.
1. **Verify at the requested level**: local checks and hosted state are separate evidence.

## Task guides

<!-- guides:start -->

- [agent-usage](references/agent-usage.md): Report agent token usage, costs, and API equivalents from session archives or DuckDB.
- [authentication](references/authentication.md): Reconcile configured provider logins, OAuth scopes, one-off grants, and scoped secrets.
- [context](references/context.md): Measure discovery and instruction budgets in source or installed skill catalogs.
- [contracts](references/contracts.md): Resolve configuration, JSON output, exit codes, and session archive compatibility.
- [daily-workflows](references/daily-workflows.md): Run workstation doctor, repo status/pull, folder trust, session sync/stats, cache prune, and completions.
- [disk-space](references/disk-space.md): Audit disk headroom, cache growth, and shared tool versions before large builds or downloads.
- [orphans](references/orphans.md): Audit files chezmoi deployed but no longer manages; decide per path to keep, delete, or forget.

<!-- guides:end -->

## Workflow ownership

Use [git-delivery](../git-delivery/SKILL.md#commit-messages) for commits, [pull-request](../gh/references/pull-request.md) for PRs, and repository `mise` tasks for releases. Use `dot login` and `dot setup` for configured provider policy ([authentication](references/authentication.md)), `gh auth` / `gcloud auth` / `gws auth` for native diagnostics, and [auth-status](../auth-status/SKILL.md) for read-only cross-provider login and expiry sweeps.

## Documentation

- [fmind/dot](https://github.com/fmind/dot) · [releases](https://github.com/fmind/dot/releases) · [changelog](https://github.com/fmind/dot/blob/main/CHANGELOG.md)
- Companions: [mise](../mise/SKILL.md), [gws](../gws/SKILL.md), [gcloud](../gcloud/SKILL.md).
