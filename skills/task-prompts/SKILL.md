---
name: task-prompts
description: "Write grounded task, delegation, and continuation prompts for coding agents."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/task-prompts
  created: "2026-09-05"
  updated: "2026-10-07"
---

# Task and Continuation Prompts

Prepare instructions the receiving agent can use without this conversation. [system-prompts](../system-prompts/SKILL.md) owns prompts embedded in applications; native resume or compaction is preferable when it already preserves the needed state.

## Workflow

1. **Choose the mode**: fresh task, or continuation of work already underway; resolve the requested outcome, latest corrections, scope, and acceptance criteria.
1. **Record continuation state**: check `git status --short --branch`, record completed proof, the exact stopping point, outstanding work, failed approaches, and reasons for material decisions. Before `/clear` or a harness switch, use [handoff](../handoff/SKILL.md), which also copies the result to the clipboard.
1. **Draft** from [prompt-template.md](references/prompt-template.md); omit empty sections and add ordered slices only when execution needs them.
1. **Write and check**: resolve the root with `git rev-parse --show-toplevel`; save `.agents/prompts/<file>.md`, defaulting to `<YYYY-MM-DD>-<slug>.md`, or `~/.agents/prompts/` outside a repository. Verify the receiver can act without hidden context, then report the path.

## Gotchas

- **Authority travels with the task**: distinguish authorized actions from proposed work; writing the prompt does not grant additional permission.
- **Keep history useful, not copied**: preserve failures and proof gaps; cite code paths and lines instead of copying source or the shared persona.
- **Keep the prompt inbox untracked**: keep `.agents/prompts/` gitignored unless the user wants it tracked; keep a small continuation short.

## Documentation

- Companion skills: [research-brief](../implementation-plan/references/research-brief.md) (decision evidence), [implementation-plan](../implementation-plan/SKILL.md) (ordered slices), [agent-project](../agent-project/SKILL.md) (host layout), [handoff](../handoff/SKILL.md) (save and copy before `/clear`).
