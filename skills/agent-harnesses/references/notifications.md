---
name: notifications
description: "Diagnose or change managed turn notifications and brain session-context hooks per host."
---

# Turn Notifications

On `fmind/dot`, notifications signal that the main session is idle or awaiting input. Restart open harnesses after config changes.

- **Claude**: `Notification` hooks route `idle_prompt` (~60s idle) to “Your turn” and permission/question events to “Needs your input”; informational and background-agent events are ignored, and no `Stop` hook is managed (runs before continuation decisions).
- **Copilot**: native attention notifications are enabled (relying on terminal/OS focus); no `Stop`/`agentStop` hooks are managed.
- **Antigravity**: managed `Stop` requires `fullyIdle: true` and skips subagents, unfinished background work, and print runs (`dot` inspects the nearest agy ancestor's `-p`/`--print`/`--prompt`). Native `notifications` stay off (default; unmanaged because agy drops `false` on save, and OSC 9 doubled Ghostty alerts while failing in ttyd).
- **OpenCode**: native desktop attention alerts skip child sessions; sounds stay off because child completions trigger them.
- **Pi**: `~/.pi/agent/extensions/dot-notify.ts` fires on `agent_settled` (after retries/queued messages) and skips print, JSON, RPC, and user-aborted runs; `dot agent doctor` reports `hooks=absent` if missing.
- **OS delivery**: Linux uses `notify-send` (`libnotify-bin`); macOS uses `osascript`. When `agent.notify.sound` is on (default), macOS plays `Glass` and Linux suppresses server sound to play `~/.cache/dot/notify.wav` via `pw-play` or `paplay` (ChromeOS `notificationd` is silent and D-Bus-activated on demand). `dot` resolves `DBUS_SESSION_BUS_ADDRESS` else `$XDG_RUNTIME_DIR/bus`, skipping delivery without a bus and playing chime-only when no notification daemon exists (containers, Android Linux VM). On macOS, `usernoted` mutes `osascript` until `Script Editor.app` registers once: run `display notification "test" with title "Script Editor" sound name "Glass"` (`Cmd+R`) in `Script Editor.app` and enable Banners/Alerts + sound + Always previews in `System Settings > Notifications > Script Editor`.
- **Short, private content**: titles show status (✅ your turn, ⏳ needs input), harness, and project (<=80 chars). In Zellij, `zellij action list-panes` supplies session/tab (`agent.notify.tab`) and stripped pane title (`agent.notify.title`, macOS subtitle), both default on (disable on shared screens); otherwise the body reads “Your turn” or “Needs your input”. Alerts have no click actions, never read prompts/transcripts, and log one stderr line with exit 0 on failure so turns never abort.
- **Brain session context**: when present, apply wires `~/fmind/brain/settings/hooks/session-context.py` as a 30s Claude `SessionStart` hook (no matcher) and `~/fmind/brain/settings/hooks/agy-context.py` as agy's 30s `brain-context` `SessionStart` hook injecting a persistent `systemMessage` ([agy](../../agy/references/agy/GUIDE.md) explains why `PreInvocation` is unsuitable).
