---
name: remote-control
description: "Run agy Remote Control: per-session tunnels, the headless daemon, and project registry sync."
---

# Headless Remote Control

Use the CLI daemon without installing the desktop app. Read [Remote Control](https://antigravity.google/docs/remote-control/) before changing its persistent OS service. `agy remote-control status` is read-only; `start` registers/restarts and `stop` unregisters it. Restart only when no remote task is running; verify the browser project picker separately.

For one terminal session, `agy --remote-control` or `/remote-control` opens a tunnel that lives only as long as that process and prints a link to the conversation; `/remote-control off` closes it. The daemon is one per machine: a systemd user service `antigravity-cli-daemon` on Linux (`journalctl --user -u antigravity-cli-daemon -n 50`), or since 1.2.14 an unsupervised background process when no systemd user manager exists. `start --name <name>` sets `cliRemoteControlHostname`; `remoteControlHostname` belongs to the desktop app. Since 1.3.4, the browser Settings modal syncs supported CLI settings (permissions, queued messages, AI credits, telemetry, and artifact review) back to `settings.json`, while "Always allow" rules approved in the browser save to the shared `config.json`. Remote Control requires a Google account or organization with Remote Control enabled and is unsupported under `AGY_ADC_AUTH` (`--remote-control` exits with an error and `/remote-control` is hidden).

The daemon reads `~/.gemini/config/config.json` only at start: run `agy remote-control start` after applying changes. On Linux a chezmoi drop-in gives the unit mise shims on `PATH`; apply reloads systemd when it changes but never restarts the daemon, so restart it yourself when no remote task is running. Keep the registry local in `~/.gemini/config/projects/`; the [project sync script](../scripts/sync-projects.py) makes it match the Git checkouts in `~/*/*/.git`:

```bash
python3 ~/.agents/skills/agy/scripts/sync-projects.py          # preview
python3 ~/.agents/skills/agy/scripts/sync-projects.py --apply
```

It adds missing checkouts and removes folder entries outside the glob or duplicated (symlinked checkouts resolve to one entry); entries without folders, such as the native default project, stay. Existing names and metadata are preserved, and new entries are written atomically. Malformed registry JSON fails with a diagnostic before entries are changed. This registers projects, not semantic code indexes.
