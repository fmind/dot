---
name: project-backlog
description: Turn audit findings into deduplicated, prioritized issue drafts with dependencies and explicit authorization before any GitHub mutation. Use when review findings must become tracked issues.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/project-backlog
  created: "2026-08-01"
  updated: "2026-09-05"
---

# Project Backlog

Turn verified findings into deduplicated issue drafts and ordered dependencies. [github-issues](../github-issues/SKILL.md) owns authorized GitHub writes.

## Workflow

1. **Resolve the target**: inspect the git candidate and use `gh repo view` for repository identity/visibility; retain any review proof gaps.
1. **Deduplicate**: read relevant open/closed issues and native dependency edges; compare the underlying problem and evidence, not titles alone.
1. **Select useful work**: retain reproducible, distinct findings; reject speculative trends, unjustified complexity, and previously rejected scope.
1. **Draft**: follow [draft-contract.md](references/draft-contract.md), include evidence and acceptance, and order dependencies before presenting the reviewable set.
1. **Publish within existing authority**: refresh issues/labels first, create nodes, then add only missing native edges; preserve and report partial state.
1. **Verify**: read back bodies, labels, and relationships; report deduplication, ordered work, receipts, and remaining actions.

## Gotchas

- **Unauthorized writes** and **partial issue creation** are failed mutation boundaries: authorization to review, draft, implement, or open a pull request never authorizes issue creation, and a partial run is reported, not improvised around.
- **Partial creation**: Keep successful issues, create no edges, and list created, failed, and unattempted drafts; on a partial edge run keep successful edges, list the rest, and let a retry re-read and apply only missing edges.
- **Labels**: Prefer the repository's existing `area/*`, `priority/*`, and `effort/*` labels; when they are missing, propose the label set in the draft and let the user decide instead of stopping.
- **Public repositories**: Never copy private paths, credentials, customer data, private issue text, or non-public runtime details into drafts; sanitize the evidence or mark the draft `needs-human`.
- **Unavailable services**: When GitHub, research sources, or credentials are unavailable, keep local drafts, name the missing verification, and perform no write.
- **Dirty worktree**: It is review evidence, not permission to stash, clean, stage, format, or commit.

## References

- [Detailed procedure](references/procedure.md): read for complex or high-risk work requiring the full checklist.

## Documentation

- [GitHub GraphQL mutations](https://docs.github.com/en/graphql/reference/mutations#addblockedby) · [Draft contract](references/draft-contract.md)
- Companion skills: [repository-review](../repository-review/SKILL.md) (the findings), [github-issues](../github-issues/SKILL.md) (issue creation and edits), [production-readiness](../production-readiness/SKILL.md) (proof ladder).
