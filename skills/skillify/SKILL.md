---
name: skillify
description: "Route lessons to checks, skills, AGENTS.md, decision logs; author skills and trim docs/prompts/configs for tokens."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/skillify
  created: "2026-09-02"
  updated: "2026-11-23"
---

# Skillify

Capture reusable workflows as skills/guides, extract `AGENTS.md` procedures, and route durable session lessons to one canonical owner via [lesson-learned](references/lesson-learned.md).

## Workflow

1. **Route before writing**: for corrections/decisions, run [lesson-learned](references/lesson-learned.md) first (prefer deterministic checks/tests/defaults over prose). Apply the [admission rule](references/package-rules.md#categories-and-scope) and check neighbors via `rg -m1 '^description:' ~/.agents/skills/*/SKILL.md .agents/skills/*/SKILL.md`; extend an existing owner unless the trigger is distinct.
1. **Choose scope**: global reusable skills live in `fmind/dot` `skills/<name>/` (registered via `dot-skills`); repo-only skills live in `.agents/skills/<name>/` (see [project-setup](../agent-harnesses/references/project-setup.md)). Keep personal defaults in global `AGENTS.md` and repo invariants in project `AGENTS.md`; extract procedures to skills via [docs/repository](../docs/references/repository/GUIDE.md).
1. **Author from [skill.md](templates/skill.md)**: follow [package rules](references/package-rules.md) with a model-delta filter—descriptions state triggers, bodies keep only verified flags, security gates, and Fmind defaults; push heavy detail to `references/`, bump `updated`, and vendor external skills via [vendor-skills](../agent-harnesses/references/vendor-skills.md).
1. **Validate & probe**: run `mise run check:skills` (or `gh skill publish --dry-run .agents/skills` externally) and exercise behavior per [evaluation](references/evaluation.md); report path, description, and scope.

## Task guides

<!-- guides:start -->

- [lesson-learned](references/lesson-learned.md): Turn session corrections and decisions into minimal edits to checks, skills, AGENTS.md, or decision logs.
- [trim](references/trim.md): Trim docs, prompts, skills, or configs to cut tokens, keeping behavior.

<!-- guides:end -->

## Documentation

- [Agent Skills specification](https://agentskills.io/specification) · [gh skill](https://cli.github.com/manual/gh_skill) · [Evaluation and load metrics](references/evaluation.md) · Companions: [trim](references/trim.md), [humanize](../humanize/SKILL.md).
