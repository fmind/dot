---
name: diff-review
description: "Review a diff, branch, or PR read-only: test strength, scope creep, and ranked findings."
---

# Diff Review

Review a diff, patch, branch, PR, or self-review in [full-review](../SKILL.md) `report` mode (read-only, no repo inventory or remote actions unless asked), ranking findings by [severity](../SKILL.md#severity) against the exact base and head.

1. **Resolve base and head**: record dirty tree, local commit, or PR head, and read full patches per changed path (including generator inputs and locks).
1. **Test the tests**: check whether tests fail for the claimed defect class; when cheap, verify with a one-line mutation in a scratch copy/worktree ([mutation-tests.md](../../python-stack/references/python-testing/references/mutation-tests.md)—surviving mutations are findings).
1. **Classify scope**: tag each changed dependency, config, public API, artifact, and suspect hunk as **keep**, **split**, or **justify** (never revert or restage hunks automatically).
1. **Audit sensitive paths**: route authz, upload, deserialization, subprocess, credential, and agent-tool diffs through [code-review](../../code-security/references/code-review/GUIDE.md).
1. **Verify proportionately**: skip builds/tests unless needed, reuse passing checks on unchanged inputs, run full gates only for cross-cutting risk or qualification, and isolate write-formatters on dirty trees ([dirty-tree rule](../../mise/SKILL.md#gotchas)).

## Sources

- Adapted from [agent-skills code-review-and-quality](https://github.com/addyosmani/agent-skills/blob/1401c8b8030e023baeebb31781a6653fe8e93026/skills/code-review-and-quality/SKILL.md) and [gstack review](https://github.com/garrytan/gstack/blob/960c3a8d6c4d14cb4c5e551a8847f8ec7c4267df/review/SKILL.md).
