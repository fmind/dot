---
name: notifications
description: "Configure Zellij OSC 7501 turn attention, mobile push settings, and brain session-context hooks."
---

# Turn Attention and Hooks

On `fmind/dot`, Zellij 0.46's built-in `attention` mode tracks coding-agent turns directly via OSC 7501 instead of desktop toast popups or sound chimes. Restart open harnesses after config changes.

- **Zellij attention & PTY colors (`dot_config/zellij/config.kdl`)**: sets `env { TERM "xterm-256color" }` (keeps panes 256-color even when launched from agent `TERM=dumb` shells), `host_notification_protocol "off"` (keeps pane OSC alerts inside Zellij without forwarding OS banners to Ghostty), `attention.startup_card "never"`, `attention.idle_rule "watched"`, and `attention.desktop_notifications` all `false`; binds `Alt i` (`GoToNextAttention`) and `Alt Shift i` (`ToggleSessionCard`) in `shared` so both work in Locked mode (`Ctrl g`).
- **Native OSC 7501 harnesses (`agy`, `claude`, `copilot`, `opencode`, `pi`)**: all five emit OSC 7501 attention states natively inside Zellij; no `dot` notification hooks or sound chimes remain.
- **Disabled local desktop/sound alerts**: `copilot` enforces `notifications: false`, `dot_config/private_opencode/modify_cli.json` enforces `attention: {notifications: false, sound: false}` in `~/.config/opencode/cli.json`, `agy` leaves native `notifications` unset, and apply retires legacy `notify` (`~/.gemini/config/hooks.json`), `Notification` (`~/.claude/settings.json`), `~/.pi/agent/extensions/dot-notify.ts`, and `~/.cache/dot/notify.wav`.
- **Preserved mobile / Remote Control push**: `claude` keeps `inputNeededNotifEnabled: true` and `agentPushNotifEnabled: true`, and Antigravity Remote Control keeps `enableNotificationsForSpecialEvents: true`.
- **Brain session context**: `fmind/brain`'s `mise run setup` registers `~/fmind/brain/settings/hooks/session-context.py` as a 30s Claude `SessionStart` hook (no matcher) and `~/fmind/brain/settings/hooks/agy-context.py` as agy's 30s `brain-context` `SessionStart` hook injecting a persistent `systemMessage` ([agy cli](../../agy/references/cli/GUIDE.md) explains why `PreInvocation` is unsuitable); `dot` preserves both on apply.
