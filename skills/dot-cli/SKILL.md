---
name: dot-cli
description: Operate fmind/dot commands for agent archives and statistics, repository pulls, environment verification, and cache pruning. Use when invoking dot.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/dot-cli
  created: "2026-07-31"
  updated: "2026-09-09"
---

# Dot CLI

`dot` is the typed Python CLI of `fmind/dot`, installed at `~/.local/bin/dot`. Use `dot <command> --help` for exact flags. `pull-request` also accepts the established `pr` alias; other commands use canonical names only.

## Commands

| Command            | Purpose                                                                                                         |
| ------------------ | --------------------------------------------------------------------------------------------------------------- |
| `dot agent`        | Inspect integrations and manage normalized sessions and token usage.                                            |
| `dot chezmoi`      | Find former chezmoi targets and move approved orphans to recoverable backups.                                   |
| `dot commit`       | Generate and commit an existing staged diff; `--all` stages the worktree only when the index is empty.          |
| `dot completion`   | Generate Fish completions for `dot` and configured external CLIs.                                               |
| `dot config`       | Show, locate, initialize, edit, or validate `~/.config/dot.yaml`.                                               |
| `dot login`        | Run GitHub, Google Workspace, or GCP authentication flows.                                                      |
| `dot prune`        | Preview or apply cleanup for agent data and caches; see [references/prune-flags.md](references/prune-flags.md). |
| `dot pull`         | Pull configured repository roots concurrently; `--push` also pushes clean repositories.                         |
| `dot pull-request` | Generate a PR description and create it with `gh`; `pr` is an alias.                                            |
| `dot release`      | Validate, prepare, tag, push, and refresh an `fmind/dot` release.                                               |
| `dot setup`        | Configure GitHub CLI OAuth scopes or the Google Workspace GCP project.                                          |
| `dot status`       | Report Git repository and Docker status, with optional JSON.                                                    |
| `dot verify`       | Check environment, auth, tools, secrets, and install freshness; `--fix` repairs bounded local state.            |

Global flags are `--config/-c <path>`, `--verbose`, and `--version/-v`.

## Workflow

1. **Identify the executable**: check `dot --version` and command help. The installed CLI can lag source; in the dot repository use `uv run --frozen dot <command>` to exercise the checkout.
1. **Health when diagnosing**: use `dot verify` for the workstation or `dot agent doctor --json` for fast integration metadata; `dot agent doctor --agent codex --deep --explain --json` adds targeted hashing, archive validation, and bounded issue examples. OpenCode is discovery-only, with no archive adapter. Ordinary session queries do not require a workstation audit.
1. **Sessions**: run `dot agent session sync`, or ingest one adapter with `dot agent session ingest AGENT [SESSION_ID] [CWD]`.
1. **Inspect**: `dot agent session list` returns the newest 50 current generations by default; widen it with `--limit`, `--all-generations`, repeated `--status`, or `--json`.
1. **Compact**: `dot agent session compact` dry-runs prefix-proven generation retention; `--apply` deletes only verified superseded generations.
1. **Disk**: preview selected cleanup with `dot prune --all --deep`; use the same selection with `--apply` only after reviewing the plan.
1. **Reinstall after source edits**: inside the dot repository, run `mise run deploy` to rebuild and install `~/.local/bin/dot`.

For bounded metadata retrieval, use `dot agent session list --limit 10 --json`, then `dot agent session show <generation-id>`. Use `show <session-id> --latest` to explicitly choose the latest generation of an ambiguous session. `show --content` includes private prompts and responses; use it only when their contents are needed. The query owner reads immutable JSONL generations, not a derived SQLite index. [Daily workflows](references/daily-workflows.md) documents selection, statistics, migration, and publication boundaries; [agent-usage](../agent-usage/SKILL.md) owns deeper usage analysis.

## Gotchas

- **Commit scope**: `dot commit` requires staged changes and prints their paths before opening the editor. It creates a commit after message review. Use `--all` only when the index is empty and every working-tree change belongs in the authorized commit.
- **Side effects**: session sync/ingest writes the normalized store; `verify --fix` repairs local state, `pull` changes checkouts, and `pull --push`, PR creation, release, and setup have remote effects. Reuse session authority and preview cleanup before an authorized `--apply`.
- **Skill health**: doctor checks bounded package metadata in `~/.agents/skills/` and expected repository links when chezmoi is available. Broken links, missing entrypoints, and incomplete scans are unhealthy; `--explain` adds bounded package names without reading skill bodies. Repair independently installed packages at their source; `--fix` delegates managed integration repair to chezmoi.
- **Deep doctor**: source hashing and full archive reconciliation can take time; progress is written to stderr.
- **Managed config**: `dot config edit` routes chezmoi-managed configuration through `chezmoi edit --apply --force` and validates afterward; `config init --force` refuses to overwrite a managed target.
- **Compaction**: invalid identities, permissions, links, unexpected files, or transcript digests stop planning before deletion; unknown schemas are retained.

## Documentation

- [fmind/dot](https://github.com/fmind/dot) — source, README, and repository-specific skills.
- Companion skills: [agent-usage](../agent-usage/SKILL.md) and [mise](../mise/SKILL.md).
