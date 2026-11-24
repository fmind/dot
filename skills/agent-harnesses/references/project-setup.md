---
name: project-setup
description: "Set up repo AGENTS.md, shared skills, discovery, host overrides, and vendor skills."
---

# Set Up Agents on a Project

Author shared project instructions and skills once, adding host overrides only where needed. [docs/repository](../../docs/references/repository/GUIDE.md) owns instruction prose; [mcp-setup](mcp-setup.md) owns MCP registration.

## Workflow

1. **Inspect first**: preserve existing `AGENTS.md`, host configs, skills, and user settings.
1. **Create the shared layer**: follow [host-setup.md](host-setup.md) using [AGENTS.md.template](../templates/AGENTS.md.template), `.agents/skills/`, and gitignored `.agents/prompts/` ([task-prompts](task-prompts/GUIDE.md)); add host overrides or custom-agent files only for hosts in use.
1. **Verify discovery**: run `dot context --check` and host listings in [host-discovery.md](host-discovery.md); listing proves discovery, not compliance.
1. **Vet vendor skills**: follow [vendor-skills.md](vendor-skills.md) (`skills find`, `skills add`, `skills experimental_install`, vs preview `gh skill`).
1. **Maintain**: sync changes through [docs/repository](../../docs/references/repository/GUIDE.md), including local skill references.

## Gotchas

- **One rule body**: never create project `CLAUDE.md` or `CLAUDE.local.md`—Claude Code loads either instead of `AGENTS.md`.
- **Vet repo configs before enabling**: review repository hooks, MCP servers, skills, plugins, and custom agents first.
- **Keep client skills & plugins project-local on multi-tenant machines**: keep org/client skills and plugins in repo `.agents/` rather than global `~/.gemini/config/{skills,plugins}.json` so they never bleed into unrelated sessions (`dot doctor` warns on external global paths).
- **Support mixed-audience teams via an Interaction Mode switch**: for shared team starter templates serving both non-technical teammates and engineers, include an explicit `Interaction Mode: Discovery | Expert` setting in `AGENTS.md` (guided explanations and confirmation prompts vs terse execution).

## Documentation

- [AGENTS.md standard](https://agents.md) · [Agent Skills specification](https://agentskills.io/specification) · [vercel-labs/skills](https://github.com/vercel-labs/skills) · [fmind/agent-supagents](https://github.com/fmind/agent-supagents)
- Companions: [cross-harness-agents](cross-harness-agents.md), [docs/repository](../../docs/references/repository/GUIDE.md), [skillify](../../skillify/SKILL.md), [subagent](../../subagent/SKILL.md).
