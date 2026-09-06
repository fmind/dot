---
name: repository-history
description: Reconstruct why tracked code exists from read-only Git history. Use when tracing a file, symbol, line, rename, revert, co-change, or linked pull request.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/repository-history
  created: "2026-08-08"
  updated: "2026-09-06"
---

# Repository History

Explain why tracked code exists from Git lineage and recorded rationale. Keep present-day debugging in [systematic-debugging](../systematic-debugging/SKILL.md) and external API choices in [technical-research](../technical-research/SKILL.md).

## Workflow

1. **Bound the question**: path, symbol, revision range, and the decision the history should inform; record HEAD, shallow state, and dirty work.
1. **Trace evidence**: use [investigation.md](references/investigation.md) for blame, line history, pickaxe, renames, commit inspection, and exact PR mapping through gh.
1. **Explain the timeline**: connect behavior changes, tests, reversions, and later superseding decisions; treat formatting and co-change as clues rather than causes.
1. **Report**: separate author-stated rationale, verified facts, inference, contradictions, and unknowns; cite commits/paths and name the smallest current check that resolves remaining risk.

## Gotchas

- **Investigation is read-only**: Preserve the working tree and existing refs. Fetch missing objects into an isolated clone when needed for the requested investigation; use a disposable worktree for bisect experiments. Pulling into the working tree, rewriting history, and contacting authors require authority for those effects.
- **Never print raw remote URLs**: identify the remote with `gh repo view --json nameWithOwner` and never echo a URL that carries a token.
- **Current blame is not original authorship**: a committer is not necessarily the designer, and a message can state intent without proving the constraint still holds; redact email addresses from returned evidence.
- **Confidence**: `High` needs explicit rationale that agrees with the patch, tests, and later history; `Medium` has agreeing lineage and co-change without stated rationale; `Low` rests on blame, one title match, a semantic search, sparse history, or an ancestry break; otherwise say `UNKNOWN`.
- **Stale rationale**: A revert describes a past decision; downgrade it when later architectural changes contradict the trade-off.
- **Shallow or incomplete clones**: Never infer that a missing commit or discussion does not exist; state the gap and lower confidence.

## Documentation

- [git blame](https://git-scm.com/docs/git-blame) · [git log](https://git-scm.com/docs/git-log) · [Pull requests associated with a commit](https://docs.github.com/en/rest/commits/commits#list-pull-requests-associated-with-a-commit)
- Adapted from [awesome-llm-apps commit-archaeologist](https://github.com/Shubhamsaboo/awesome-llm-apps/blob/779e9f9bcf87fa8cd95870a438b70b84e47d3173/agent_skills/commit-archaeologist/SKILL.md).
- Companion skills: [systematic-debugging](../systematic-debugging/SKILL.md) (reproduce a current failure), [diff-review](../diff-review/SKILL.md) (one change), [repository-review](../repository-review/SKILL.md) (cross-cutting audit), [technical-research](../technical-research/SKILL.md) (current external facts), [github-issues](../github-issues/SKILL.md) (remote issue state).
