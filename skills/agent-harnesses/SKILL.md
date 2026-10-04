---
name: agent-harnesses
description: "Operate and configure Claude Code, Codex, Copilot, Grok, and OpenCode."
license: MIT
metadata:
  kind: collection
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/agent-harnesses
  created: "2026-09-16"
  updated: "2026-10-04"
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

On the `fmind/dot` workstation, notifications mean it is your turn: the main session is idle or needs an answer. `dot agent session sync` captures sessions from each harness's own store. Restart open harnesses after changing notification configuration.

- **Claude and Grok**: `Notification` hooks select `idle_prompt` for “Your turn” and actionable permission/question events for “Needs your input”. Claude's idle alert waits about 60 seconds without typing. No `Stop` notifier is managed (Grok's list stays empty) because those hooks run before continuation decisions. Informational notifications and background-agent completion do not trigger the managed notifier.
- **Codex and Copilot**: native attention notifications are enabled; no `Stop` / `agentStop` desktop hooks are managed, avoiding premature and duplicate alerts. Native alerts depend on the host's focus detection and terminal/OS support.
- **Antigravity**: the managed `Stop` notifier requires `fullyIdle: true`, including through the `antigravity` alias; native input notifications remain enabled.
- **OpenCode**: native desktop attention alerts exclude child sessions. Sounds are disabled because child completion also plays them.

- **Delivery**: Linux uses `notify-send` or D-Bus; macOS uses the built-in `osascript` notification command. On ChromeOS, a managed user D-Bus activation file starts the bundled Crostini `notificationd` bridge on demand. Headless sessions without a notification service skip delivery; operating-system notification settings still control visible banners.
- **Content**: Managed notifications show the harness, project, a short status, and the originating terminal title when available, limited to 80 characters. They have no click actions, pane numbers, or session labels and never read prompt or transcript content. Native notifications use the harness's own presentation.
- **Failures**: a failed notification writes one stderr line and exits 0, so it never fails the agent turn.

## Task guides

<!-- guides:start -->

- [claude](references/claude/GUIDE.md): Claude Code sessions and customization.
- [codex](references/codex/GUIDE.md): Codex sessions and customization.
- [copilot](references/copilot/GUIDE.md): Copilot sessions and extensions.
- [grok](references/grok/GUIDE.md): Grok Build sessions and configuration.
- [opencode](references/opencode/GUIDE.md): OpenCode sessions and provider configuration.

<!-- guides:end -->
