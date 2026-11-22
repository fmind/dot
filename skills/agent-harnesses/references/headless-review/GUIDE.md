---
name: headless-review
description: "Structured headless agy review with JSON schema and fail-closed exit checks."
---

# Structured Headless Reviews

Run from the target repository; [review.schema.json](references/review.schema.json) mirrors `_reviewer.md`'s Output Contract (`verdict`, `summary`, `P0`–`P2` `findings`, `deletions`, `unverified`).

- **Pre-capture deterministic evidence**: `fmind-review-*` roles are shell-free and MCP-free (`commandExecutionPolicy: "off"`, `inheritMcp: false`; all global roles inherit air-gapped `_reviewer.md` except `fmind-review-factcheck` on `_reviewer_web.md`). Because `agy` 1.5.x binds `read_file` + `finish` on air-gapped roles (plus `search_web` on `_reviewer_web`), run deterministic gates first and write the frozen diff, touched file list, directory manifests, `--help`, `vale --output=JSON`, gate logs, and PNG/DOM renders into a temp dir exposed read-only via `--add-dir`:

```bash
render_dir="$(cd "$(mktemp -d /tmp/agy-review.XXXXXX)" && pwd -P)"
agy_review="$render_dir/review.json"
git diff > "$render_dir/working.diff"
git status --short > "$render_dir/files.txt"
agy --agent fmind-review-code --print-timeout 20m --output-format json \
  --sandbox --settings '{"allowNonWorkspaceAccess":false}' --add-dir "$render_dir" \
  --json-schema ~/.agents/skills/agent-harnesses/references/headless-review/references/review.schema.json \
  -p "Read $render_dir/working.diff, $render_dir/files.txt, and the referenced files in $PWD for verified defects against your Audit Rubric." \
  > "$agy_review" &&
  jq -e '.status == "SUCCESS" and (.finished_reason // null) == null and (.structured_output.verdict | IN("PASS", "REVISE", "BLOCK"))' "$agy_review" >/dev/null
```

- **Isolation & cleanup**: pair `--agent fmind-review-<role>` with `--sandbox --settings '{"allowNonWorkspaceAccess":false}'` on untrusted repos (and launch `fmind-review-factcheck` from an isolated `/var/tmp/<sandbox>` dir holding sanitized extracts on secret-bearing repos); delete `"$render_dir"` after reading `"$agy_review"`.
- **Fail-closed exit checks**: require exit `0`, `status == "SUCCESS"` (`1.5.13+` reports `SUCCESS` when retries succeed), absent `finished_reason` (`print_timeout`/`interrupted`/`error` since `1.4.11`), and object `structured_output`. On `agy` 1.5.2+, `--print-timeout` and model/agent errors exit `3` (`status: ERROR`, stderr `AGY_ERROR: {...}`); permission refusals stay exit `0` under `denied_actions`; bad `--json-schema` or unknown `--agent` exits `1`, and `-p` auto-skips subagent questions.
- **Timeouts & streaming**: always pass `--print-timeout` (default `0s` waits unboundedly for the turn and background tasks; large repo reviews take ~15m). For multi-turn pipes, use `--input-format stream-json --output-format stream-json` (one `result` per turn, cumulative `usage`). Keep output files distinct, retain stderr, and track `usage` separately from interactive estimates ([headless docs](https://antigravity.google/docs/cli/headless/), `agy changelog`).
