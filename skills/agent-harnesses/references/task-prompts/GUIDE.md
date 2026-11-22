---
name: task-prompts
description: "Write task, delegation, and handoff prompts; resume, compact, or fork agy sessions."
---

# Task and Continuation Prompts

Write self-contained prompts for an agent without this conversation. [agent-frameworks](../../../agent-frameworks/SKILL.md) owns embedded application prompts; prefer native resume or compaction via [continuation](references/continuation.md) when session state carries over.

## Workflow

1. **Choose the mode**: fresh task or continuation; lock down outcome, latest corrections, scope, and acceptance criteria.
1. **Capture state**: check `git status --short --branch`, completed proof, exact stopping point, remaining work, failed approaches, and key decision rationales. Before `/clear`, follow [continuation](references/continuation.md) to save and copy the handoff.
1. **Draft non-empty sections**: objective, authority, constraints and rejected approaches, verified facts, current state, next step, verification, and return (plus ordered slices only when needed).
1. **Save and verify**: write `.agents/prompts/<YYYY-MM-DD>-<slug>.md` under `git rev-parse --show-toplevel` (or `~/.agents/prompts/` outside Git), confirm zero hidden-context assumptions, and report the path.

## Task guides

- [continuation](references/continuation.md): Resume, compact, or fork agy sessions, or copy a handoff before /clear.

## Gotchas

- **Authority travels with the task**: separate approved actions from proposals; writing a prompt grants no new permission.
- **Cite, never paste**: keep failures and proof gaps; reference `path:line` instead of copying code or `AGENTS.md`.
- **Keep `.agents/prompts/` untracked**: verify `git check-ignore -q .agents/prompts/x.md` (covered by global Git ignore; on external hosts where it exits `1`, append `.agents/prompts/` to `.git/info/exclude`, never tracked `.gitignore`), and commit prompts only on request.

## Documentation

- [Antigravity conversations](https://antigravity.google/docs/cli/conversations/) · [AGENTS.md](https://agents.md)
- Companions: [clipboard](../../../clipboard/SKILL.md), [git-worktree](../../../git-delivery/references/git-worktree/GUIDE.md).
