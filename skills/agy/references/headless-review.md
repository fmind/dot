---
name: headless-review
description: "Run a structured headless agy review with JSON schema and fail-closed exit checks."
---

# Structured Headless Reviews

Run from the target repository; [review.schema.json](cli/references/review.schema.json) enforces output shape only, so use a disposable snapshot when filesystem isolation from concurrent edits is needed.

```bash
agy_review=$(mktemp /var/tmp/agy-review.XXXXXX)
agy --print-timeout 20m --output-format json \
  --json-schema ~/.agents/skills/agy/references/cli/references/review.schema.json \
  -p 'Review the working-tree diff for verified defects. Do not edit files. Return findings, checks actually run, and unresolved gaps.' \
  > "$agy_review" &&
  jq -e '.status == "SUCCESS" and (.finished_reason // null) == null and (.structured_output | type) == "object"' "$agy_review" >/dev/null
```

Require exit 0, `status == "SUCCESS"`, absent `finished_reason` (present only on `print_timeout`, `interrupted`, or `error` since 1.4.11), and an object `structured_output`. On agy 1.5.2, `--print-timeout` cut-offs and model/agent errors exit 3 with `status: ERROR` and stderr `AGY_ERROR: {...}` (1.5.0+); permission refusals stay exit 0 under `denied_actions`; non-object `--json-schema` or unknown `--agent` exits 1, and `-p` auto-skips subagent questions.

Always pass `--print-timeout` (default `0s` waits unboundedly for the turn and, since 1.5.0, background tasks; large repo reviews take ~15m). For multi-turn pipes, use `--input-format stream-json --output-format stream-json` (one `result` per turn, cumulative `usage`). Keep output files distinct per run, retain stderr, and track `usage` separately from interactive estimates ([headless docs](https://antigravity.google/docs/cli/headless/), `agy changelog`).
