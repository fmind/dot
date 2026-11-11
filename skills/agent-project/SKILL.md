---
name: agent-project
description: "Set up repo AGENTS.md, shared skills/agents, host bridges, discovery, and vendor skills."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/agent-project
  created: "2026-06-23"
  updated: "2026-11-11"
---

# Set Up Agents on a Project

Author shared project instructions and skills once, adding host bridges only where needed. [repository-docs](../repository-docs/SKILL.md) owns instruction prose; [mcp-setup](../agent-harnesses/references/mcp-setup.md) owns MCP registration.

## Workflow

1. **Inspect first**: preserve existing `AGENTS.md`, host configs, skills, and user settings.
1. **Create the shared layer**: follow [host-setup.md](references/host-setup.md) using the [project template](templates/AGENTS.md.template), `.agents/skills/`, and gitignored `.agents/prompts/` ([task-prompts](../task-prompts/SKILL.md)); add the Claude skills symlink, host overrides, or custom-agent files only for hosts in use.
1. **Verify discovery**: run `dot agent context --check` and host listings in [host-discovery.md](references/host-discovery.md); listing proves discovery, not compliance.
1. **Vet vendor skills**: follow [vendor-skill policy](references/vendor-skills.md) for immutable review, project scope, `skills` vs preview `gh skill`, and each tool guide's Official Skills section.
1. **Maintain**: sync changes through [repository-docs](../repository-docs/SKILL.md), including local skill references.

## Task guides

<!-- guides:start -->

- [cross-harness-agents](references/cross-harness-agents.md): Decide when a custom agent role pays off, write per-host definitions, and verify discovery.

<!-- guides:end -->

## Gotchas

- **One rule body**: never create project `CLAUDE.md` or `CLAUDE.local.md`—Claude Code loads either instead of `AGENTS.md`.
- **Vet repo configs before enabling**: review repository hooks, MCP servers, skills, plugins, and custom agents first.

## Documentation

- [AGENTS.md standard](https://agents.md) · [Agent Skills specification](https://agentskills.io/specification)
