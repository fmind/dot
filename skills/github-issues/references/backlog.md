# Backlog Workflow

Turn verified findings into a deduplicated, prioritized, dependency-ordered set of issue drafts. Planning is read-only; creating issues, labels, or relationships requires authority for the confirmed repository.

1. **Confirm the target**: read the repository and its instructions, then resolve identity and visibility with `gh repo view --json nameWithOwner,visibility`; do not treat discovery as mutation authorization.
1. **Retain review proof**: start from reproduced findings and keep partial scans or unavailable services as evidence gaps; use [repository-review](../../repository-review/SKILL.md) when the audit is not complete.
1. **Read existing issues**: fetch the open and closed issues needed for duplicate analysis with bodies, comments, labels, state, and native `blockedBy` and `blocking` relationships; compare the underlying problem and evidence, not titles alone.
1. **Classify**: mark each candidate a `verified-finding` or `trend-opportunity`; retain an opportunity only when current project evidence proves fit and value.
1. **Reject noise**: drop candidates that duplicate an issue, lack reproducible evidence, exceed likely value, restore rejected scope, or add unjustified complexity.
1. **Draft**: follow the [draft contract](draft-contract.md), explain the distinction from close matches, and model dependencies as draft-to-draft or draft-to-issue edges.
1. **Stop at the gate**: present deduplication decisions, ordered drafts, and the dependency graph; proceed only when the user has authorized creation in the confirmed repository.
1. **Create and reconcile**: refresh issues and labels immediately before writing, create every node before any dependency edge, retain successful partial state, and retry only missing operations.
1. **Verify**: read back every body, label set, and `blockedBy` and `blocking` relationship; report review evidence, deduplication, ordered drafts, authorization, verified receipts, and remaining partial state.

Research only when a current primary source materially confirms a retained finding. Never copy private paths, credentials, customer data, private issue text, or non-public runtime details into a public repository.
