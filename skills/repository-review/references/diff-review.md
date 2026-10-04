# Diff Review Procedure

Use for a diff, patch, branch, PR, or self-review; shared candidate, intent, risk, verification, severity, and authorization rules live in [repository-review](../SKILL.md).

1. **Resolve the target**: read the request, issue, spec, and change description; record whether the candidate is a dirty tree, local commit, or remote pull-request head, with its base and head.
1. **Inventory the delta**: start with `git diff --stat` and `git diff --name-status` for the selected revisions or index, then read complete patches by path with `git diff ... -- <path>`. Use `rg -n` to locate callers and read the relevant source ranges. Track reviewed paths so smaller reads still cover the requested scope; inspect generator inputs and lockfile changes when relevant rather than dumping every generated line or silently excluding them.
1. **Read tests first**: determine what behavior the candidate claims, whether the tests can fail for that defect class, and which requirements stay unproved. When cheap, prove it with one temporary mutation in a scratch copy or worktree; a mutation that stays green is a missing-test finding.
1. **Trace intended versus implemented**: map permissions, user journeys, data rules, failure semantics, and operational promises to concrete code paths and tests.
1. **Classify scope**: compare every changed dependency, config, public API, generated artifact, and unrelated-looking hunk with the stated contract and its real call or build path.
   - Classify it as **keep** (necessary and connected), **split** (independently valuable or unrelated), or **justify** (real but non-obvious coupling).
   - Path names alone do not prove scope creep; never stage, revert, discard, or rewrite the candidate because a detector labels a path unrelated.
1. **Report**: verify and rank findings with the shared rules, quoting the file and line that make each one real. A finding can use this compact shape:

   ```text
   [P1] Short imperative title — path/to/file.ext:line
   Evidence: the exact behavior or code path.
   Impact: who or what fails, under which condition.
   Reproduction: the smallest command, scenario, or trace.
   Correction: the minimum direction, without implementing it.
   ```

## Sources

- Adapted from [agent-skills code-review-and-quality](https://github.com/addyosmani/agent-skills/blob/1401c8b8030e023baeebb31781a6653fe8e93026/skills/code-review-and-quality/SKILL.md), [gstack review](https://github.com/garrytan/gstack/blob/960c3a8d6c4d14cb4c5e551a8847f8ec7c4267df/review/SKILL.md), [pm-skills intended-vs-implemented](https://github.com/phuryn/pm-skills/blob/18468a95b427e70e258b51389796367c6f684e7d/pm-ai-shipping/skills/intended-vs-implemented/SKILL.md), [codebase design](https://github.com/mattpocock/skills/blob/84fdeffd12f2ee307994d1eb6feb48173b6e0502/skills/engineering/codebase-design/SKILL.md).
