---
name: smoke
description: "Smoke-test every repo task and CLI command; warnings count as failures."
---

# Smoke

Run everything a repository exposes and report a matrix. A smoke-only request runs this guide alone in [full-review](../../SKILL.md) `report` mode; fix only when asked.

1. **Discover**: list the tasks and read each command before running it (under mise `quiet = true`, see [concise output](../../../mise/references/task-conventions.md#concise-output) to print resolved commands). Add `[project.scripts]` entry points and the commands quoted in `README.md` and CI.

   ```bash
   mise tasks ls --no-global --json --hidden | jq -r '.[] | [.name, ((.run // []) | join(" && "))] | @tsv'
   ```

1. **Skip what needs authority**: external tasks (deploy, release, publish, push, upgrade, login, prune) run only with explicit authority and their `--dry-run` when they have one; otherwise list them as skipped with the reason. Mutating tasks (format, fix, lock, generate) run in a snapshot. Service tasks (serve, dev, watch) start under a short timeout, get a health probe, then stop: kill only the process you started.
1. **Run each task**: the aggregate gate first, then each task alone with stdin closed and a time bound. Exit 0 can still print warnings, so scan every log for `warning`, `deprecat`, `Traceback`, pytest's warnings summary, and skipped tests; the report file records each task's status and exit code.

   ```bash
   mise run --force --timeout 10m --report-file "$report" <task> </dev/null >"$log" 2>&1; echo "exit=$?"
   ```

1. **Walk CLIs**: run `--help` on every command and subcommand, then each read-only command; parse `--json` output with `jq`. A bad argument must exit nonzero with a clear message, not a traceback.
1. **Report the matrix**: entry point, exit code, warnings, and a note (failed, skipped with reason, or passed); skipped is not passed.
