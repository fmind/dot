---
name: dot-development
description: "Develop fmind/dot CLI, with-secret, session parsers, archives, dot_tasks, and repo contract tests."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/.agents/skills/dot-development
  created: "2026-09-09"
  updated: "2026-11-17"
---

# Develop Dot

Modify `fmind_dot` while preserving CLI, archive, and installation contracts. [dot-cli](../../../skills/dot-cli/SKILL.md) operates the installed CLI; [python-stack](../../../skills/python-stack/references/foundation/GUIDE.md) and [argparse](../../../skills/python-stack/references/argparse/GUIDE.md#defaults-for-new-clis) own generic Python and CLI design.

## Workflow

1. **Locate the owner**: check the map below and read current code before choosing a seam.
1. **Preserve the surface**: keep [CLI contracts](../../../skills/python-stack/references/argparse/GUIDE.md#defaults-for-new-clis) and Fish completions intact unless changing them. Test config failures through the public CLI; config-free paths (`--help`, `doctor --headroom`) must work when config loading fails.
1. **Use existing boundaries**: route config, streams, subprocesses, and fan-out through `State`, `Runner`, and `run_parallel`. Runtime dependency is strictly PyYAML (`@dataclass` + strict validators and stdlib otherwise). Isolate tests with temporary homes and fake runners so suites never touch live auth, archives, or workstation state.
1. **Test behavior**: run `uv run --frozen --project dot pytest -c dot/pyproject.toml -q dot/tests/<test_file>.py` and cover changed paths and failure modes. Read [session compatibility](references/session-compatibility.md) before touching parser output, retention rules, or bundle schemas.
1. **Qualify**: run affected static checks (`AGENTS.md` sets full-gate and formatter-isolation boundaries).
1. **Check the right binary**: test checkout behavior via `uv run --frozen --project dot dot <command>`. When installation is in scope, run `mise run deploy` (`uv tool install` locked to `dot/uv.lock`) and verify `dot --version` plus the changed command (`mise run doctor` checks workstation health, not repo code).

## Source and test map

Modules live in `dot/src/fmind_dot/` and tests in `dot/tests/` (`test_<module>.py` unless noted; `rg -l <symbol> dot/tests` finds others).

- `cli.py`, `command.py`, `state.py`, `config.py` (`policy.yaml`, `api-prices.yaml`), `process.py`, `private_files.py`, `reporting.py` → `test_cli.py`, `test_config.py`, `test_process.py`, `test_private_files.py`: stdlib `argparse`; `cli.build_parser()` registers the seven top-level commands (`context`, `doctor`, `login`, `pull`, `stats`, `status`, `trust`) alphabetically via `Parser.command()` (`Parser.group()` for `login`) with `handler(state, args)`, raising `UsageError` (exit 2) on invalid flag combinations. `command.FISH_COMPLETION` invokes `dot` with `_DOT_COMPLETE` so `command.candidates()` completes from the live parser without regenerating scripts.
- `auth.py`, `repository.py`, `trust.py`, `with_secret.py` → `test_system.py`, `test_repository.py`, `test_trust.py`, `test_with_secret.py`, `tests/test_fish.py`: synthetic provider probes only; never run live login as a test gate. `with_secret.py` (`~/.local/bin/with-secret`) injects per-process secrets without `argv` exposure and rejects personal `UV_PUBLISH_TOKEN` (PyPI uses Trusted Publishing).
- `system.py` (`dot doctor`) → `test_system.py`: inspects workstation tools, all five agent hosts, and archive sync/status.
- `agent.py` (`dot stats`), `context_budget.py` (`dot context`) → `test_agent_workflows.py`, `test_context_budget.py`, `test_usage.py`.
- `archive/`: `common.py`, `parsers.py`, and `sqlite_parsers.py` → `test_agent_parsers.py`, `store.py` → `test_session_store.py`, `sync.py` → `test_agent_workflows.py`, `usage.py` → `test_usage.py`.
- `dot/dot_tasks/` & root `tests/`: `completions.py`, `mise_locks.py`, `mise_refresh.py`, `release.py`, `skill_contracts.py`, `theme_pin.py` → `tests/test_bootstrap.py`, `dot/tests/{test_mise_locks,test_mise_refresh,test_release,test_contracts,test_theme_fonts}.py`; Fish completions run via `mise run completions` (`policy.yaml` `completions`, bundled mise `<tool>.fish`, or default `<tool> completion fish`, keeping `MANAGED_COMPLETIONS` (`"agy.fish"`) untouched) while chezmoi/Fish/starter/skill contracts live in root `tests/`.

## Documentation

- [Project tasks](../../../mise.toml) · [package config](../../../dot/pyproject.toml) · [Python argparse](https://docs.python.org/3/library/argparse.html) · [PyYAML](https://pyyaml.org/wiki/PyYAMLDocumentation) · [releases](https://github.com/fmind/dot/releases) · [changelog](https://github.com/fmind/dot/blob/main/CHANGELOG.md)
- Companion skills: [chezmoi](../chezmoi/SKILL.md), [dot-release](../dot-release/SKILL.md).
