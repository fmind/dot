---
name: smoke
description: "Smoke-test every repo task and CLI command; warnings count as failures."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/smoke
  created: "2026-10-04"
  updated: "2026-10-04"
---

# Smoke

Prove that everything a repository exposes still runs: each task, each CLI command, and each documented example, with a matrix the user can trust. Warnings count as failures. [quality-assurance](../quality-assurance/SKILL.md) owns risk-based campaigns over user journeys; [repository-review](../repository-review/SKILL.md) owns code findings. Fix defects only when the request includes fixing them.

## Workflow

1. **Baseline and isolation**: record `git status --short`. Tasks that format, lock, or generate files mutate the tree; with unrelated work present, run them in a snapshot per [git-worktree](../git-worktree/SKILL.md) and report their diff instead of leaving it behind.
1. **Discover**: list every entry point and read each command before running it; never classify by name alone.

   ```bash
   mise tasks --json --hidden | jq -r '.[] | select(.global | not) | [.name, ((.run // []) | join(" && "))] | @tsv'
   MISE_TASK_QUIET=false mise run -n <task>  # print the resolved command; quiet settings hide it
   jq -r '.scripts // {} | keys[]' package.json
   just --summary; make -pRrq : 2>/dev/null | grep -E '^[a-zA-Z0-9_.-]+:' | cut -d: -f1 | sort -u
   ```

   Add CLI entry points from `[project.scripts]`, `bin` fields, and `scripts/`, plus the commands quoted in `README.md` and CI workflows.
1. **Classify**: _safe_ (check, lint, test, local build, docs build), _mutating_ (format, fix, lock, generate: snapshot only), _service_ (serve, dev, watch: start under a timeout, probe health, stop it), and _external_ (deploy, release, publish, push, upgrade, login, prune, paid or networked writes). Run an external task only with explicit authority and its `--dry-run` when it has one; otherwise list it as skipped with the reason.
1. **Run tasks**: start with the repository's aggregate gate (`mise run all`, `check`, `test`), then each remaining task individually so failures stay attributable. Close stdin, bound time, keep logs, and force tasks whose cached outputs would skip them.

   ```bash
   mise run --force --timeout 10m <task> </dev/null >"$log" 2>&1; echo "exit=$?"
   ```

1. **Walk CLIs**: run `--help` on every command and subcommand recursively (Typer and Click list them under `Commands:`), then each read-only command (`status`, `list`, `show`, `doctor`, `validate`, any `--dry-run`) with representative arguments. Parse `--json` output with `jq`; a malformed document is a failure. Error paths count too: a bad argument must exit nonzero with a clear message, not a traceback.
1. **Treat warnings as failures**: scan each log for `warning`, `deprecat`, `WARN`, pytest's warnings summary, `Traceback`, and skipped tests; a warning passes only with a tracked, explained exception. Look at intentionally quiet tasks as well; quiet output must not hide a nonzero exit.
1. **Report the matrix**: entry point, class, exit code, duration, warnings, and note (fixed, skipped with reason, or failed with the first useful error line). Confirm that the tested snapshot equals the working tree after the last fix, and rerun only what a fix invalidated.

## Gotchas

- **Interactive prompts** hang without a terminal: closed stdin plus `--timeout` turns them into a recorded failure; prefer the tool's `--yes` only when its effect is safe.
- **Dependencies run twice**: `depends` re-runs prerequisites; reuse a passing result when inputs did not change instead of serial re-execution.
- **Environment**: mise `[env]`, `.env`, and `CI=true` change behavior; run with the repository's defaults and note any variable you set.
- **Host-only checks**: a task skipped for a missing optional tool is "not run", not "passed".

## Documentation

- [mise run](https://mise.jdx.dev/cli/run.html) · [mise tasks](https://mise.jdx.dev/tasks/)
- Companion skills: [mise](../mise/SKILL.md) (task vocabulary), [cli-development](../cli-development/SKILL.md) (CLI contracts), [systematic-debugging](../systematic-debugging/SKILL.md) (root causes).
