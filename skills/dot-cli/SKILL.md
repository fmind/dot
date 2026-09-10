---
name: dot-cli
description: Operate fmind/dot commands for agent archives and statistics, repository pulls, environment verification, and cache pruning. Use when invoking dot.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/dot-cli
  created: "2026-07-31"
  updated: "2026-09-10"
---

# Dot CLI

Use `dot` for bounded repository operations, local diagnostics, and immutable agent-session archives. The installed command and its `--help` own the active interface. Skills and native CLIs own AI writing, provider setup, release, and provider-source retention.

## Commands

| Command          | Purpose                                                                                                           |
| ---------------- | ----------------------------------------------------------------------------------------------------------------- |
| `dot agent`      | Ingest, query, export, and compact session archives; inspect integrations and preview generated-artifact cleanup. |
| `dot completion` | Generate and syntax-check Fish completions before atomic replacement.                                             |
| `dot config`     | Show, locate, initialize, edit, and validate strict YAML configuration.                                           |
| `dot doctor`     | Check local tools, permissions, environment, and installation; `--deep` adds provider authentication probes.      |
| `dot pull`       | Fetch and fast-forward selected repositories with bounded concurrency and an explicit dirty-tree policy.          |
| `dot status`     | Inspect selected repositories and Docker without fetching; optionally report attention counts.                    |

## Workflow

1. **Inspect the installed contract**: use `dot --version`, `dot --help`, and the relevant subcommand help. Global options precede the subcommand.
1. **Diagnose selectively**: `dot doctor --json` is local; `dot doctor --deep --json` also probes authentication. `dot agent doctor --agent codex --explain` inspects one integration; `--deep` hashes sources and validates archives. Diagnostics share the `dot.diagnostics/v1` envelope with scope, passed, and checks.
1. **Select repositories**: use `dot status . --needs-attention`, then `dot pull . --dry-run --json` before an authorized update. Omitting paths uses configured workspace directories. `--push` requires remote-write authority.
1. **Capture and inspect sessions**: `dot agent session sync --agent codex --dry-run --json` previews parsing; remove `--dry-run` to publish complete generations. Session, prompt, and usage statistics are offline reads. See [daily workflows](references/daily-workflows.md) for date semantics, selection, and store boundaries.
1. **Clean only owned data**: `dot agent session compact` previews verified redundant generations; `--apply` deletes the selected generations. `dot agent clean` previews generated project prompts, proposals, and reports; `--apply` removes those categories. Neither command prunes provider-owned sources or unrelated tool caches.

## Contracts

Configuration precedence is explicit `--config`, then `DOT_CONFIG_PATH`, then `~/.config/dot.yaml`. A missing default uses built-in defaults; an explicit missing file fails. Configuration uses `schema_version: 3` and positive finite numeric seconds in `timeout_seconds`, `probe_timeout_seconds`, and `stale_lag_seconds`. Unknown keys are rejected. Repair commands remain available with malformed configuration; chezmoi-managed edits go through their source.

Requested data goes to stdout; progress and errors go to stderr. Exit codes are 0 for success, 1 for an operational failure or incomplete result, 2 for usage errors, and 130 for interruption. JSON output is versioned; failed operations never become an empty success. Hook protocols retain their host-specific neutral responses and bounded failure evidence.

A generation contains transcript, usage status/measurement, and integrity manifest, published in one atomic directory operation with private permissions. Extraction or publication failure leaves no completed generation. Retry the same ingestion after repairing the cause. Dot 4 uses only the fresh `sessions/v2` store, parser 3, and manifest schema 2. Earlier stores and standalone usage files remain untouched and are excluded from queries. Compaction compares canonical record fingerprints without retaining the full archive contents in memory; it preserves divergent transcripts, different usage evidence, and fails before deletion on unsupported formats or integrity errors.

## Workflow ownership

Use [conventional-commit](../conventional-commit/SKILL.md) for staged commits, [github-pull-request](../github-pull-request/SKILL.md) for PRs, and repository mise tasks for releases. Use `gh auth`, `gcloud auth`, and `gws auth` through their native contracts. Skills own AI judgment; deterministic privacy and mutation boundaries still apply.

## Documentation

- [fmind/dot](https://github.com/fmind/dot) — setup, implementation, and repository tasks.
- Companion skills: [agent-usage](../agent-usage/SKILL.md), [mise](../mise/SKILL.md), [gws](../gws/SKILL.md), [gcloud](../gcloud/SKILL.md).
