# Seeded-Defect Reviewer Calibration

Verify in a **fresh session** that a reviewer subagent catches target defect classes without nitpicking clean controls on the production `VERDICT / SUMMARY / FINDINGS / DELETIONS / UNVERIFIED` contract. Follow [agent evaluation](../../agent-frameworks/references/evaluation/GUIDE.md) (`>= 3` paired trials per prompt revision).

## Calibration Matrix

Create synthetic fixtures inside a clean `/var/tmp` sandbox directory (never customer data in public repos) so the fixture files stay inside the active workspace root under `allowNonWorkspaceAccess: false`:

1. **Seeded defect cases (`>= 2` distinct rubric classes)**: plant concrete flaws per lens (e.g., shell interpolation + hardcoded dummy token for `security`; a `600`-LOC module + tautological mock for `code`; em dashes + prose backticks + raw unformatted wall for `human`).
1. **Clean controls (`>= 2` clean edge cases)**: fix those exact flaws cleanly, including valid edge cases covered by `## Do Not Flag` (e.g., short plain 1:1 email for `human`; private `noindex` app without `sitemap.xml` for `web`).

## Headless Production-Contract Probe

Run headless from the sandbox without overriding the subagent's `## Output Contract` (or use [headless-review](../../agy/references/headless-review/GUIDE.md) only when testing JSON pipelines), confining file reads to the sandbox:

```bash
sandbox=$(mktemp -d /var/tmp/subagent-cal.XXXXXX)
bad_out=$(mktemp /var/tmp/subagent-bad.XXXXXX)
good_out=$(mktemp /var/tmp/subagent-good.XXXXXX)
# Populate $sandbox/bad.py and $sandbox/good.py before running:

(cd "$sandbox" && agy --agent fmind-review-code --print-timeout 5m --output-format json \
  --settings '{"allowNonWorkspaceAccess":false}' \
  -p "Review bad.py read-only using your Output Contract.") > "$bad_out" &&
  jq -er '.status == "SUCCESS" and (.finished_reason // null) == null and (.response | test("VERDICT: (BLOCK|REVISE)"))' "$bad_out" >/dev/null

(cd "$sandbox" && agy --agent fmind-review-code --print-timeout 5m --output-format json \
  --settings '{"allowNonWorkspaceAccess":false}' \
  -p "Review good.py read-only using your Output Contract.") > "$good_out" &&
  jq -er '.status == "SUCCESS" and (.finished_reason // null) == null and (.response | test("VERDICT: PASS")) and (.response | test("FINDINGS: none"))' "$good_out" >/dev/null
```

Require across `>= 3` fresh-session trials:

- Zero writes to the fixture directory (`mtime` / checksum unchanged).
- `bad_out` returns `VERDICT: BLOCK` or `REVISE` and cites every planted defect with accurate `loc:`.
- `good_out` returns `VERDICT: PASS` and `FINDINGS: none` (if it invents nitpicks, add that false-positive class to `## Do Not Flag` rather than bloating disclaimers).

## Multi-Case Regression Suites

When a project maintains `>= 5` custom roles or edits reviewer prompts frequently, pin an on-demand Python/`pytest` harness driving headless probes rather than running LLM calls per commit.
