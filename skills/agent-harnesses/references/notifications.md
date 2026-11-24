---
name: notifications
description: "Zellij OSC 7501 turn attention, push alerts, brain context hooks."
---

# Turn Attention and Hooks

On `fmind/dot`, Zellij 0.46's built-in `attention` mode tracks coding-agent turns via OSC 7501 and forwards native terminal notifications (`OSC 9/777/99`) to Ghostty for OS popups. Restart open harnesses after config changes.

- **Zellij attention & PTY colors (`dot_config/zellij/config.kdl`)**: sets `env { TERM "xterm-256color" }` (keeps panes 256-color even when launched from agent `TERM=dumb` shells), `host_notification_protocol "auto"` (forwards pane OSC alerts to Ghostty for native OS popups), `attention.startup_card "attention"`, `attention.idle_rule "watched"`, `attention.track_commands true`, and `attention.desktop_notifications` (`needs_you`, `failed`, `done`) all `true`; binds `Alt i` (`GoToNextAttention`) and `Alt Shift i` (`ToggleSessionCard`) in `shared` so both work in Locked mode (`Ctrl g`), and unbinds `Alt o` in `shared_except "locked"`.
- **Native OSC 7501 & terminal notifications (`agy`, `copilot`)**: both emit OSC 7501 attention states natively inside Zellij (`agy` `1.5.10+` stays in working state while waiting on non-daemon background subagents/tasks), and `agy` (`notifications: true`) and `copilot` (`notifications: true`) emit native terminal desktop notifications forwarded through Zellij to Ghostty. Apply retires legacy `~/.cache/dot/notify.wav` on macOS.
- **Preserved mobile / Remote Control push**: Antigravity Remote Control keeps `enableNotificationsForSpecialEvents: true`.
- **Brain session context & multi-tenant isolation**: a brain's setup can install a `SessionStart` context hook for agy (`~/.gemini/config/hooks.json`, injecting a persistent `systemMessage`; `PreInvocation` fires on every model call — see Brain Framework [operations guide](https://fmind.github.io/brain-framework/operations/)). On multi-tenant workstations, gate hook output on canonicalized (`realpath`) containment under a trusted tenant root directory (with repo owner only as an extra AND-condition), keep `~/.gemini/config/hooks.json` at `0600` (not managed by `fmind/dot`), and keep client skills project-local per [project-setup](project-setup.md).
