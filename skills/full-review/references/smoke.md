---
name: smoke
description: "Smoke-test every repo task and CLI command; warnings count as failures."
---

# Smoke

Exercise every exposed repo task and CLI entry point, reporting a matrix (runs in [full-review](../SKILL.md) `report` mode unless fixes are requested).

1. **Discover**: inspect every mise task ([concise output](../../mise/references/task-conventions.md#concise-output) covers `quiet = true`), `[project.scripts]`, and `README.md`/CI commands before running:

   ```bash
   mise tasks ls --no-global --json --hidden | jq -r '.[] | [.name, ((.run // []) | join(" && "))] | @tsv'
   ```

1. **Gate side effects**: run external tasks (deploy, release, publish, push, upgrade, login, prune) only with approval and `--dry-run` (else mark skipped + reason); run mutating tasks (format, fix, lock, generate) in a snapshot; probe service tasks (serve, dev, watch) under a short timeout and kill only processes you spawned.
1. **Run tasks** (aggregate gate first, then each isolated with closed stdin and timeout), scanning logs even on exit 0 for `warning`, `deprecat`, `Traceback`, pytest warning summaries, and skipped tests:

   ```bash
   mise run --force --timeout 10m --report-file "$report" <task> </dev/null >"$log" 2>&1; echo "exit=$?"
   ```

1. **Walk CLIs**: test `--help` across subcommands, run read-only commands, validate `--json` with `jq`, and verify bad args exit non-zero cleanly without tracebacks.
1. **Report matrix**: entry point | exit code | warnings | status (`passed`, `failed`, or `skipped` with reason—skipped != passed).
