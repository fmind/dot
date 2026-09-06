---
name: agent-project
description: Bootstrap a repository's AGENTS.md and .agents/ layout so Antigravity, Claude Code, Codex, Copilot, Grok, and OpenCode share one instruction set. Use when setting up agents on a repo.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/agent-project
  created: "2026-06-23"
  updated: "2026-09-05"
---

# Set Up Agents on a Project

Author the shared project instruction and skill layer once, then add only required host bridges. [agents-md](../agents-md/SKILL.md) owns instruction conventions; [agent-mcp](../agent-mcp/SKILL.md) owns MCP configuration.

## Workflow

1. **Inspect first**: preserve existing AGENTS.md, host files, skills, and user settings; reuse a stack-specific instruction file when one exists.
1. **Create the shared layer**: `AGENTS.md` from the [project template](templates/AGENTS.md), `.agents/skills/`, and ignored `.agents/{prompts,proposals,reports}/` for [agent-prompt](../agent-prompt/SKILL.md), [agent-proposal](../agent-proposal/SKILL.md), and [agent-report](../agent-report/SKILL.md).
1. **Bridge installed hosts**: follow [host-setup.md](references/host-setup.md) for Claude links, optional configuration, and native custom-agent locations; do not create unused host files.
1. **Verify discovery**: read [host-discovery.md](references/host-discovery.md) for listing commands and native plugin catalogs; distinguish presence from demonstrated instruction following.
1. **Keep current**: route repository changes through [update-docs](../update-docs/SKILL.md), including project-local skill references.

## Gotchas

- **One rule body**: shared rules live in `AGENTS.md`; `CLAUDE.md` is only the bridge, never a second copy.
- **Smallest override**: project configuration overrides the user's global defaults; add only what the repository needs.
- **Strict formats**: keep JSON free of comments unless the host documents JSONC, and validate TOML before launching an agent.
- **Untrusted configuration**: review a repository's hooks, MCP servers, skills, plugins, and custom-agent definitions before enabling them.

## Documentation

- [AGENTS.md standard](https://agents.md) · [Agent Skills specification](https://agentskills.io/specification)
- Companion skills: [agent-mcp](../agent-mcp/SKILL.md) (MCP servers), [agents-md](../agents-md/SKILL.md) (instruction conventions), [update-docs](../update-docs/SKILL.md) (keeping `AGENTS.md` current), [agent-prompt](../agent-prompt/SKILL.md) (`.agents/prompts/`), [agent-proposal](../agent-proposal/SKILL.md) (`.agents/proposals/`), [agent-report](../agent-report/SKILL.md) (`.agents/reports/`).
