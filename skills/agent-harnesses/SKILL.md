---
name: agent-harnesses
description: "Operate and configure Claude Code, Copilot, OpenCode, and Pi; add or fix MCP servers across coding hosts and verify access."
license: MIT
metadata:
  kind: collection
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/agent-harnesses
  created: "2026-09-16"
  updated: "2026-11-13"
---

# Agent Harnesses

Operate the selected coding-agent host without mixing another host's settings, permissions, or lifecycle. [agy](../agy/SKILL.md) owns Antigravity; [claude](references/claude.md) owns Claude Code.

## Workflow

1. **Check version-specific docs before calling a feature missing**: `--help` can omit supported flags.
1. **Verify precedence and permissions before changing execution**: hooks and extensions run code.
1. **Verify behavior and discovery**: check the host's own instruction/skill loading; [agent-project](../agent-project/SKILL.md) owns shared repo layout and [mcp-setup](references/mcp-setup.md) owns MCP registration.

## Task guides

<!-- guides:start -->

- [claude](references/claude.md): Claude Code sessions, managed settings, headless flags, hooks, and background tasks.
- [copilot](references/copilot/GUIDE.md): Copilot sessions and extensions.
- [mcp-setup](references/mcp-setup.md): Add, vet, or fix MCP servers across coding hosts and verify live access.
- [notifications](references/notifications.md): Configure Zellij OSC 7501 turn attention, mobile push settings, and brain session-context hooks.
- [opencode](references/opencode/GUIDE.md): OpenCode sessions and provider configuration.
- [pi](references/pi.md): Pi sessions, providers, project trust, extensions, and headless runs.

<!-- guides:end -->

## Gotchas

- **Edit managed keys in `fmind/dot`**: `modify_*` chezmoi templates in `~/.local/share/chezmoi` merge Claude, Copilot, OpenCode, and Pi settings—direct edits to managed keys (including via `/config`) revert on `chezmoi apply --force`, while unmanaged keys survive. Edit source, preview with `mise run diff` (skips encrypted targets), and apply.
- **Vet vendor skills and packages**: Pi packages/extensions run in-process; install requested packages only via [vendor-skill policy](../agent-project/references/vendor-skills.md) under one package manager.
