# Seeded-Defect Reviewer Calibration

Verify in a **fresh session** that a reviewer supagent catches target defect classes, cites `rule: <Rubric #N | doc:line>`, passes clean controls without nitpicking, and fails closed (`VERDICT: BLOCK`) on unreadable primary targets under the production `VERDICT / SUMMARY / FINDINGS / DELETIONS / UNVERIFIED` contract. Run **1 paired probe** (seeded defect + clean control) for routine prompt edits; reserve `>= 3` paired trials ([agent evaluation](../../agent-frameworks/references/evaluation/GUIDE.md)) as an optional stability check for major rewrites or on request.

## Calibration Matrix

Create synthetic fixtures inside a clean `/var/tmp` sandbox directory (never customer data in public repos) so fixture files stay inside the active workspace root under `allowNonWorkspaceAccess: false`:

1. **Seeded defect cases (`>= 2` distinct `P0`/`P1` rubric rules)**: plant concrete `P0`/`P1` flaws per lens (e.g., shell interpolation for `security`; non-atomic in-place file write + swallowed exception for `code`; `"Distills Book X"` name-dropping + mixed multi-discipline rubric for `supagent`).
1. **Clean controls (`>= 2` clean edge cases)**: fix those exact flaws cleanly, including valid edge cases covered by `## Do Not Flag` (e.g., pure Python library `pyproject.toml` without `[project.scripts]` for `python`; sourced shell helper library without `set -eu` for `shell`; short plain 1:1 email for `human`; private `noindex` app without `sitemap.xml` for `frontend`).
1. **Unreadable-target fail-closed probe**: point the reviewer at a nonexistent absolute path (`$sandbox/does_not_exist.py`) and verify it returns `VERDICT: BLOCK` instead of failing open with `PASS`.

## Headless Production-Contract Probe

Because `excludeDefaultComponents: true` strips workspace CWD and `agy` CLI `read_file` requires absolute paths, **always pass absolute fixture paths (`"$sandbox/..."`)** in `-p` (for visual/web roles or external diff/log bundles under `allowNonWorkspaceAccess: false`, follow the `$render_dir` + `--add-dir` recipe in [headless-review](../../agent-harnesses/references/headless-review/GUIDE.md)):

```bash
sandbox="$(cd "$(mktemp -d /var/tmp/subagent-cal.XXXXXX)" && pwd -P)"
trap 'rm -rf -- "$sandbox"' EXIT
schema=~/.agents/skills/agent-harnesses/references/headless-review/references/review.schema.json
# Populate $sandbox/bad.py and $sandbox/good.py first (for repo-local <org>-review-*
# or un-applied roles, copy the compiled agent into $sandbox/.agents/agents/):

(cd "$sandbox" && agy --agent fmind-review-code --model gemini-4-hydrogen --effort medium --print-timeout 2m --output-format json \
  --sandbox --disable-slash-commands --settings '{"allowNonWorkspaceAccess":false}' \
  --json-schema "$schema" \
  -p "Audit $sandbox/bad.py read-only strictly against your Audit Rubric and Output Contract.") |
  jq -er '.status == "SUCCESS" and (.finished_reason // null) == null and ((.denied_actions // []) | length == 0) and (.structured_output.verdict | IN("BLOCK", "REVISE")) and ([.structured_output.findings[].rule | test("Rubric #")] | any)' >/dev/null

(cd "$sandbox" && agy --agent fmind-review-code --model gemini-4-hydrogen --effort medium --print-timeout 2m --output-format json \
  --sandbox --disable-slash-commands --settings '{"allowNonWorkspaceAccess":false}' \
  --json-schema "$schema" \
  -p "Audit $sandbox/good.py read-only strictly against your Audit Rubric and Output Contract.") |
  jq -er '.status == "SUCCESS" and (.finished_reason // null) == null and ((.denied_actions // []) | length == 0) and .structured_output.verdict == "PASS" and (.structured_output.findings | length == 0)' >/dev/null

(cd "$sandbox" && agy --agent fmind-review-code --model gemini-4-hydrogen --effort medium --print-timeout 2m --output-format json \
  --sandbox --disable-slash-commands --settings '{"allowNonWorkspaceAccess":false}' \
  --json-schema "$schema" \
  -p "Audit $sandbox/does_not_exist.py read-only strictly against your Audit Rubric and Output Contract.") |
  jq -er '.status == "SUCCESS" and (.finished_reason // null) == null and ((.denied_actions // []) | length == 0) and .structured_output.verdict == "BLOCK"' >/dev/null
```

Verify on the fresh-session probe (and optionally across `>= 3` trials on major rewrites):

- Zero writes to the fixture directory (`mtime` / SHA-256 unchanged).
- `bad.py` returns `BLOCK` or `REVISE`, cites every planted defect with accurate `loc:` and `rule: Rubric #<N>`, and invents zero unwritten standards.
- `good.py` returns `PASS` and `findings: []` (if it invents nitpicks, add that false-positive class to `## Do Not Flag` rather than bloating disclaimers).
- `does_not_exist.py` returns `BLOCK` (never `PASS` on uninspected targets).

## Multi-Case Regression Suites

When a project maintains `>= 5` custom roles or edits reviewer prompts frequently, pin an on-demand Python harness driving headless probes rather than running LLM calls per commit. In `fmind/dot`, run `mise run test:supagents:live` (defaults to `--model gemini-4-hydrogen --effort medium`; pass `--role code --effort low` for a faster smoke run; `--list` prints built-in suites offline; the automated harness requires `>= 1` expected blocking `Rubric #N` citation per seeded defect).
