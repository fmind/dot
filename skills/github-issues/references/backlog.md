# Backlog Workflow

Turn verified findings into a deduplicated, prioritized, dependency-ordered set of issue drafts. Planning is read-only; creating issues, labels, or relationships requires authority for the confirmed repository.

## Workflow

1. **Retain review proof**: start from reproduced findings and keep partial scans or unavailable services as evidence gaps; use [repository-review](../../repository-review/SKILL.md) when the audit is not complete.
1. **Map existing relationships**: add native `blockedBy` and `blocking` relationships to the open and closed issues read for duplicate analysis; compare the underlying problem and evidence, not titles alone.
1. **Classify**: mark each candidate a `verified-finding` or `trend-opportunity`; retain an opportunity only when current project evidence proves fit and value.
1. **Reject noise**: drop candidates that duplicate an issue, lack reproducible evidence, exceed likely value, restore rejected scope, or add unjustified complexity.
1. **Draft**: follow the [draft contract](#draft-contract), explain the distinction from close matches, and model dependencies as draft-to-draft or draft-to-issue edges.
1. **Stop at the gate**: present deduplication decisions, ordered drafts, and the dependency graph; proceed only when the user has authorized creation in the confirmed repository.
1. **Create and reconcile**: refresh issues and labels immediately before writing, create every node before any [dependency edge](#dependency-edges), retain successful partial state, and retry only missing operations.
1. **Verify and report**: read back every body, label set, and edge; report review evidence, deduplication, ordered drafts, authorization, verified receipts, and remaining partial state.

Research only when a current primary source materially confirms a retained finding. Never copy private paths, credentials, customer data, private issue text, or non-public runtime details into a public repository.

## Draft contract

Give every draft a stable local ID and this complete Markdown body:

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

Add routing metadata outside the body: existing area, priority, and effort labels; directional `blocked-by` and `blocking` edges; the deduplication decision; and the evidence class. Prioritize impact and urgency rather than implementation order, and keep the graph acyclic.

## Dependency edges

Use gh's native dependency flags (gh 2.94+). Before each mutation or retry, read current edges with `gh issue view <number> -R <owner/repo> --json blockedBy,blocking` (each field is a `{nodes, totalCount}` object, not a flat list) and skip existing ones. Add an edge from the blocked issue with `gh issue edit <blocked> -R <owner/repo> --add-blocked-by <prerequisite>`; `gh issue create` also accepts `--blocked-by` and `--blocking` for issues that already exist. Afterwards verify both directions: the blocked issue's `blockedBy` and the prerequisite's `blocking`.
