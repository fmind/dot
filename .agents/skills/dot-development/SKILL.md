---
name: dot-development
description: "Develop fmind/dot CLI commands, session parsers, storage, configuration, and installation."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/.agents/skills/dot-development
  created: "2026-09-09"
  updated: "2026-09-16"
---

# Develop Dot

Change the Python CLI while retaining its observable command, archive, and installation contracts. [dot-cli](../../../skills/dot-cli/SKILL.md) owns operating the installed tool; [python-stack](../../../skills/python-stack/references/foundation/GUIDE.md) and [cli-contracts](../../../skills/cli-development/references/cli-contracts.md) own generic implementation and interface design.

## Workflow

1. **Find the owner**: inspect `git status --short`, `git diff`, and `git diff --cached`, then follow the source/test map below. Read the current implementation before selecting a change boundary.
1. **Define the observable change**: preserve command names, aliases, help, JSON output, exit codes, stdout/stderr, and Fish completions unless the task explicitly changes them. Exercise configuration errors through the public CLI; repair commands must remain usable when ordinary config loading fails.
1. **Implement through existing boundaries**: reuse `State` and `Runner` for configuration, streams, and external commands. Use temporary homes and fake runners in tests so a CLI regression cannot authenticate, publish, prune real data, or modify the workstation.
1. **Select proof**: run relevant existing tests with `uv run --frozen pytest -q dot/tests/<test_file>.py`; add behavioral cases for changed outcomes and realistic failures. Read [session compatibility](references/session-compatibility.md) before changing parser output, generation identity, or stored formats.
1. **Qualify the candidate**: run affected static checks and reuse the focused test results above. Follow project `AGENTS.md` for the full-gate boundary: shared behavior, dependencies, packaging, or explicit full qualification. Isolate write-formatting checks when unrelated work is present and compare the tested candidate with the intended source before transferring proof or edits.
1. **Verify the right executable**: use `uv run --frozen dot <command>` for checkout behavior. When installation is in scope, `mise run deploy` builds and selects the installed runtime; verify `dot --version` and the changed installed command separately. `mise run verify` is workstation health, not repository qualification.

## Source and test map

- `cli.py`, `command_group.py`, `state.py`, and `config.py`: command discovery, configuration, and public errors; `test_cli.py` and `test_config.py` exercise the boundary.
- `auth.py` and `workstation.py`: login, setup, cache inspection, and confirmed cleanup; `test_workstation.py` uses synthetic provider probes. Never run real login/setup/prune as a validation gate.
- `repository.py`, `process.py`, and `system.py`: repository concurrency, subprocess cancellation, completions, and workstation checks; use their matching tests and temporary homes.
- `archive/parsers.py`, `usage.py`, `pricing.py`, and `statistics.py`: capture, request accounting, subscription periods, and prompt statistics. `test_usage_periods.py` covers deduplication, model changes, date boundaries, and immutable recapture; `test_pricing.py` covers cache accounting and unknown rates.

## Documentation

- [Project tasks](../../../mise.toml) and [package configuration](../../../dot/pyproject.toml) own the actual gate and dependency graph.
- Releases: [fmind/dot](https://github.com/fmind/dot/releases) · [changelog](https://github.com/fmind/dot/blob/main/CHANGELOG.md)
- Companion skills: [chezmoi](../chezmoi/SKILL.md) (managed configuration), [dot-release](../dot-release/SKILL.md) (release lifecycle), [systematic-debugging](../../../skills/systematic-debugging/SKILL.md) (unknown failures).
