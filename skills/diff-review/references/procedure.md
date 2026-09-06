# Diff Review Procedure

Read for the detailed campaign, protocol, or reporting requirements when the task needs them.

1. **Resolve the target**: Read the request, issue, spec, and change description; record base, head, and whether the candidate is a dirty tree, local commit, or remote pull-request head. Preserve staged, unstaged, and untracked work.
1. **Inventory the delta**: Inspect changed files, generated artifacts, dependency or schema changes, and the nearby code that holds the invariants; never review the diff in isolation.
1. **Read tests first**: Determine what behavior the candidate claims, whether the tests can fail for that defect class, and which requirements stay unproved.
1. **Trace intended versus implemented**: Map permissions, user journeys, data rules, failure semantics, and operational promises to concrete code paths and tests.
1. **Review by risk**: Weigh correctness, data integrity, authorization, input boundaries, concurrency, resource lifecycle, error propagation, compatibility, migration, performance, observability, and rollback in proportion to the change.
1. **Classify scope**: Compare every changed dependency, config, public API, generated artifact, and unrelated-looking hunk with the stated contract and its real call or build path.
   - Classify it as **keep** (necessary and connected), **split** (independently valuable or unrelated), or **justify** (real but non-obvious coupling).
   - Path names alone do not prove scope creep; never stage, revert, discard, or rewrite the candidate because a detector labels a path unrelated.
1. **Verify each finding**: Reproduce it by code tracing, a focused test, or a safe temporary experiment, and quote the file and line that make it real.
1. **Run proportional checks**: Start with focused tests and static analysis, and record which candidate each result covers.
1. **Gate when proportionate**: Run the full gate (`mise run all`); if the tree carries unrelated changes and the gate write-formats, run it in an isolated working-tree copy containing the candidate edits or fall back to `mise run check` and `mise run test` (see [mise](../mise/SKILL.md)).
1. **Calibrate**: Discard preferences and speculation; rank what remains by user impact, exploitability, data loss, regression likelihood, and confidence. Do not manufacture findings to make the review look useful.
1. **Report**: Lead with findings ordered by severity, or say there are none and list test and proof gaps; end with the target identity, checks run, and residual risks. Other review skills reuse this scale:
   - **P0**: immediate security breach, irreversible data loss, or broad outage risk.
   - **P1**: likely correctness, security, or availability defect that should block merge.
   - **P2**: material edge-case, maintainability, performance, or test defect worth fixing before or soon after merge.
   - **P3**: minor issue, reported only when the user asked for an exhaustive review.

   ```text
   [P1] Short imperative title — path/to/file.ext:line
   Evidence: the exact behavior or code path.
   Impact: who or what fails, under which condition.
   Reproduction: the smallest command, scenario, or trace.
   Correction: the minimum direction, without implementing it.
   ```

## Sources

- Adapted from [agent-skills code-review-and-quality](https://github.com/addyosmani/agent-skills/blob/d2478bf0c73a6357df39a3ed6aff16acaa218843/skills/code-review-and-quality/SKILL.md), [gstack review](https://github.com/garrytan/gstack/blob/960c3a8d6c4d14cb4c5e551a8847f8ec7c4267df/review/SKILL.md), [pm-skills intended-vs-implemented](https://github.com/phuryn/pm-skills/blob/18468a95b427e70e258b51389796367c6f684e7d/pm-ai-shipping/skills/intended-vs-implemented/SKILL.md), [codebase design](https://github.com/mattpocock/skills/blob/84fdeffd12f2ee307994d1eb6feb48173b6e0502/skills/engineering/codebase-design/SKILL.md).
