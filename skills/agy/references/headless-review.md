---
name: headless-review
description: "Run a structured headless agy review with a JSON schema and fail-closed exit checks."
---

# Structured Headless Reviews

Run this from the repository to review, using its existing account and selected model. The [object schema](agy/references/review.schema.json) constrains the report, not tool permissions; the no-edits prompt is an instruction, not filesystem isolation. Use a disposable snapshot for stronger separation from ongoing edits.

```bash
agy_review=$(mktemp /var/tmp/agy-review.XXXXXX)
agy --print-timeout 20m --output-format json \
  --json-schema ~/.agents/skills/agy/references/agy/references/review.schema.json \
  -p 'Review the working-tree diff for verified defects. Do not edit files. Return findings, checks actually run, and unresolved gaps.' \
  > "$agy_review" &&
  jq -e '.status == "SUCCESS" and (.finished_reason // null) == null and (.structured_output | type) == "object"' "$agy_review" >/dev/null
```

Consume the result only when all four hold: exit code 0, `status` is `SUCCESS`, `finished_reason` is absent, and `structured_output` is an object. Verified on agy 1.5.2: a normal run returns `status: SUCCESS` with no `finished_reason`, while a `--print-timeout` cut-off exits 3 with `status: ERROR`, `finished_reason: print_timeout`, partial output, a `[agy] print timeout after ...` line, and an `AGY_ERROR: {...}` line on stderr (since 1.5.0). `finished_reason` appears only when a turn ends early (`print_timeout`, `interrupted`, or `error`; since 1.4.11).

Other failures: model or agent errors also exit 3 with an `AGY_ERROR` line; actions refused by permissions are soft-denied, keep exit 0, and appear in `denied_actions`. `--json-schema` accepts only an object-root schema string or file and exits 1 otherwise; an unknown `--agent <name>` in `-p` mode also exits 1, and subagent questions are skipped in `-p` runs so subagents do not hang.

Pass `--print-timeout` explicitly: the default (`0s`) waits for the turn and, since 1.5.0, for its background tasks, with no hidden cap. For several turns in one process, use `--input-format stream-json --output-format stream-json` and read one `result` event per turn; its `usage` is cumulative. A full review of a large working tree took about 15 minutes in testing. Keep results local, choose a distinct output file for concurrent runs, and preserve stderr diagnostics. Record `usage` separately from estimated interactive-session statistics; reported tokens do not establish a monetary charge. See [headless mode](https://antigravity.google/docs/cli/headless/) and `agy changelog`.
