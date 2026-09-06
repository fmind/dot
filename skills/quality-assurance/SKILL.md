---
name: quality-assurance
description: Design and execute risk-based test campaigns across critical user journeys and report proof gaps. Use for cross-layer validation beyond one diff.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/quality-assurance
  created: "2026-08-08"
  updated: "2026-09-06"
---

# Quality Assurance

Run a risk-based test campaign over the actual feature journey. Keep one-diff review in [diff-review](../diff-review/SKILL.md); project- or provider-specific stochastic model evaluation remains a separate workflow.

## Workflow

1. **Define working**: exact candidate, users, critical journeys, supported environments, acceptance criteria, and risk-ranked failure modes.
1. **Choose coverage**: map risks to the smallest meaningful unit, integration, browser, accessibility, performance, resilience, or manual checks; reuse existing evidence only when identity and scope match.
1. **Prepare the environment**: use deterministic fixtures and local fakes by default; declare real-service access, cost, and cleanup before crossing those boundaries.
1. **Exercise the journey**: run the repository's `mise` test tasks, then cover unhappy paths, permissions, recovery, cancellation, and relevant platform variants; preserve failures and useful artifacts.
1. **Report**: reproducible defects, passed/failed/unrun checks, and residual gaps; distinguish test coverage from operational readiness and hosted behavior.

## Gotchas

- **Authorization**: Real staging, paid APIs, destructive fixtures, production probes, account changes, and customer data require explicit authorization; afterwards tear every paid or externally exposed resource down.
- **Browser sessions**: A test request does not authorize reusing a logged-in browser, entering passwords or MFA, bypassing CAPTCHA, or making purchases; tool rules live in [playwright](../playwright/SKILL.md).
- **Do not weaken assertions**: never skip a failing test, silently retry, or call an unavailable boundary green.
- **Evidence classes**: Keep automated, manual, runtime, accessibility, performance, and public/deployed evidence separate; a passing local matrix is not deployed or public proof.

## References

- [Detailed procedure](references/procedure.md): read for complex or high-risk work requiring the full checklist.

## Documentation

- Companion skills: [playwright](../playwright/SKILL.md) (browser automation), [benchmark](../benchmark/SKILL.md) (latency and load baselines), [test-driven-development](../test-driven-development/SKILL.md) (implementing behavior), [product-design-review](../product-design-review/SKILL.md) (UX judgment), [secure](../secure/SKILL.md) (repository scanning), [production-readiness](../production-readiness/SKILL.md) (launch gate).
