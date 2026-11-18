---
name: headless-review
description: "Run a structured headless agy review with JSON schema and fail-closed exit checks."
---

# Structured Headless Reviews

Run from the target repository; [review.schema.json](references/review.schema.json) mirrors `_reviewer.md`'s Output Contract (`verdict`, `P0`–`P2` `findings`, `deletions`, `unverified`). `fmind-review-*` roles strip file-edit and subagent-delegation tools while retaining sandboxed `run_command` (`commandExecutionPolicy: sandbox`) for `git diff`, linters/tests, benchmarks, and headless Chrome/Playwright checks (use a disposable snapshot when filesystem isolation from concurrent edits is needed):

```bash
agy_review=$(mktemp /var/tmp/agy-review.XXXXXX)
agy --agent fmind-review-code --print-timeout 20m --output-format json \
  --sandbox --settings '{"allowNonWorkspaceAccess":false}' \
  --json-schema ~/.agents/skills/agy/references/headless-review/references/review.schema.json \
  -p "Review the working-tree diff and touched files in $PWD for verified defects against your Audit Rubric. Do not edit files." \
  > "$agy_review" &&
  jq -e '.status == "SUCCESS" and (.finished_reason // null) == null and (.structured_output.verdict | IN("PASS", "REVISE", "BLOCK"))' "$agy_review" >/dev/null
```

Pair `--agent fmind-review-<role>` with `--sandbox --settings '{"allowNonWorkspaceAccess":false}'` on untrusted repos so the headless reviewer keeps read/search/web plus OS-sandboxed diagnostic commands and `finish` (`structured_output`) without file-edit tools (when visual/browser reviewers capture `/tmp` renders outside the repo, allocate `render_dir="$(cd "$(mktemp -d /tmp/agy-render.XXXXXX)" && pwd -P)"`, pass `--add-dir "$render_dir"`, direct `-p` to write temporary renders inside `"$render_dir"` so `read_file` can inspect them, and remove `"$render_dir"` on exit). Require exit 0, `status == "SUCCESS"`, absent `finished_reason` (present only on `print_timeout`, `interrupted`, or `error` since 1.4.11), and an object `structured_output`. On agy 1.5.2+, `--print-timeout` cut-offs and model/agent errors exit 3 with `status: ERROR` and stderr `AGY_ERROR: {...}` (1.5.0+); permission refusals stay exit 0 under `denied_actions`; non-object `--json-schema` or unknown `--agent` exits 1, and `-p` auto-skips subagent questions.

Always pass `--print-timeout` (default `0s` waits unboundedly for the turn and, since 1.5.0, background tasks; large repo reviews take ~15m). For multi-turn pipes, use `--input-format stream-json --output-format stream-json` (one `result` per turn, cumulative `usage`). Keep output files distinct per run, retain stderr, and track `usage` separately from interactive estimates ([headless docs](https://antigravity.google/docs/cli/headless/), `agy changelog`).
