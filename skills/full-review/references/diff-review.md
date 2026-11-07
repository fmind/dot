---
name: diff-review
description: "Review a diff, branch, or PR read-only: test strength, scope creep, and ranked findings."
---

# Diff Review

Review a diff, patch, branch, PR, or self-review in [full-review](../SKILL.md) `report` mode: no repository inventory, fixes, or remote actions unless the user asks. Rank findings by [severity](../SKILL.md#severity) and tie every finding and check to the exact base and head.

1. **Resolve the candidate**: record whether it is a dirty tree, local commit, or remote PR head, with its base and head; read complete patches by path, including generator inputs and lockfile changes, so every changed path is reviewed.
1. **Test the tests**: decide which behavior the candidate claims and whether its tests can fail for that defect class. When cheap, prove it with one temporary mutation in a scratch copy or worktree (Python: [mutation tests](../../python-stack/references/python-testing/references/mutation-tests.md)); a mutation that stays green is a missing-test finding.
1. **Classify scope**: compare every changed dependency, config, public API, generated artifact, and unrelated-looking hunk with the stated contract, and mark it **keep** (necessary and connected), **split** (independently valuable or unrelated), or **justify** (real but non-obvious coupling). Path names alone do not prove scope creep; never stage, revert, discard, or rewrite the candidate because a detector labels a path unrelated.
1. **Trace security risk**: changes to authorization, uploads, deserialization, subprocesses, credentials, or agent tools go through [code-review](../../code-security/references/code-review/GUIDE.md).
1. **Verify proportionately**: a read-only review needs no build or test run by default. Reuse passing results while inputs are unchanged, run the full gate only for explicit qualification or cross-cutting risk, and isolate write-formatting checks on a dirty tree ([dirty-tree rule](../../mise/SKILL.md#gotchas)).

## Sources

- Adapted from [agent-skills code-review-and-quality](https://github.com/addyosmani/agent-skills/blob/1401c8b8030e023baeebb31781a6653fe8e93026/skills/code-review-and-quality/SKILL.md) and [gstack review](https://github.com/garrytan/gstack/blob/960c3a8d6c4d14cb4c5e551a8847f8ec7c4267df/review/SKILL.md).
