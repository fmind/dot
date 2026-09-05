---
name: agent-prompt
description: Audit repository context and write an amplified task prompt in .agents/prompts/<file>.md to handover to another agent. Use when delegating an agent prompt.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/agent-prompt
  created: "2026-09-05"
  updated: "2026-09-05"
---

# Agent Prompt

Investigate the repository, clarify ambiguities, and write a self-contained execution prompt under `.agents/prompts/<file>.md` to handover a delegated task to another coding agent. Amplifying prompts upfront grounds the task in real file paths, commands, and constraints so an execution model can implement without stalling.

## Workflow

1. **Parse the request**: extract the target filename under `.agents/prompts/<file>.md` (defaulting to a descriptive slug if omitted) and the task description from the invocation arguments (for example, `/agent-prompt PLAN.md Improve code coverage`).
1. **Investigate the repository**: inspect relevant source files, tests, configurations, and dependencies with `rg`, `fd`, or file viewers; verify exact paths and symbol names instead of guessing.
1. **Assess clarity and clarify**: check whether the request leaves critical architectural decisions or scope underspecified; if ambiguous, ask the user to clarify before writing, or record explicit, grounded assumptions.
1. **Amplify the prompt**: structure a complete, self-contained instruction for the receiving agent covering:
   - **Objective**: concise statement of the outcome and acceptance criteria.
   - **Context & verified paths**: exact file paths, relevant line numbers, and existing implementation patterns.
   - **Constraints & standards**: non-negotiable project rules (minimalist, 80/20, typed, lint-before-done, no-sudo).
   - **Implementation steps**: ordered, dependency-aware instructions with concrete actions.
   - **Verification gate**: commands the receiving agent must execute warning-free (`mise run check`, `mise run test`).
1. **Write the prompt file**: write the amplified prompt to `.agents/prompts/<file>.md` under `git rev-parse --show-toplevel`; create the directory if it does not exist.
1. **Summarize to the user**: provide a brief summary of what the prompt instructs, the files it targets, and how to invoke the next agent session with it.

## Gotchas

- **Do not execute the task**: this skill prepares the amplified prompt for another agent; do not edit code or implement the changes in this session.
- **Self-contained instructions**: the receiving agent lacks this session's context; resolve all pronouns, cite actual file paths, and provide explicit verification commands.
- **Ignore working prompts**: ensure `.agents/prompts/` is gitignored so temporary prompt files are not tracked in git.

## Documentation

- Companion skills: [agent-proposal](../agent-proposal/SKILL.md) (human-in-the-loop proposals before prompt drafting), [handover](../handover/SKILL.md) (session-to-session state handover), [implementation-plan](../implementation-plan/SKILL.md) (multi-slice architecture plans), [prompt-design](../prompt-design/SKILL.md) (system prompt engineering).
