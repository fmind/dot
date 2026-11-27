---
name: project-setup
description: "Set up repo AGENTS.md, shared skills, discovery, host overrides, and vendor skills."
---

# Set Up Agents on a Project

Author shared project instructions and skills once, adding host overrides only where needed. [docs/repository](../../docs/references/repository/GUIDE.md) owns instruction prose; [mcp-setup](mcp-setup.md) owns MCP registration.

## Workflow

1. **Inspect first**: preserve existing `AGENTS.md`, host configs, skills, and user settings.
1. **Create the shared layer**:
   ```bash
   mkdir -p .agents/skills .agents/prompts
   ```
   - Seed `AGENTS.md` from [AGENTS.md.template](../templates/AGENTS.md.template) when no stack template supplied one (`.template` avoids auto-loading).
   - Store repo skills in `.agents/skills/<name>/SKILL.md` and handoffs in gitignored `.agents/prompts/` ([task-prompts](task-prompts/GUIDE.md)); Antigravity, Copilot, Cursor, and other [AGENTS.md](https://agents.md) hosts read both natively.
1. **Keep unused host state ignored & add overrides only on demand**:
   - Keep `.claude/` and `.gemini/` in `.gitignore` without `.claude/skills` symlinks or `CLAUDE.md` files.
   - Add host-only files only when required: `.github/copilot-instructions.md` for Copilot additions, existing third-party host files on external repos, or native custom-agent roles when [cross-harness-agents](cross-harness-agents.md) justifies them (Antigravity honors `.gitignore`).
1. **Verify discovery**: launch each CLI at the repo root, run `dot context --check`, and confirm instructions, skills, and MCP via [host-discovery.md](host-discovery.md) (listing proves discovery, not compliance).
1. **Vet vendor skills & maintain**: vet third-party packages via [vendor-skills.md](vendor-skills.md) (`skills find`/`add`/`experimental_install` vs preview `gh skill`), and sync doc/skill updates through [docs/repository](../../docs/references/repository/GUIDE.md).

## Gotchas

- **One rule body**: never create project `CLAUDE.md` or `CLAUDE.local.md`—Claude Code loads either instead of `AGENTS.md`.
- **Vet repo configs before enabling**: review repository hooks, MCP servers, skills, plugins, and custom agents first.
- **Keep client skills & plugins project-local on multi-tenant machines**: keep org/client skills, plugins, agents, and rules in repo `.agents/` rather than global `~/.gemini/config/{skills,plugins,agents,rules}.json` so they never bleed into unrelated sessions (`dot doctor` warns on external global paths).
- **Support mixed-audience teams**: for shared starter templates serving both non-technical teammates and engineers, include an explicit `Interaction Mode: Discovery | Expert` setting in `AGENTS.md` (guided explanations and confirmation prompts vs terse execution).

## Documentation

- [AGENTS.md standard](https://agents.md) · [Agent Skills specification](https://agentskills.io/specification) · [vercel-labs/skills](https://github.com/vercel-labs/skills) · [fmind/agent-supagents](https://github.com/fmind/agent-supagents)
- Companions: [cross-harness-agents](cross-harness-agents.md), [docs/repository](../../docs/references/repository/GUIDE.md), [skillify](../../skillify/SKILL.md), [subagent](../../subagent/SKILL.md).
