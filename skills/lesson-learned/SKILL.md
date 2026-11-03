---
name: lesson-learned
description: "Turn session corrections and approved decisions into minimal edits to checks, skills, AGENTS.md, or decision logs."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/lesson-learned
  created: "2026-11-03"
  updated: "2026-11-03"
---

# Lesson Learned

Turn what a session taught into the smallest durable change in the right owner, so projects align bit by bit without piling up rules. Run it on `/lesson-learned` or "lessons learned", and propose it as a `(Lesson Learned)` suggestion after an implementation, approved decisions, a correction, or a repeated instruction. [skillify](../skillify/SKILL.md) owns creating and extending skills, [trim](../trim/SKILL.md) owns shortening, and [AGENTS.md guidance](../repository-docs/references/agents.md) defines what each instruction layer holds.

## Workflow

1. **Collect candidates**: list the user's corrections, approved decisions with their reason, repeated instructions, workarounds, and rules that proved stale, wrong, or ignored, each with where it came from. Drop session-specific paths, one-off values, and secrets. Done when every correction and approved decision is listed or excluded with a reason.
1. **Admit few**: keep a lesson only when the situation will recur, an agent would likely get it wrong next time, and no existing rule already says it; search the owners first (`rg -i '<keyword>' AGENTS.md ~/.agents/AGENTS.md ~/.agents/skills/*/ .agents/skills/`). An ignored rule is a wording or placement problem, not a missing rule. Done when each candidate is admitted or rejected with one reason.
1. **Pick one owner, strongest first**:
   1. a test, check, lint rule, script, or code default that enforces it;
   1. the skill that owns the topic, through skillify when the change is more than a line or needs a new skill;
   1. the project `AGENTS.md` for a repository invariant;
   1. the global persona (`dot_agents/AGENTS.md` in fmind/dot) for a durable personal preference across projects;
   1. the project decision log, the brain through [bf](../bf/SKILL.md) when the project has one, for a dated choice and its reason, including "do not re-raise" outcomes.

   Done when each lesson has exactly one owner and no copy elsewhere.
1. **Improve before adding**: don't just append. First sharpen, merge, or align the existing content the lesson touches, and delete what it makes stale; add a new line only when nothing existing can carry it. Done when each edit reports the words added and removed per file and instruction budgets still pass (`dot agent context --project .`, plus `--source .` in fmind/dot).
1. **Propose, then apply**: list each lesson as a `(Lesson Learned)` suggestion naming the owner path and the exact old and new text, ranked by impact. Apply only what the user approves, since approving a decision does not approve rule wording; then run the owner's checks (focused tests, `mise run check:skills` for skills, the formatter for docs). Done when approved edits pass their checks or the failure is reported.

## Gotchas

- **Prefer enforcement over prose**: a check fails on every host and costs no context; a sentence is loaded every session and can still be ignored.
- **Report "no lesson" plainly**: most sessions change nothing durable; say so in one line instead of inventing a rule.
- **Keep host memory out of the loop**: harness memory (such as Claude Code's `memory/` directory) is read by one host only, so route durable lessons to shared owners and migrate memory entries that hold them; touch memory only on the user's request, and never delete a memory file that a decision log cites as evidence.
- **Keep lessons generic**: customer or employer specifics stay in their repositories; global owners get generic wording with synthetic fixtures.
- **Keep agy `/learn` lessons in the dot source**: its global scope writes `~/.gemini/GEMINI.md` (the chezmoi-deployed persona, which the next `chezmoi apply --force` overwrites), rule files under `~/.gemini/config/rules/`, or new skills under `~/.gemini/config/skills/` (`~/.agents/skills`), all outside the dot source. Approve its `learning_proposal.md` only for project scope; apply global lessons to the dot source with this workflow.

## Documentation

- Companion skills: [skillify](../skillify/SKILL.md) (skill authoring), [trim](../trim/SKILL.md) (shortening owners), [repository-docs](../repository-docs/SKILL.md) (instruction layers and Markdown style), [bf](../bf/SKILL.md) (brain decision logs).
