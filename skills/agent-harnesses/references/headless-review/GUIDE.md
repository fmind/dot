---
name: headless-review
description: "Structured headless agy review with JSON schema and fail-closed exit checks."
---

# Structured Headless Reviews

Run from the target repository; [review.schema.json](references/review.schema.json) mirrors `_reviewer.md`'s Output Contract (`verdict`, `summary`, `P0`–`P2` `findings`, `deletions`, `unverified`). Host tool allowlists and permission boundaries live in [cross-harness-agents](../cross-harness-agents.md#permission-limits).

- **Preflight shadowing check**: run `dot context --check` against the repository root and walk every directory from `$PWD` up to the git root refusing `.agents/agents`, `.agents/agents.json`, or `.github/agents` (including symlinks; project profiles silently shadow global roles).
- **Capture frozen evidence**: run deterministic gates first and write diffs, file manifests, `--help`, gate logs, and PNG/DOM renders to a temp dir exposed read-only via `--add-dir`, passing **absolute file paths** in `-p` (clean-context `agy` reviewers strip CWD and bind `read_file` only; unreadable primary targets fail closed with `BLOCK`):

```bash
set -eu
repo_root="$(cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd -P)" && pwd -P)"
dot context --check --project "$repo_root"
walk_dir="$(pwd -P)"
while :; do
  for suspect in "$walk_dir/.agents/agents" "$walk_dir/.agents/agents.json" "$walk_dir/.github/agents"; do
    if [ -e "$suspect" ] || [ -L "$suspect" ]; then
      printf 'refusing untrusted repo agent path: %s\n' "$suspect" >&2
      exit 1
    fi
  done
  [ "$walk_dir" = "$repo_root" ] || [ "$walk_dir" = "/" ] && break
  walk_dir="$(dirname "$walk_dir")"
done
render_dir="$(cd "$(mktemp -d /tmp/agy-review.XXXXXX)" && pwd -P)"
trap 'rm -rf -- "$render_dir"' EXIT INT TERM
agy_review="$render_dir/review.json"
git diff > "$render_dir/working.diff"
git status --short > "$render_dir/files.txt"
agy --agent fmind-review-code --model gemini-4-hydrogen-medium --print-timeout 20m --output-format json \
  --sandbox --disable-slash-commands --settings '{"allowNonWorkspaceAccess":false}' --add-dir "$render_dir" \
  --json-schema ~/.agents/skills/agent-harnesses/references/headless-review/references/review.schema.json \
  -p "Read $render_dir/working.diff, $render_dir/files.txt, and referenced files under $PWD using absolute paths against your Audit Rubric." \
  > "$agy_review"
jq -e '.status == "SUCCESS" and (.finished_reason // null) == null and (.structured_output.verdict | IN("PASS", "REVISE", "BLOCK"))' "$agy_review" >/dev/null
```

- **Isolated `fmind-review-factcheck` recipe**: on secret-bearing repos, copy only sanitized extracts into a canonical `/var/tmp` sandbox, merge existing `~/.gemini/antigravity-cli/settings.json` `.permissions.deny` rules via `jq` with loopback + cloud-metadata `read_url`/`execute_url` denies (preventing `--settings` array replacement from dropping `$HOME` secret denies), and assert the fail-closed JSON verdict on separate statements under `set -eu`:

```bash
set -eu
fact_dir="$(cd "$(mktemp -d /var/tmp/agy-factcheck.XXXXXX)" && pwd -P)"
trap 'rm -rf -- "$fact_dir"' EXIT INT TERM
fact_settings="$(jq -cn --slurpfile base ~/.gemini/antigravity-cli/settings.json \
  '{allowNonWorkspaceAccess:false, permissions:{deny:(($base[0].permissions.deny // []) + [
    "read_url(localhost)","execute_url(localhost)","read_url(127.0.0.1)","execute_url(127.0.0.1)",
    "read_url([::1])","execute_url([::1])","read_url(0.0.0.0)","execute_url(0.0.0.0)",
    "read_url(169.254.169.254)","execute_url(169.254.169.254)",
    "read_url(metadata.google.internal)","execute_url(metadata.google.internal)"
  ] | unique)}}')"
# Copy sanitized draft extracts into "$fact_dir/extract.md", then run:
(cd "$fact_dir" && agy --agent fmind-review-factcheck --model gemini-4-hydrogen-medium --print-timeout 15m --output-format json \
  --sandbox --disable-slash-commands --settings "$fact_settings" \
  --json-schema ~/.agents/skills/agent-harnesses/references/headless-review/references/review.schema.json \
  -p "Fact-check $fact_dir/extract.md strictly against your Audit Rubric.") > "$fact_dir/review.json"
jq -e '.status == "SUCCESS" and (.finished_reason // null) == null and (.structured_output.verdict | IN("PASS", "REVISE", "BLOCK"))' "$fact_dir/review.json" >/dev/null
```

- **Fail-closed exit checks & `agy` 1.5.17 quirks**: top-level `agy --agent` ignores custom frontmatter `model:`, so pass `--model gemini-4-hydrogen-medium` explicitly (`--model gemini-4-hydrogen --effort medium` is equivalent; do not pair an effort-suffixed `--model` with `--effort`). Require exit `0`, `status == "SUCCESS"`, absent `finished_reason` (`print_timeout`/`interrupted`/`error`), and object `structured_output`. Always prefer `--json-schema` over plain JSON text: `agy` can duplicate plain `response` text around `{}` when `finish` fires, and `denied_actions` stays `null` even when `permissions.deny` blocks a read (rely on `_reviewer.md`'s fail-closed `BLOCK` on unreadable targets). `--print-timeout` and model/agent errors exit `3`; bad `--json-schema`, unknown `--model`, or unknown `--agent` exits `1`.
- **Timeouts & streaming**: always pass `--print-timeout` (default `0s` waits unboundedly; large repo reviews take ~15m). For multi-turn pipes, pair `--input-format stream-json --output-format stream-json` without `-p` (`--json-schema` persists across resumed `--conversation` turns). Keep output files distinct, retain stderr, and track `usage` separately ([headless docs](https://antigravity.google/docs/cli/headless/), `agy changelog`).
