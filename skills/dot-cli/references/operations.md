---
name: operations
description: "Inspect repositories, diagnose workstation health, and manage session archives with dot."
---

# Dot Operations

## Workflow

1. **Diagnose selectively**: `dot doctor --json` checks local tools, permissions, environment, disk headroom, installation, and a chezmoi orphan count (a warning that never fails); `dot doctor --deep --json` also probes authentication. `dot doctor --headroom` checks only disk and memory headroom in one line (`--json` keeps the envelope) and cannot be combined with `--fix` or `--deep`. `dot agent doctor --agent codex` checks one agent's discovery (its deployed persona, skills link, and compiled subagents resolve to the shared sources; OpenCode also needs the Claude-skills opt-out), user-level notify hook events, command types, explicit Claude/Codex disable switches, last sync with its failed and retained counts, and archive readability. This static check does not prove project/policy overrides, Codex hook trust, or desktop delivery; use the harness's native hook inspection for effective session behavior. Diagnostics share the `dot.diagnostics/v1` envelope with scope, passed, and checks.
1. **Select repositories**: use `dot status . --needs-attention` (add `--fetch` for current remote counts), then `dot pull . --dry-run --json` before an authorized update. Omitting paths uses configured workspace directories. `--push` requires remote-write authority.
1. **Capture and inspect sessions**: `dot agent session sync --agent codex --dry-run --json` previews parsing; remove `--dry-run` to capture changed sessions. `dot agent stats` (totals, or per-session rows with `--sessions`) syncs incrementally before reporting; `dot agent session show ID --content --tail 20` reads a bounded transcript. See [daily workflows](daily-workflows.md) for date semantics, selection, and store boundaries.
1. **Scope personal credentials**: `dot secret run` follows [scoped credentials](authentication.md#scoped-credentials); use ordinary commands for customer profiles, SDK ADC, and native HF/Kaggle/OpenCode logins.

In the dotfiles repository, `mise run doctor` also runs chezmoi and mise diagnostics; `check:scan` audits the committed npm and pipx tool locks that `--locked` installs follow. `mise run verify` runs the installed `dot doctor` alone; neither command replaces the repository gate.
