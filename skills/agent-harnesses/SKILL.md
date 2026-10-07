---
name: agent-harnesses
description: "Operate and configure Claude Code, Codex, Copilot, Grok, and OpenCode."
license: MIT
metadata:
  kind: collection
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/agent-harnesses
  created: "2026-09-16"
  updated: "2026-10-07"
---

# Agent Harnesses

Operate the selected coding-agent host without conflating its configuration, permissions, or lifecycle with another host. Antigravity has its own [agy](../agy/SKILL.md) owner.

## Workflow

Every host follows these steps; read only the matching guide for its specifics and required resources.

1. **Check official docs for version-sensitive features**: read the relevant official page and changelog before relying on flags, settings, models, or feature availability; installed help can omit supported flags. Report version gaps before applying a newer recipe, and keep release-specific details upstream.
1. **Resolve precedence and permission scope first**: before changing execution behavior; hooks and extensions execute code.
1. **Verify** the result, resulting artifacts, and the host's own instruction or skill discovery. Use [agent-project](../agent-project/SKILL.md) for shared instruction layout and [mcp-setup](../mcp-setup/SKILL.md) for MCP registration.

## Task guides

<!-- guides:start -->

- [claude](references/claude/GUIDE.md): Claude Code sessions and customization.
- [codex](references/codex/GUIDE.md): Codex sessions and customization.
- [copilot](references/copilot/GUIDE.md): Copilot sessions and extensions.
- [grok](references/grok/GUIDE.md): Grok Build sessions and configuration.
- [notifications](references/notifications.md): Diagnose or change managed turn notifications and their hooks per host.
- [opencode](references/opencode/GUIDE.md): OpenCode sessions and provider configuration.

<!-- guides:end -->

## Gotchas

- **Edit managed host keys in fmind/dot**: on this workstation, Claude, Codex, Copilot, Grok, and OpenCode settings are merged from `modify_*` chezmoi templates in `~/.local/share/chezmoi`. A direct edit to a managed key (including through `/config` or a host's settings skill) reverts on `chezmoi apply --force`; unmanaged keys survive. Change the source, preview with `chezmoi diff`, then apply.
