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

Use gh's native dependency flags (gh 2.94+). Before each mutation or retry, read current edges with `gh issue view <number> -R <owner/repo> --json blockedBy,blocking` and skip existing ones. Add an edge from the blocked issue with `gh issue edit <blocked> -R <owner/repo> --add-blocked-by <prerequisite>`; `gh issue create` also accepts `--blocked-by` and `--blocking` for issues that already exist. Afterwards verify both directions: the blocked issue's `blockedBy` and the prerequisite's `blocking`.
