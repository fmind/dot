---
name: notifications
description: "Diagnose or change managed turn notifications and their hooks per host."
---

# Turn Notifications

On the `fmind/dot` workstation, notifications mean it is your turn: the main session is idle or needs an answer. `dot agent session sync` captures sessions from each harness's own store. Restart open harnesses after changing notification configuration.

- **Claude and Grok**: `Notification` hooks select `idle_prompt` for “Your turn” and actionable permission/question events for “Needs your input”. Claude's idle alert waits about 60 seconds without typing. No `Stop` notifier is managed (Grok's list stays empty) because those hooks run before continuation decisions. Informational notifications and background-agent completion do not trigger the managed notifier.
- **Codex and Copilot**: native attention notifications are enabled; no `Stop` / `agentStop` desktop hooks are managed, avoiding premature and duplicate alerts. Native alerts depend on the host's focus detection and terminal/OS support.
- **Antigravity**: the managed `Stop` notifier requires `fullyIdle: true`, including through the `antigravity` alias; native input notifications remain enabled.
- **OpenCode**: native desktop attention alerts exclude child sessions. Sounds are disabled because child completion also plays them.
- **Delivery**: Linux uses `notify-send` or D-Bus; macOS uses the built-in `osascript` notification command. On ChromeOS, a managed user D-Bus activation file starts the bundled Crostini `notificationd` bridge on demand. Headless sessions without a notification service skip delivery; operating-system notification settings still control visible banners.
- **Content**: Managed notifications show the harness, project, a short status, and the originating terminal title when available, limited to 80 characters. They have no click actions, pane numbers, or session labels and never read prompt or transcript content. Native notifications use the harness's own presentation.
- **Failures**: a failed notification writes one stderr line and exits 0, so it never fails the agent turn.
