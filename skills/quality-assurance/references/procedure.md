# Quality Assurance Procedure

Read for the detailed campaign, protocol, or reporting requirements when the task needs them.

1. **Resolve the candidate**: Record the requirement or spec, base and head or working-tree identity, environment, versions, and existing proof.
1. **Build the risk matrix**: Start from requirements, changed behavior, user journeys, and known failure modes; rank by impact, likelihood, detectability, reversibility, and change exposure, and cover the highest risk first.
1. **Choose the lightest layer**: Unit tests for logic, property or fuzz tests for wide input spaces, contract tests for interfaces, integration tests for owned boundaries, end-to-end tests for critical journeys.
1. **Prepare controlled state**: Create isolated data with explicit setup and teardown; confirm the test cannot mutate user or external state beyond the authorized scope.
1. **Run changed behavior first**: Exercise the success path, unhappy paths, boundaries, permissions, cancellation, retries, concurrency, and recovery the requirements promise.
1. **Test real presentation**: Prefer direct HTTP or API evidence; use a browser only for rendering, interaction, session state, or accessibility, driving it with [playwright](../playwright/SKILL.md) through roles and labels and verifying state after every action.
1. **Test non-functional risk**: Measure latency, load, resource use, resilience, security boundaries, and observability only where the matrix or spec requires; set the baseline and threshold first with [benchmark](../benchmark/SKILL.md).
1. **Run regression proof**: Execute the relevant package or subsystem suite before the full gate.
1. **Gate the candidate**: Run the full gate (`mise run all`); if the tree carries unrelated changes and the gate write-formats, run it in an isolated working-tree copy containing the candidate edits or fall back to `mise run check` and `mise run test` (see [mise](../mise/SKILL.md)).
1. **Retest fixes narrowly**: Reproduce the original failure, verify the fix, then rerun impacted journeys and the gate; avoid open-ended visual polishing loops.
1. **Report the matrix**: Record per case the risk and requirement, layer and environment, preconditions, steps or command, expected result, actual evidence, status (pass, fail, blocked, or not run), and cleanup with residual risk.
1. **Summarize**: Lead with blockers, then failures, passes, and untested boundaries with the authority or capability needed to test them; report the highest proven rung of the [proof ladder](../production-readiness/SKILL.md).

## Sources

- Adapted from [gstack QA](https://github.com/garrytan/gstack/blob/960c3a8d6c4d14cb4c5e551a8847f8ec7c4267df/qa/SKILL.md), [Anthropic webapp-testing](https://github.com/anthropics/skills/blob/f17010c9bb483898c1d9c9f42dde2b3a98889434/skills/webapp-testing/SKILL.md), [agent-skills browser testing](https://github.com/addyosmani/agent-skills/blob/d2478bf0c73a6357df39a3ed6aff16acaa218843/skills/browser-testing-with-devtools/SKILL.md).
