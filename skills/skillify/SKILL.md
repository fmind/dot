---
name: skillify
description: "Capture workflows as skills or guides, or extract AGENTS.md procedures."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/skillify
  created: "2026-09-02"
  updated: "2026-11-10"
---

# Skillify

Capture session lessons as reusable skills or guides. This skill owns workflow extraction, catalog conventions, and [package rules](references/package-rules.md); [lesson-learned](../lesson-learned/SKILL.md) decides whether a lesson belongs in a skill at all.

## Workflow

1. **Extract from the session**: goal, trigger phrases, verified commands with flags, user corrections, decisions with reasons, dead ends, and required tools; strip session paths, one-off values, and secrets.
1. **Apply the admission rule** in [package rules](references/package-rules.md#categories-and-scope) before picking an owner or scope.
1. **Check neighbors**: run `rg -m1 '^description:' ~/.agents/skills/*/SKILL.md .agents/skills/*/SKILL.md` (`gh skill list` scans host directories without descriptions) and inspect overlapping skills; extend an existing owner for the same workflow, create a new skill only for a distinct trigger, and link neighbors instead of copying.
1. **Choose scope**:
   - **Global** (reusable, tool-generic): `skills/<name>/` in `fmind/dot` (`~/.agents/skills/<name>/`), registered and checked via `dot-skills` (`mise run check:skills` + affected install tests).
   - **Local** (repo-specific commands or conventions): `.agents/skills/<name>/` (read natively by agy; add `.claude/skills -> ../.agents/skills` only when Claude Code is used per [agent-project](../agent-project/SKILL.md); also registered via `dot-skills` inside `fmind/dot`).
1. **Author from [skill.md](templates/skill.md)**: apply [package rules](references/package-rules.md); move long configs and examples to `references/`.
1. **Validate**: frontmatter `name` matches directory, links resolve, resources are reachable, and `mise run check:skills` passes (or `gh skill publish --dry-run .agents/skills` in external repos).
1. **Exercise behavior**: run the [adoption check](references/adoption-check.md) on substantial additions or routing edits (natural trigger, neighboring task, observable outcome in an isolated fixture); report unavailable host checks separately.
1. **Report**: path, description, and scope.

## Extracting from AGENTS.md

Keep personal defaults in global `AGENTS.md` and repo invariants in project `AGENTS.md`. Move procedures into their owning skill (new skill only for a distinct workflow), leave a routing cue, and sync via [repository-docs](../repository-docs/SKILL.md).

## Gotchas

- **Descriptions route, bodies instruct**: state triggers in `description`, never a workflow summary.
- **Keep dates current**: set `created` and `updated` on creation; bump `updated` on every edit.
- **Vendor external skills cleanly**: follow [vendor-skills](../agent-project/references/vendor-skills.md) instead of retyping upstream skills.
- **Follow [portability](references/portability.md)** when promoting a guide or publishing standalone.

## Documentation

- [Agent Skills specification](https://agentskills.io/specification) · [Catalog and usage review](references/catalog-review.md)
