---
name: agent-proposal
description: Research candidate changes and write an editable proposal with benefits, costs, and trade-offs. Use before scope is accepted; implementation-plan orders approved work.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/agent-proposal
  created: "2026-09-05"
  updated: "2026-09-05"
---

# Agent Proposal

Research a feature, refactoring, or architectural change and draft an easily editable proposal file in `.agents/proposals/<file>.md`. Writing structured proposals lets humans review, annotate, or prune items before kicking off an implementation session or generating an amplified execution prompt.

## Workflow

1. **Parse the request**: extract the target filename under `.agents/proposals/<file>.md` and the proposed topic or exploration goal from the arguments (for example, `/agent-proposal FEATURES.md Suggest 10 new features for the project`).
1. **Investigate the codebase**: explore existing capabilities, configurations, and architecture to ensure proposals are realistic, technically grounded, and aligned with repository philosophy.
1. **Formulate the proposal**: organize each proposed item with three clear attributes:
   - **What to do**: concrete, specific action or feature description.
   - **Benefit**: tangible value, developer ergonomics, performance, or capability unlocked.
   - **Cost & trade-offs**: complexity, maintenance overhead, breaking changes, or migration effort.
1. **Format for human editing**: format the document with scannable tables or bulleted blocks with checkboxes (`- [ ]`) so the human can easily delete, edit, or check off items during review.
1. **Write the proposal file**: write to `.agents/proposals/<file>.md` under `git rev-parse --show-toplevel`; create the directory if it does not exist.
1. **Report**: give the file path and strongest recommendation; once scope is accepted, implement when asked, or use [implementation-plan](../implementation-plan/SKILL.md) when sequencing is needed.

## Gotchas

- **Proposal scope**: preparing options does not authorize implementation; an explicit instruction to implement accepted items does, without another proposal cycle.
- **Scannable over dense**: avoid long narrative paragraphs; use tight, bulleted lists or comparison tables that can be reviewed in under two minutes.
- **Gitignore proposals**: keep `.agents/proposals/` gitignored so draft proposals do not pollute git status.

## Documentation

- Companion skills: [agent-prompt](../agent-prompt/SKILL.md) (turning approved proposals into amplified prompts), [product-loop](../product-loop/SKILL.md) (product discovery and problem framing), [plan-review](../plan-review/SKILL.md) (red-teaming architecture plans).
