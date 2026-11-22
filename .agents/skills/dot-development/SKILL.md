---
name: dot-development
description: "Develop fmind_dot CLI, with-secret, dot_tasks, and contract tests."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/.agents/skills/dot-development
  created: "2026-09-09"
  updated: "2026-11-22"
---

# Develop Dot

Modify `fmind_dot` while preserving CLI and installation contracts. [dot-cli](../../../skills/dot-cli/SKILL.md) operates the CLI; [python](../../../skills/python/references/foundation/GUIDE.md) and [argparse](../../../skills/python/references/argparse/GUIDE.md#defaults-for-new-clis) own Python packaging and CLI design.

## Workflow

1. **Locate the owner**: inspect the layout below and read current code before choosing a seam (`rg -l <symbol> dot/tests tests` finds test owners).
1. **Preserve the surface**: keep [CLI contracts](../../../skills/python/references/argparse/GUIDE.md#defaults-for-new-clis) and Fish completions intact unless changing them. Test config failures via the public CLI; `--help` and `doctor --headroom` must work without config loading.
1. **Use existing boundaries**: route config, streams, subprocesses, and fan-out through `State`, `Runner`, and `run_parallel`. Runtime dependency is strictly PyYAML (`@dataclass`, strict validators, stdlib). Isolate tests with temp homes and fake runners so suites never touch live auth or host state.
1. **Test and qualify**: run `uv run --frozen --project dot pytest -c dot/pyproject.toml -q dot/tests/<test_file>.py` covering changed paths and failure modes, plus `AGENTS.md` static checks (isolate formatters alongside unrelated edits).
1. **Check the right binary**: test checkout code via `uv run --frozen --project dot dot <command>`. When installation is in scope, run `mise run deploy` (`uv tool install` locked to `dot/uv.lock`) and verify `dot --version` plus the changed command (`mise run doctor` checks workstation health, not checkout code).

## Layout and seams

- **Directories**: `dot/src/fmind_dot/` holds the runtime CLI; `dot/dot_tasks/` holds repo maintenance tasks; `dot/tests/` holds CLI and task unit tests (`test_<module>.py` when 1:1); root `tests/` holds chezmoi, Fish, starter, and skill contract tests.
- **CLI & completions**: `cli.build_parser()` registers subcommands alphabetically via `Parser.command()` / `Parser.group()` with `handler(state, args)` raising `UsageError` (exit `2`). `command.FISH_COMPLETION` invokes `dot` with `_DOT_COMPLETE` for live completion, and `mise run completions` refreshes generated Fish completions.
- **Auth & `with-secret`**: test provider auth with synthetic probes only (never live login as a test gate). `with-secret` (`~/.local/bin/with-secret`) injects secrets in child env only and rejects `UV_PUBLISH_TOKEN` (PyPI uses Trusted Publishing).

## Documentation

- [Project tasks](../../../mise.toml) · [package config](../../../dot/pyproject.toml) · [releases](https://github.com/fmind/dot/releases) · [changelog](https://github.com/fmind/dot/blob/main/CHANGELOG.md)
- Companion skills: [chezmoi](../chezmoi/SKILL.md), [dot-release](../dot-release/SKILL.md).
