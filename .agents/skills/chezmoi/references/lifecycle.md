# Chezmoi Target Lifecycle and Machine Conventions

Operational details for hooks, modifiers, externals, systemd units, Neovim, and Zellij in `fmind/dot` ([parent skill](../SKILL.md)).

## Hooks and repeatability

- **Repeatable modifiers**: test existing-target and second-pass behavior in `dot/tests/` — Bash/profile modifiers (`managed-block.tmpl`) in `test_shell_modifiers.py` and JSON/TOML modifiers (`config-merge.tmpl`) in `test_harness_config.py`.
- **`run_*` scripts**: plain hooks execute every apply; `once_` and `onchange_` rerun only when template/content hashes change.
- **Linux user timers (`dot_config/systemd/user/`)**: `run_onchange_after_systemd-user-reload.sh.tmpl` tracks sha256 hashes of `antigravity-cli-daemon.service.d/path.conf` and `antigravity-cli-daemon-update.{service,timer}`, runs `systemctl --user daemon-reload`, and starts the update timer while printing a manual restart hint for `antigravity-cli-daemon.service` (never auto-restarts it because Remote Control sessions may run inside).

## Managed workstation targets

- **External pins**: `fmind/theme` commit and font release archives use SHA-256 externals; checksum mismatches fail `chezmoi apply`. `mise run upgrade` bumps the theme pin only when every `COPIED` block in `dot/dot_tasks/theme_pin.py` matches.
- **Neovim (`dot_config/nvim/`) & `nvim-tty`**: `dot_local/bin/executable_nvim-tty` sets non-interactive-safe `EDITOR`: opens `nvim` on TTY stdin/stdout and exits `1` cleanly in headless agent shells. Fold lazy plugin bumps back from `~/.config/nvim/lazy-lock.json` using `chezmoi re-add --source "$(pwd -P)"` (symlinked targets require resolved repo paths; regenerate `mise.lock` via `mise run lock`, never `re-add`).
- **Zellij (`dot_config/zellij/config.kdl`)**: sets `env { TERM "xterm-256color" }` so panes launched from `TERM=dumb` agent shells keep 256-color PTYs, and disables `host_notification_protocol` / desktop toasts while keeping native OSC 7501 attention tracking ([notifications](../../../../skills/agent-harnesses/references/notifications.md)).
