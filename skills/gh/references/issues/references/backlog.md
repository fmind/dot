# Backlog Workflow

Turn verified findings into a deduplicated, prioritized, acyclic set of issue drafts. Planning is read-only; creating issues, labels, or edges requires authority for the confirmed repository. Never copy private paths, credentials, customer data, or internal details into a public repository.

## Workflow

1. **Start from verified proof**: retain partial scans or unreachable services as evidence gaps; run [full-review](../../../../full-review/SKILL.md) first if incomplete. Consult primary external sources only when needed to confirm a finding.
1. **Map existing issues and edges**: read open/closed candidates plus `blockedBy` and `blocking`, comparing root causes and evidence rather than titles.
1. **Classify and filter**: label each candidate `verified-finding` or `trend-opportunity` (kept only with proven project fit); drop duplicates, unverified claims, low-value churn, and previously rejected scope.
1. **Draft**: apply the [draft contract](#draft-contract), note distinctions from close matches, attach existing area/priority/effort labels plus `blocked-by`/`blocking` edges and evidence class, and rank by impact and urgency.
1. **Gate**: present deduplication decisions, ordered drafts, and the dependency graph; stop until creation is authorized.
1. **Create and link**: refresh issues/labels before writing, create all nodes before [dependency edges](#dependency-edges), keep partial successes, and retry only missing steps.
1. **Verify**: read back every body, label set, and edge; report receipts and any remaining gaps.

## Draft contract

Give every draft a stable local ID and this Markdown body:

```markdown
## Problem

State the current verified gap and its impact.

## Proposal

Describe the smallest complete root-cause solution.

## Acceptance criteria

- [ ] Define directly verifiable outcomes.

## Evidence and references

- Cite repository paths, commands, exact-head CI, authorized runtime observations, or public primary sources.

## Boundaries

Name excluded mutations, proof levels, complexity, spend, and runtime scope.

## Validation

- List focused checks and the complete repository-owned gate.
```

## Dependency edges

Use native flags (`gh` 2.94+). Before each write or retry, read `gh issue view <number> -R <owner/repo> --json blockedBy,blocking` (`{nodes, totalCount}` objects, not flat lists) and skip existing edges. Link via `gh issue edit <blocked> -R <owner/repo> --add-blocked-by <prerequisite>` (or `gh issue create --blocked-by` / `--blocking` for existing issues), then verify both `blockedBy` and `blocking`.
