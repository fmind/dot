---
name: operations
description: "Inspect repositories, diagnose workstation health, and manage session archives with dot."
---

# Dot Operations

## Commands

| Command          | Purpose                                                                                                      |
| ---------------- | ------------------------------------------------------------------------------------------------------------ |
| `dot agent`      | Ingest, query, export, and compact session archives; inspect integrations and report activity.               |
| `dot cache`      | Inspect configured native caches, or select Docker, Hugging Face, or uv.                                     |
| `dot login`      | Show providers; authenticate Workspace, GCP, GitHub, or the Workspace-then-GCP `google` sequence.            |
| `dot prune`      | Show providers; `dot prune all` cleans configured caches after confirmation (`--dry-run` previews).          |
| `dot setup`      | Reconcile GitHub scopes or an explicit Workspace project and OAuth client.                                   |
| `dot completion` | Generate and syntax-check Fish completions before atomic replacement.                                        |
| `dot config`     | Show, locate, initialize, edit, and validate strict YAML configuration.                                      |
| `dot doctor`     | Check local tools, permissions, environment, and installation; `--deep` adds provider authentication probes. |
| `dot pull`       | Fetch and fast-forward selected repositories with bounded concurrency and an explicit dirty-tree policy.     |
| `dot status`     | Inspect selected repositories without fetching; optionally report attention counts.                          |


## Workflow

1. **Inspect the installed contract**: use `dot --version`, `dot --help`, and the relevant subcommand help. Global options precede the subcommand.
1. **Diagnose selectively**: `dot doctor --json` is local; `dot doctor --deep --json` also probes authentication. `dot agent doctor --agent codex --explain` inspects one integration; `--deep` hashes sources and validates archives. Diagnostics share the `dot.diagnostics/v1` envelope with scope, passed, and checks.
1. **Select repositories**: use `dot status . --needs-attention`, then `dot pull . --dry-run --json` before an authorized update. Omitting paths uses configured workspace directories. `--push` requires remote-write authority.
1. **Capture and inspect sessions**: `dot agent session sync --agent codex --dry-run --json` previews parsing; remove `--dry-run` to publish complete generations. Session, prompt, and usage statistics are offline reads. See [daily workflows](daily-workflows.md) for date semantics, selection, and store boundaries.
1. **Clean only owned data**: `dot agent session compact` previews verified redundant generations; `--apply` deletes the selected generations. Provider-owned sources, project documents, and tool caches remain outside archive compaction.

