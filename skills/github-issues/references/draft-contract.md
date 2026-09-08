# Backlog Draft Contract

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

Add routing metadata outside the body: existing area, priority, and effort labels; directional `blocked-by` and `blocking` edges; the deduplication decision; and the evidence class. Prioritize impact and urgency rather than implementation order, keep the graph acyclic, and create all issue nodes before edges.

Resolve node IDs with `gh issue view <number> --repo <owner/repo> --json id`. Before each mutation or retry, read current relationships, skip existing edges, and verify both directions afterwards. For a blocked issue, pass that issue as `issueId` and its prerequisite as `blockingIssueId` to GitHub's `addBlockedBy` GraphQL mutation.
