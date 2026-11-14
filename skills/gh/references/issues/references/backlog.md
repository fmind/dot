# Backlog Workflow

Turn verified findings into deduplicated, prioritized, acyclic issue drafts (read-only until creation is authorized; never leak private paths, credentials, customer data, or internal details into public repos).

## Workflow

1. **Start from verified proof**: keep partial scans or unreachable services as evidence gaps; run [full-review](../../../../full-review/SKILL.md) first if incomplete.
1. **Map existing issues and edges**: read open/closed candidates plus `blockedBy` and `blocking` by root cause, not title.
1. **Filter**: tag `verified-finding` or `trend-opportunity` (proven fit only); drop duplicates, unverified claims, churn, and previously rejected scope.
1. **Draft & gate**: format per [draft contract](#draft-contract) with area/priority/effort labels, `blocked-by`/`blocking` edges, and evidence class; rank by impact and urgency, then stop for approval.
1. **Create, link & verify**: refresh issues/labels before writing, create nodes before [dependency edges](#dependency-edges), retry only missing steps, and read back every body, label set, and edge.

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
