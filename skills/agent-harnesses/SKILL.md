---
name: agent-harnesses
description: "Operate and configure Claude Code, Codex, Copilot, Grok, and OpenCode."
license: MIT
metadata:
  kind: collection
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/agent-harnesses
  created: "2026-09-16"
  updated: "2026-09-19"
---

# Agent Harnesses

Operate the selected coding-agent host without conflating its configuration, permissions, or lifecycle with another host. Antigravity has its own [agy](../agy/SKILL.md) owner.

## Workflow

Every host follows these steps; read only the matching guide for its specifics and required resources.

1. **Inspect the installed contract**: run the host's `--version` and `--help`; identify the surface (CLI, app, IDE, or cloud), workspace, configuration scope, and the session to start or resume.
1. **Refresh evolving details**: read the relevant official page and changelog before relying on flags, settings, models, or feature availability. Compare with installed help, which can omit supported flags; report version gaps before applying a newer recipe, and keep release-specific details upstream.
1. **Use the documented interface** for the session, configuration, or extension. Resolve configuration precedence and permission scope before changing execution behavior; hooks and extensions execute code.
1. **Verify** the result, resulting artifacts, and the host's own instruction or skill discovery. Use [agent-project](../agent-project/SKILL.md) for shared instruction layout and [mcp-setup](../mcp-setup/SKILL.md) for MCP registration.

## Workstation hooks

On the `fmind/dot` workstation, managed hooks call `dot agent hook` for desktop notifications and session capture; restart open harnesses after changing hook configuration.

- **Delivery**: Linux uses `notify-send` or D-Bus; macOS uses the built-in `osascript` notification command. On ChromeOS, a managed user D-Bus activation file starts the bundled Crostini `notificationd` bridge on demand. Headless sessions without a notification service skip delivery; operating-system notification settings still control visible banners.
- **Content**: Notifications show the harness, project, a short status, and the originating terminal title when available, limited to 80 characters. They have no click actions, pane numbers, or session labels and never read prompt or transcript content.
- **Capture**: Codex session-end capture respects its three-second hook limit. A Claude session that ends before its transcript exists reports a skipped capture without failing the hook; `dot agent session sync --agent claude` recovers it later.

## Task guides

<!-- guides:start -->

- [claude](references/claude/GUIDE.md): Claude Code sessions and customization.
- [codex](references/codex/GUIDE.md): Codex sessions and customization.
- [copilot](references/copilot/GUIDE.md): Copilot sessions and extensions.
- [grok](references/grok/GUIDE.md): Grok Build sessions and configuration.
- [opencode](references/opencode/GUIDE.md): OpenCode sessions and provider configuration.

<!-- guides:end -->
