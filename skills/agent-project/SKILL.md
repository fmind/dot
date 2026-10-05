---
name: agent-project
description: "Set up repository AGENTS.md, shared skills and agents, host bridges, discovery, and vendor skills."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/agent-project
  created: "2026-06-23"
  updated: "2026-10-05"
---

# Set Up Agents on a Project

Author the shared project instruction and skill layer once, then add only required host bridges. [repository-docs](../repository-docs/SKILL.md) owns instruction content; [mcp-setup](../mcp-setup/SKILL.md) owns MCP configuration.

## Workflow

1. **Inspect first**: preserve existing AGENTS.md, host files, skills, and user settings; reuse a stack-specific instruction file when one exists.
1. **Create the shared layer and bridges**: follow [host-setup.md](references/host-setup.md) to start `AGENTS.md` from the [project template](templates/AGENTS.md), add `.agents/skills/` and the ignored `.agents/prompts/` inbox for [task-prompts](../task-prompts/SKILL.md), then add Claude links, optional configuration, and native custom-agent locations only for installed hosts.
1. **Verify discovery**: read [host-discovery.md](references/host-discovery.md) for listing commands and native plugin catalogs; distinguish presence from demonstrated instruction following.
1. **Install vendor skills deliberately**: follow the shared [vendor-skill policy](references/vendor-skills.md) for source review, project scope, versioning, replacement, and the current `skills` versus preview `gh skill` boundary. Select packages from the [dated official skill source audit](references/official-skills.md), which records inspected sources and gaps; recheck the selected source before installation.
1. **Keep current**: route repository changes through [repository-docs](../repository-docs/SKILL.md), including project-local skill references.

## Task guides

<!-- guides:start -->

- [cross-harness-agents](references/cross-harness-agents.md): Generate shared role profiles with Supagents and verify native harness discovery.

<!-- guides:end -->

## Gotchas

- **Keep one rule body**: shared rules live in `AGENTS.md`; never add a project `CLAUDE.md`, which Claude Code would load instead of `AGENTS.md`.
- **Add only needed overrides**: project configuration overrides the user's global defaults; add only what the repository needs.
- **Keep configuration formats strict**: keep JSON free of comments unless the host documents JSONC, and validate TOML before launching an agent.
- **Review repository configuration first**: review a repository's hooks, MCP servers, skills, plugins, and custom-agent definitions before enabling them.

## Documentation

- [AGENTS.md standard](https://agents.md) · [Agent Skills specification](https://agentskills.io/specification)
