---
name: agent-harnesses
description: "Operate Antigravity (agy CLI, Remote Control, SDK) and Copilot; host bridges/discovery, vendor skills, MCP setup, headless reviews, prompts."
license: MIT
metadata:
  kind: collection
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/agent-harnesses
  created: "2026-09-16"
  updated: "2026-11-22"
---

# Agent Harnesses & Project Setup

Operate Antigravity (`agy`) and Copilot, register MCP servers, and set up shared repository `AGENTS.md`, `.agents/skills/`, host bridges, and vendor skills without mixing settings or lifecycles.

## Workflow

1. **Check version docs before calling features missing**: `--help` can omit flags.
1. **Verify precedence & permissions**: hooks, repo configs, and extensions run code; vet before enabling.
1. **Verify discovery**: run `dot context --check` and host listings ([project-setup](references/project-setup.md), [host-discovery](references/host-discovery.md)).

## Task guides

<!-- guides:start -->

- [agy-cli](references/agy-cli/GUIDE.md): CLI sessions, managed settings, auth, custom agents, and completions.
- [antigravity-sdk](references/antigravity-sdk/GUIDE.md): Python SDK orchestration, policy, subagents, and lifecycle.
- [copilot](references/copilot.md): Copilot CLI sessions, non-interactive flags, folder trust, and extensions.
- [cross-harness-agents](references/cross-harness-agents.md): Decide when a custom agent role pays off, write per-host definitions, and verify discovery.
- [headless-review](references/headless-review/GUIDE.md): Structured headless agy review with JSON schema and fail-closed exit checks.
- [mcp-setup](references/mcp-setup.md): Add, vet, or fix MCP servers across coding hosts and verify live access.
- [notifications](references/notifications.md): Zellij OSC 7501 turn attention, push alerts, brain context hooks.
- [project-setup](references/project-setup.md): Set up repo AGENTS.md, shared skills, host bridges, discovery, and vendor skills.
- [remote-control](references/remote-control.md): Headless agy Remote Control: session tunnels, daemon, and project registry.
- [statusline](references/statusline.md): Configure or diagnose the managed agy status line and terminal title.
- [task-prompts](references/task-prompts/GUIDE.md): Write task, delegation, and handoff prompts; resume, compact, or fork agy sessions.

<!-- guides:end -->

## Gotchas

- **Edit managed keys in `fmind/dot`**: `modify_*` templates merge Antigravity and Copilot settings—managed edits revert on `chezmoi apply --force`. Edit source, preview via `mise run diff`, then apply.

## Documentation

- [Antigravity CLI](https://antigravity.google/docs/cli/reference/) · [Python SDK](https://antigravity.google/docs/sdk/overview/) · [Remote Control](https://antigravity.google/docs/remote-control/) · [MCP](https://modelcontextprotocol.io/docs/getting-started/intro) · [AGENTS.md](https://agents.md)
- Companions: [subagent](../subagent/SKILL.md), [skillify](../skillify/SKILL.md), [docs](../docs/SKILL.md), [dot-cli](../dot-cli/SKILL.md).
