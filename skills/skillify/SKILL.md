---
name: skillify
description: Turn this conversation, a repeated workflow, or an oversized AGENTS.md section into a global or local SKILL.md. Use when asked to skillify or capture a workflow.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/skillify
  created: "2026-09-02"
  updated: "2026-09-11"
---

# Skillify

Capture what this session learned as a skill the next session can run without the conversation. Use the host's native authoring tools for package mechanics; this skill owns workflow extraction, personal conventions, and the [catalog package rules](references/package-rules.md).

## Workflow

1. **Extract from the session**: the goal, the user's trigger phrases, the exact commands that worked (with flags), the decisions and why, the dead ends, and the tools required; drop session-specific paths, one-off values, and secrets.
1. **Apply the admission rule** in [package rules](references/package-rules.md): identify the personal choice, reusable procedure or artifact, demonstrated failure, or upstream route that changes agent behavior. If only general product knowledge remains, use documentation instead of creating a skill.
1. **Check the catalog**: `skills list` and `skills list -g`, then read any neighbor with an overlapping description; extend it when the workflow is the same, write a new skill only for a distinct trigger, and link neighbors instead of copying them.
1. **Choose the scope**:
   - **Global** (reusable, tool-generic): `~/.agents/skills/<name>/`, the `skills/` directory of the dot repository; add its CLI names to `skills/contracts.json`, then run `mise run check:skills` and `mise run test` there.
   - **Local** (repository-specific commands, data, or conventions): `.agents/skills/<name>/` in the project; add `.claude/skills -> ../.agents/skills` if missing per [agent-project](../agent-project/SKILL.md).
1. **Write from the template**: copy [skill.md](templates/skill.md) and apply the authoring limits in [package rules](references/package-rules.md); long configs and examples go to `references/`.
1. **Validate**: frontmatter `name` equals the directory, every link resolves, every resource is directly disclosed, every required tool is documented, and `mise run check:skills` passes for a global skill.
1. **Test behavior**: follow the [adoption check](references/adoption-check.md) for substantial additions or routing changes: a natural trigger, a neighboring task, and an observable outcome in an isolated fixture. Keep paid or external effects within scope and report unavailable host validation separately.
1. **Report**: the path, the description, the scope, and whether the routing probes in `dot/testdata/skills/` need a new prompt for the skill.

## Extracting from AGENTS.md

Keep durable preferences in the global persona and repository invariants in project `AGENTS.md`. Move procedures into the existing owning skill where possible; create a global or local skill only for a distinct reusable workflow. Leave a routing cue and re-run [repository-docs](../repository-docs/SKILL.md).

## Gotchas

- **Descriptions route, bodies instruct**: the description decides when the skill loads; the body decides what happens. Do not summarize the workflow in the description.
- **Dates**: set `created` and `updated` to today; bump `updated` on every later edit.
- **Third-party content**: when the workflow came from an external skill, follow the shared [vendor-skill policy](../agent-project/references/vendor-skills.md) instead of retyping it.

## Documentation

- [Agent Skills specification](https://agentskills.io/specification)
- Native tooling: [Agent Skills](https://agentskills.io/specification) and the [vendor-skill policy](../agent-project/references/vendor-skills.md).
- Companion skills: [agent-project](../agent-project/SKILL.md) (local skill layout), [repository-docs](../repository-docs/SKILL.md) (trim `AGENTS.md` after extraction).
