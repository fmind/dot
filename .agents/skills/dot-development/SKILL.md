---
name: dot-development
description: "Develop fmind/dot CLI commands, session parsers, storage, configuration, and installation."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/.agents/skills/dot-development
  created: "2026-09-09"
  updated: "2026-11-07"
---

# Develop Dot

Change the Python CLI while retaining its observable command, archive, and installation contracts. [dot-cli](../../../skills/dot-cli/SKILL.md) owns operating the installed tool; [python-stack](../../../skills/python-stack/references/foundation/GUIDE.md) and [cli-contracts](../../../skills/python-stack/references/cli-contracts.md) own generic implementation and interface design.

## Workflow

1. **Find the owner**: follow the source/test map below and read the current implementation before selecting a change boundary.
1. **Define the observable change**: keep the [cli-contracts](../../../skills/python-stack/references/cli-contracts.md) surface and Fish completions unless the task changes them. Exercise configuration errors through the public CLI; repair commands must remain usable when ordinary config loading fails.
1. **Implement through existing boundaries**: reuse `State`, `Runner`, and `run_parallel` for configuration, streams, external commands, and concurrent subprocess probes. Use temporary homes and fake runners in tests so a CLI regression cannot authenticate, publish, prune real data, or modify the workstation.
1. **Select proof**: run relevant existing tests with `uv run --frozen --project dot pytest -q dot/tests/<test_file>.py`; add behavioral cases for changed outcomes and realistic failures. Read [session compatibility](references/session-compatibility.md) before changing parser output, replacement rules, or stored formats.
1. **Qualify the candidate**: run affected static checks and reuse the focused test results above; project `AGENTS.md` owns the full-gate boundary and formatter isolation.
1. **Verify the right executable**: use `uv run --frozen --project dot dot <command>` for checkout behavior. When installation is in scope, `mise run deploy` reinstalls it with `uv tool install`, constrained to `dot/uv.lock`; verify `dot --version` and the changed installed command separately. `mise run doctor` is workstation health, not repository qualification.

## Source and test map

Modules live in `dot/src/fmind_dot/` and tests in `dot/tests/`; a module's tests are `test_<module>.py` unless listed here, and `rg -l <symbol> dot/tests` finds the rest.

- `cli.py`, `command_group.py`, and `state.py`: `test_cli.py`; exercise configuration errors through the public CLI.
- `auth.py` and `workstation.py`: `test_workstation.py` with synthetic provider probes. Never run real login/setup/prune as a validation gate.
- `secrets.py`: `test_secrets.py` (it rejects a personal `UV_PUBLISH_TOKEN`; packages use Trusted Publishing). Keep fixtures synthetic and never print credential values.
- `hooks.py`: `test_agent_hooks.py`.
- `system.py` (`dot completion`): `test_system.py`. `COMPLETION_SOURCES` lists the tools; only `completions.path` is configurable. An entry selects a native generator (`binary` and `args`) or a mise package with a bundled `<tool>.fish` (`package`); entries with neither run `<tool> completion fish`. Missing executables and inactive mise shims are skipped. Tools without a working generator need another source: agy keeps a chezmoi-managed script in `dot_config/fish/completions/`, and acli has none (1.3.39 removed `acli completion`). The Atuin cache omits its AI `?` binding.
- `agent.py` (`dot agent` commands): `test_agent_workflows.py`, `test_usage.py`, and `test_session_query.py`.
- `archive/`: `parsers.py` → `test_agent_parsers.py`, `store.py` → `test_session_store.py`, `query.py` → `test_session_query.py`, `sync.py` → `test_agent_workflows.py`, `statistics.py` → `test_daily_workflows.py`; `test_archive_transaction.py` covers replacement and usage retention, `test_usage_periods.py` covers deduplication, model changes, date boundaries, and legacy recapture.

## Documentation

- [Project tasks](../../../mise.toml) and [package configuration](../../../dot/pyproject.toml) own the actual gate and dependency graph.
- Releases: [fmind/dot](https://github.com/fmind/dot/releases) · [changelog](https://github.com/fmind/dot/blob/main/CHANGELOG.md)
- Companion skills: [chezmoi](../chezmoi/SKILL.md) (managed configuration), [dot-release](../dot-release/SKILL.md) (release lifecycle).
