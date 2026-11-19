---
name: headless-review
description: "Run a structured headless agy review with JSON schema and fail-closed exit checks."
---

# Structured Headless Reviews

Run from the target repository; [review.schema.json](references/review.schema.json) mirrors `_reviewer.md`'s Output Contract (`verdict`, `P0`–`P2` `findings`, `deletions`, `unverified`). `fmind-review-*` roles are strictly shell-free and MCP-free (`commandExecutionPolicy: "off"`, `inheritMcp: false`): 33 roles inherit air-gapped `_reviewer.md`, and `fmind-review-factcheck` inherits `_reviewer_web.md` (sanitized public web lookup). Because `agy` 1.5.x CLI binds `read_file` + `finish` on air-gapped roles (plus `search_web` on `_reviewer_web`), run deterministic gates first and write the frozen diff, touched file list, gate logs, and pre-rendered PNG/DOM captures into a temp directory exposed read-only via `--add-dir`:

```bash
render_dir="$(cd "$(mktemp -d /tmp/agy-review.XXXXXX)" && pwd -P)"
agy_review="$render_dir/review.json"
git diff > "$render_dir/working.diff"
git status --short > "$render_dir/files.txt"
agy --agent fmind-review-code --print-timeout 20m --output-format json \
  --sandbox --settings '{"allowNonWorkspaceAccess":false}' --add-dir "$render_dir" \
  --json-schema ~/.agents/skills/agy/references/headless-review/references/review.schema.json \
  -p "Read $render_dir/working.diff, $render_dir/files.txt, and the referenced files in $PWD for verified defects against your Audit Rubric." \
  > "$agy_review" &&
  jq -e '.status == "SUCCESS" and (.finished_reason // null) == null and (.structured_output.verdict | IN("PASS", "REVISE", "BLOCK"))' "$agy_review" >/dev/null
```

Pair `--agent fmind-review-<role>` with `--sandbox --settings '{"allowNonWorkspaceAccess":false}'` on untrusted repos (and launch `fmind-review-factcheck` from an isolated `/var/tmp/<sandbox>` dir holding sanitized extracts when auditing secret-bearing repos); remove `"$render_dir"` after extracting `"$agy_review"`. Require exit 0, `status == "SUCCESS"`, absent `finished_reason` (present only on `print_timeout`, `interrupted`, or `error` since 1.4.11), and an object `structured_output`. On agy 1.5.2+, `--print-timeout` cut-offs and model/agent errors exit 3 with `status: ERROR` and stderr `AGY_ERROR: {...}` (1.5.0+); permission refusals stay exit 0 under `denied_actions`; non-object `--json-schema` or unknown `--agent` exits 1, and `-p` auto-skips subagent questions.

Always pass `--print-timeout` (default `0s` waits unboundedly for the turn and, since 1.5.0, background tasks; large repo reviews take ~15m). For multi-turn pipes, use `--input-format stream-json --output-format stream-json` (one `result` per turn, cumulative `usage`). Keep output files distinct per run, retain stderr, and track `usage` separately from interactive estimates ([headless docs](https://antigravity.google/docs/cli/headless/), `agy changelog`).
