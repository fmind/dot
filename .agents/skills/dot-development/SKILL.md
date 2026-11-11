---
name: dot-development
description: "Develop fmind/dot CLI commands, session parsers, archive storage, config, and deploy."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/.agents/skills/dot-development
  created: "2026-09-09"
  updated: "2026-11-11"
---

# Develop Dot

Modify `fmind_dot` while preserving CLI, archive, and installation contracts. [dot-cli](../../../skills/dot-cli/SKILL.md) operates the installed CLI; [python-stack](../../../skills/python-stack/references/foundation/GUIDE.md) and [cli-contracts](../../../skills/python-stack/references/cli-contracts.md) own generic Python and CLI design.

## Workflow

1. **Locate the owner**: check the map below and read current code before choosing a seam.
1. **Preserve the surface**: keep [cli-contracts](../../../skills/python-stack/references/cli-contracts.md) and Fish completions intact unless changing them. Test config failures through the public CLI; repair commands (`config edit`, `--help`) must work when config loading fails.
1. **Use existing boundaries**: route config, streams, subprocesses, and fan-out through `State`, `Runner`, and `run_parallel`. Runtime dependencies are strictly Pydantic and PyYAML (stdlib otherwise). Isolate tests with temporary homes and fake runners so suites never touch live auth, archives, or workstation state.
1. **Test behavior**: run `uv run --frozen --project dot pytest -q dot/tests/<test_file>.py` and cover changed paths and failure modes. Read [session compatibility](references/session-compatibility.md) before touching parser output, retention rules, or bundle schemas.
1. **Qualify**: run affected static checks (`AGENTS.md` sets full-gate and formatter-isolation boundaries).
1. **Check the right binary**: test checkout behavior via `uv run --frozen --project dot dot <command>`. When installation is in scope, run `mise run deploy` (`uv tool install` locked to `dot/uv.lock`) and verify `dot --version` plus the changed command (`mise run doctor` checks workstation health, not repo code).

## Source and test map

Modules live in `dot/src/fmind_dot/` and tests in `dot/tests/` (`test_<module>.py` unless noted; `rg -l <symbol> dot/tests` finds others).

- `cli.py`, `command.py`, `state.py`, `config.py`, `process.py`, `private_files.py`, `reporting.py` → `test_cli.py`, `test_config.py`, `test_process.py`: stdlib `argparse`; `cli.build_parser()` registers commands alphabetically via `Parser.group()` / `Parser.command()` with `handler(state, args)`, raising `UsageError` (exit 2) on invalid flag combinations. `command.FISH_COMPLETION` invokes `dot` with `_DOT_COMPLETE` so `command.candidates()` completes from the live parser without regenerating scripts.
- `auth.py`, `workstation.py`, `repository.py`, `orphan.py`, `trust.py` → `test_workstation.py`, `test_daily_workflows.py`, `test_orphan.py`, `test_trust.py`: synthetic provider probes only; never run live login/setup/prune as a test gate.
- `secrets.py` → `test_secrets.py`: rejects personal `UV_PUBLISH_TOKEN` (PyPI uses Trusted Publishing); synthetic fixtures only, never print secret values.
- `hooks.py` → `test_agent_hooks.py`.
- `system.py` (`dot doctor`, `dot completion`) → `test_system.py`: `COMPLETION_SOURCES` maps native generators (`binary` + `args`), bundled mise `<tool>.fish` (`package`), or default `<tool> completion fish` (`completions.path` is the only config key). Missing binaries and inactive shims skip cleanly; `agy` uses `dot_config/fish/completions/` and `acli` has none (dropped in 1.3.39); Atuin omits its AI `?` binding.
- `agent.py`, `agent_doctor.py`, `context_budget.py` → `test_agent_workflows.py`, `test_agent_doctor.py`, `test_context_budget.py`, `test_usage.py`, `test_session_query.py`.
- `archive/`: `parsers.py` → `test_agent_parsers.py`, `store.py` → `test_session_store.py`, `query.py` → `test_session_query.py`, `sync.py` → `test_agent_workflows.py`, `usage.py` & `pricing.py` → `test_usage.py`, `statistics.py` → `test_daily_workflows.py`; `test_archive_transaction.py` (replacement/retention) and `test_usage_periods.py` (dedup, model switches, date windows, legacy recapture).

## Documentation

- [Project tasks](../../../mise.toml) · [package config](../../../dot/pyproject.toml) · [releases](https://github.com/fmind/dot/releases) · [changelog](https://github.com/fmind/dot/blob/main/CHANGELOG.md)
- Companion skills: [chezmoi](../chezmoi/SKILL.md), [dot-release](../dot-release/SKILL.md).
