---
name: quality-assurance
description: "Plan and run QA test campaigns over user journeys, failure modes, and release risks."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/quality-assurance
  created: "2026-08-08"
  updated: "2026-10-04"
---

# Quality Assurance

Run a risk-based test campaign over the actual feature journey. Keep one-diff review in [repository-review](../repository-review/SKILL.md); [agent-evaluation](../agent-evaluation/SKILL.md) owns stochastic model comparisons through project or provider runners.

## Workflow

1. **Resolve the candidate**: record the requirement or spec, base and head or working-tree identity, users, critical journeys, supported environments, versions, acceptance criteria, and existing proof.
1. **Build the risk matrix**: start from requirements, changed behavior, user journeys, and known failure modes; rank by impact, likelihood, detectability, reversibility, and change exposure, and cover the highest risk first. Reuse existing evidence only when identity and scope match.
1. **Choose the lightest layer**: unit tests for logic, property or fuzz tests for wide input spaces, contract tests for interfaces, integration tests for owned boundaries, end-to-end tests for critical journeys; add accessibility, resilience, or manual checks only where a risk needs them.
1. **Prepare controlled state**: use deterministic fixtures, isolated data, and local fakes by default, with explicit setup and teardown; confirm the test cannot mutate user or external state beyond the authorized scope, and declare real-service access, cost, and cleanup before crossing those boundaries.
1. **Exercise changed behavior first**: run the repository's `mise` test tasks, then the success path, unhappy paths, boundaries, permissions, cancellation, retries, concurrency, recovery, and platform variants the requirements promise; preserve failures and useful artifacts.
1. **Test real presentation**: prefer direct HTTP or API evidence; use a browser only for rendering, interaction, session state, or accessibility, driving it with [playwright](../playwright/SKILL.md) through roles and labels and verifying state after every action.
1. **Test non-functional risk**: measure latency, load, resource use, resilience, security boundaries, and observability only where the matrix or spec requires; set the baseline and threshold first with [benchmark](../benchmark/SKILL.md).
1. **Run regression proof**: execute the relevant package or subsystem suite; run the full gate (`mise run all`) only for release qualification, repository requirements, or cross-cutting risk, applying the [dirty-tree rule](../mise/SKILL.md#gotchas) when unrelated changes are present.
1. **Retest fixes narrowly**: reproduce the original failure, verify the fix, then rerun the impacted journeys and the checks the fix invalidated; avoid open-ended visual polishing loops.
1. **Report the matrix**: per case, record the risk and requirement, layer and environment, preconditions, steps or command, expected result, actual evidence, status (pass, fail, blocked, or not run), and cleanup with residual risk. Lead with blockers, then failures, passes, and untested boundaries with the authority or capability needed to test them; distinguish test coverage from operational readiness and hosted behavior, and report the highest proven rung of the [proof ladder](../production-readiness/SKILL.md).

## Gotchas

- **Authorization**: Real staging, paid APIs, destructive fixtures, production probes, account changes, and customer data require explicit authorization; afterwards tear down only resources created for the test and covered by its cleanup authority.
- **Browser sessions**: A test request does not authorize reusing a logged-in browser, entering passwords or MFA, bypassing CAPTCHA, or making purchases; tool rules live in [playwright](../playwright/SKILL.md).
- **Do not weaken assertions**: never skip a failing test, silently retry, or call an unavailable boundary green.
- **Evidence classes**: Keep automated, manual, runtime, accessibility, performance, and public/deployed evidence separate; a passing local matrix is not deployed or public proof.

## Documentation

- Companion skills: [playwright](../playwright/SKILL.md) (browser automation), [benchmark](../benchmark/SKILL.md) (latency and load baselines), [python-testing](../python-testing/SKILL.md) (implementing behavior), [product-design-review](../product-design-review/SKILL.md) (UX judgment), [code-security](../code-security/references/code-review/GUIDE.md) (repository scanning), [production-readiness](../production-readiness/SKILL.md) (launch gate).
- Adapted from [gstack QA](https://github.com/garrytan/gstack/blob/960c3a8d6c4d14cb4c5e551a8847f8ec7c4267df/qa/SKILL.md), [Anthropic webapp-testing](https://github.com/anthropics/skills/blob/f17010c9bb483898c1d9c9f42dde2b3a98889434/skills/webapp-testing/SKILL.md), [agent-skills browser testing](https://github.com/addyosmani/agent-skills/blob/d2478bf0c73a6357df39a3ed6aff16acaa218843/skills/browser-testing-with-devtools/SKILL.md).
