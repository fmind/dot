---
name: agent-prompt
description: "Prepare a grounded task or continuation prompt. Use when delegating fresh work or carrying progress, decisions, failures, and proof into a new agent session."
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/agent-prompt
  created: "2026-09-05"
  updated: "2026-09-05"
---

# Agent Prompt

Prepare instructions the receiving agent can use without this conversation. [prompt-design](../prompt-design/SKILL.md) owns prompts embedded in applications; native resume or compaction is preferable when it already preserves the needed state.

## Workflow

1. **Choose the mode**: fresh task, or continuation of work already underway; resolve the requested outcome, latest corrections, scope, and acceptance criteria.
1. **Ground the prompt**: inspect relevant repository instructions, source, tests, and installed dependencies; verify paths and commands and label assumptions.
1. **For a continuation**: check `git status --short --branch`, record completed proof, the exact stopping point, outstanding work, failed approaches, and reasons for material decisions.
1. **Draft** from [prompt-template.md](references/prompt-template.md); omit empty sections and add ordered slices only when execution needs them.
1. **Write and check**: resolve the root with `git rev-parse --show-toplevel`; save `.agents/prompts/<file>.md`, defaulting to `<YYYY-MM-DD>-<slug>.md`, or `~/.agents/prompts/` outside a repository. Verify the receiver can act without hidden context, then report the path.

## Gotchas

- **Authority travels with the task**: distinguish authorized actions from proposed work; writing the prompt does not grant additional permission.
- **Useful history**: preserve failures and proof gaps; cite code paths and lines instead of copying source or the shared persona.
- **Working inbox**: keep `.agents/prompts/` gitignored unless the user wants it tracked; keep a small continuation short.

## Documentation

- Companion skills: [agent-proposal](../agent-proposal/SKILL.md) (options), [implementation-plan](../implementation-plan/SKILL.md) (ordered slices), [plan-execution](../plan-execution/SKILL.md) (receiving work), [agent-project](../agent-project/SKILL.md) (host layout).
