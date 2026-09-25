---
name: operations
description: "Inspect repositories, diagnose workstation health, and manage session archives with dot."
---

# Dot Operations

## Commands

| Command          | Purpose                                                                                                         |
| ---------------- | --------------------------------------------------------------------------------------------------------------- |
| `dot agent`      | Sync, query, and export session archives; check notify hooks and sync health; report activity.                  |
| `dot cache`      | Inspect configured native caches, or select Docker, Hugging Face, or uv.                                        |
| `dot login`      | Show providers; authenticate Workspace, GCP, GitHub, or the Workspace-then-GCP `google` sequence.               |
| `dot prune`      | Show providers; `dot prune all` cleans configured caches after confirmation (`--dry-run` previews).             |
| `dot orphan`     | List files chezmoi deployed but no longer manages, with whether each still holds its last write; never deletes. |
| `dot setup`      | Reconcile GitHub scopes or an explicit Workspace project and OAuth client.                                      |
| `dot secret`     | Supply a personal key to one command, or publish distributions to PyPI with a scoped token.                     |
| `dot completion` | Generate and syntax-check Fish completions before atomic replacement; `--check` validates without installing.   |
| `dot config`     | Show, locate, initialize, edit, and validate strict YAML configuration.                                         |
| `dot doctor`     | Check local tools, permissions, environment, and installation; `--deep` adds provider authentication probes.    |
| `dot pull`       | Fetch and fast-forward selected repositories with bounded concurrency and an explicit dirty-tree policy.        |
| `dot status`     | Inspect selected repositories without fetching; optionally report attention counts.                             |
| `dot trust`      | Pre-accept harness folder trust for a repository, or `all` for the configured workspaces.                       |

## Workflow

1. **Inspect the installed contract**: use `dot --version`, `dot --help`, and the relevant subcommand help. Global options precede the subcommand.
1. **Diagnose selectively**: `dot doctor --json` is local; `dot doctor --deep --json` also probes authentication. `dot agent doctor --agent codex` checks one agent's user-level notify hook events, command types, explicit Claude/Codex disable switches, last sync with its failed and retained counts, and archive readability. This static check does not prove project/policy overrides, Codex hook trust, or desktop delivery; use the harness's native hook inspection for effective session behavior. Diagnostics share the `dot.diagnostics/v1` envelope with scope, passed, and checks.
1. **Select repositories**: use `dot status . --needs-attention`, then `dot pull . --dry-run --json` before an authorized update. Omitting paths uses configured workspace directories. `--push` requires remote-write authority.
1. **Capture and inspect sessions**: `dot agent session sync --agent codex --dry-run --json` previews parsing; remove `--dry-run` to capture changed sessions. `dot agent stats` and `dot agent usage` sync incrementally before reporting. See [daily workflows](daily-workflows.md) for date semantics, selection, and store boundaries.
1. **Scope personal credentials**: `dot secret run NAME -- COMMAND ...` supplies one key from the existing environment or `~/.config/dot/secrets/NAME`. Empty overrides fail; the personal file must be an owner-only regular file. Use ordinary commands for customer profiles, SDK ADC, and native HF/Kaggle/OpenCode logins. `dot secret publish --dry-run` validates the PyPI-only helper; actual publication requires explicit authority. See the repository [credential setup](https://github.com/fmind/dot#secret-management) for native precedence and migration.

In the dotfiles repository, `mise run doctor` also runs chezmoi and mise diagnostics plus `check:vuln:tools`. That audit covers installed npm and pipx versions selected by a mise configuration source; retired or unmanaged installations are outside its scope. It reports audited versions, advisory findings, and coverage gaps, and fails when nothing was audited or any finding or gap remains. `mise run verify` runs the installed `dot doctor` alone; neither command replaces the repository gate.
