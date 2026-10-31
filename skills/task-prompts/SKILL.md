---
name: task-prompts
description: "Write task, delegation, and handoff prompts for agents; resume or compact agy sessions."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/task-prompts
  created: "2026-09-05"
  updated: "2026-10-31"
---

# Task and Continuation Prompts

Prepare instructions the receiving agent can use without this conversation. [system-prompts](../system-prompts/SKILL.md) owns prompts embedded in applications; native resume or compaction is preferable when it already preserves the needed state; the [continuation](references/continuation.md) guide chooses between them and a handoff.

## Workflow

1. **Choose the mode**: fresh task, or continuation of work already underway; resolve the requested outcome, latest corrections, scope, and acceptance criteria.
1. **Record continuation state**: check `git status --short --branch`, record completed proof, the exact stopping point, outstanding work, failed approaches, and reasons for material decisions. Before `/clear`, follow the [continuation](references/continuation.md) guide, which also copies the result to the clipboard.
1. **Draft** from [prompt-template.md](references/prompt-template.md); omit empty sections and add ordered slices only when execution needs them.
1. **Write and check**: resolve the root with `git rev-parse --show-toplevel`; save `.agents/prompts/<file>.md`, defaulting to `<YYYY-MM-DD>-<slug>.md`, or `~/.agents/prompts/` outside a repository. Verify the receiver can act without hidden context, then report the path.

## Task guides

<!-- guides:start -->

- [continuation](references/continuation.md): Resume, compact, or fork an agy session, or save and copy a handoff prompt before /clear.

<!-- guides:end -->

## Gotchas

- **Authority travels with the task**: distinguish authorized actions from proposed work; writing the prompt does not grant additional permission.
- **Keep history useful, not copied**: preserve failures and proof gaps; cite code paths and lines instead of copying source or the shared persona.
- **Keep the prompt inbox untracked**: the global Git ignore already excludes `.agents/prompts/` (confirm with `git check-ignore -v .agents/prompts/x.md`), so add no repository entry, and track prompts only when the user asks; keep a small continuation short.

## Documentation

- Companion skills: [research-brief](../implementation-plan/references/research-brief.md) (decision evidence), [implementation-plan](../implementation-plan/SKILL.md) (ordered slices), [agent-project](../agent-project/SKILL.md) (host layout), [clipboard](../clipboard/SKILL.md) (verified copy), [git-worktree](../git-delivery/references/git-worktree/GUIDE.md) (isolated continuation).
