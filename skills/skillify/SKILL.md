---
name: skillify
description: "Route session lessons to checks, skills, AGENTS.md, or decision logs; author skills and guides."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/skillify
  created: "2026-09-02"
  updated: "2026-11-14"
---

# Skillify

Capture workflows as reusable skills or guides, extract `AGENTS.md` procedures, and route `(Lesson Learned)` session corrections to one canonical owner via [lesson-learned](references/lesson-learned.md). This skill owns workflow extraction, catalog conventions, and [package rules](references/package-rules.md).

## Workflow

1. **Decide the owner first**: for session corrections, decisions, or `(Lesson Learned)` proposals, run [lesson-learned](references/lesson-learned.md) before touching a skill—prefer deterministic checks, tests, or code defaults over prose.
1. **Extract from the session**: goal, trigger phrases, verified commands with flags, user corrections, decisions with reasons, dead ends, and required tools; strip session paths, one-off values, and secrets.
1. **Apply the admission rule** in [package rules](references/package-rules.md#categories-and-scope) before picking an owner or scope.
1. **Check neighbors**: run `rg -m1 '^description:' ~/.agents/skills/*/SKILL.md .agents/skills/*/SKILL.md` (`gh skill list` scans host directories without descriptions) and inspect overlapping skills; extend an existing owner for the same workflow, create a new skill only for a distinct trigger, and link neighbors instead of copying.
1. **Choose scope**:
   - **Global** (reusable, tool-generic): `skills/<name>/` in `fmind/dot` (`~/.agents/skills/<name>/`), registered and checked via `dot-skills` (`mise run check:skills` + affected install tests).
   - **Local** (repo-specific commands or conventions): `.agents/skills/<name>/` (read natively by agy; add `.claude/skills -> ../.agents/skills` only when Claude Code is used per [agent-project](../agent-project/SKILL.md); also registered via `dot-skills` inside `fmind/dot`).
1. **Author from [skill.md](templates/skill.md)**: apply [package rules](references/package-rules.md) with a strict model-delta filter—cut language basics, tutorials, and tool fluff a model already knows; keep only verified flags, security gates, Fmind defaults, and links to heavy configs in `references/`.
1. **Validate**: frontmatter `name` matches directory, links resolve, resources are reachable, and `mise run check:skills` passes (or `gh skill publish --dry-run .agents/skills` in external repos).
1. **Exercise behavior**: run [evaluation](references/evaluation.md) on substantial additions, trims, or routing edits (direct trigger, neighbor disambiguation, negative control, and binary checks in an isolated fixture); report unavailable host checks separately.
1. **Report**: path, description, and scope.

## Extracting from AGENTS.md

Keep personal defaults in global `AGENTS.md` and repo invariants in project `AGENTS.md`. Move procedures into their owning skill (new skill only for a distinct workflow), leave a routing cue, and sync via [repository-docs](../repository-docs/SKILL.md).

## Gotchas

- **Descriptions route, bodies instruct**: state triggers in `description`, never a workflow summary.
- **Keep dates current**: set `created` and `updated` on creation; bump `updated` on every edit.
- **Vendor external skills cleanly**: follow [vendor-skills](../agent-project/references/vendor-skills.md) instead of retyping upstream skills.
- **Promote cleanly**: follow [promotion and portability](references/package-rules.md#promotion-and-portability) when extracting a standalone skill and delete the old copy.

## Task guides

<!-- guides:start -->

- [lesson-learned](references/lesson-learned.md): Turn session corrections and decisions into minimal edits to checks, skills, AGENTS.md, or decision logs.

<!-- guides:end -->

## Documentation

- [Agent Skills specification](https://agentskills.io/specification) · [Evaluation and load metrics](references/evaluation.md) · Companions: [trim](../trim/SKILL.md), [humanize](../humanize/SKILL.md).
