---
name: headless-review
description: "Run a structured headless agy review with a JSON schema and fail-closed exit checks."
---

# Structured Headless Reviews

Run this from the repository to review, using its existing account and selected model. The [object schema](agy/references/review.schema.json) constrains the report, not tool permissions; the no-edits prompt is an instruction, not filesystem isolation. Use a disposable snapshot for stronger separation from ongoing edits.

```bash
agy --agent code-reviewer --print-timeout 20m --output-format json \
  --json-schema ~/.agents/skills/agy/references/agy/references/review.schema.json \
  -p 'Review the working-tree diff for verified defects. Do not edit files. Return findings, checks actually run, and unresolved gaps.' \
  > /var/tmp/agy-review.json &&
  jq -e '.status == "SUCCESS" and (.structured_output | type) == "object"' /var/tmp/agy-review.json >/dev/null
```

Require a zero process exit code **and** an object `structured_output` before consuming it: on a print timeout agy still reports `status: SUCCESS` and exit 0 with partial output, but omits `structured_output`. Model or agent failures exit 3 with an `AGY_ERROR: {...}` line on stderr; actions refused by permissions are soft-denied, keep exit 0, and appear in `denied_actions`. Since 1.2.14, `--json-schema` accepts only an object-root schema string or file and exits 1 otherwise. Pass `--print-timeout` explicitly: 1.2.6 made the default unlimited although the headless page still says 5 minutes. For several turns in one process, use `--input-format stream-json --output-format stream-json` and read one `result` event per turn; its `usage` is cumulative. A full review of a large working tree took about 15 minutes in testing. Keep results local, choose a distinct output file for concurrent runs, and preserve stderr diagnostics. Record `usage` separately from estimated interactive-session statistics; reported tokens do not establish a monetary charge. See [headless mode](https://antigravity.google/docs/cli/headless/).

The `code-reviewer` role and tool allowlist rules live in the [agy guide](agy/GUIDE.md#managed-custom-agents).
