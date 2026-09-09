---
name: dot-development
description: Maintain fmind/dot's Python implementation. Use when changing its CLI commands, session parsers or storage, configuration, completions, or installation.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/.agents/skills/dot-development
  created: "2026-09-09"
  updated: "2026-09-09"
---

# Develop Dot

Change the Python CLI while retaining its observable command, archive, and installation contracts. [dot-cli](../../../skills/dot-cli/SKILL.md) owns operating the installed tool; [python-stack](../../../skills/python-stack/SKILL.md) and [cli-contracts](../../../skills/cli-contracts/SKILL.md) own generic implementation and interface design.

## Workflow

1. **Find the owner**: inspect `git status --short`, `git diff`, and `git diff --cached`, then follow the source/test map below. Read the current implementation before selecting a change boundary.
1. **Define the observable change**: preserve command names, aliases, help, JSON output, exit codes, stdout/stderr, and Fish completions unless the task explicitly changes them. Exercise configuration errors through the public CLI; repair commands must remain usable when ordinary config loading fails.
1. **Implement through existing boundaries**: reuse `State` and `Runner` for configuration, streams, and external commands. Use temporary homes and fake runners in tests so a CLI regression cannot authenticate, publish, prune real data, or modify the workstation.
1. **Select proof**: run relevant existing tests with `uv run --frozen pytest -q dot/tests/<test_file>.py`; add behavioral cases for changed outcomes and realistic failures. Read [session compatibility](references/session-compatibility.md) before changing parser output, generation identity, or stored formats.
1. **Qualify the candidate**: run `mise run all`. Since it formats, materialize tracked changes and relevant untracked files in an isolated Git-aware candidate when the tree contains unrelated work; retain symlinks, modes, deletions, and required repository metadata. Verify the candidate matches the intended source and inspect formatter changes before transferring proof or edits.
1. **Verify the right executable**: use `uv run --frozen dot <command>` for checkout behavior. When installation is in scope, `mise run deploy` builds and selects the installed runtime; verify `dot --version` and the changed installed command separately. `mise run verify` is workstation health, not repository qualification.

## Documentation

- [Project tasks](../../../mise.toml) and [package configuration](../../../dot/pyproject.toml) own the actual gate and dependency graph.
- Companion skills: [chezmoi](../chezmoi/SKILL.md) (managed configuration), [dot-release](../dot-release/SKILL.md) (release lifecycle), [systematic-debugging](../../../skills/systematic-debugging/SKILL.md) (unknown failures).
