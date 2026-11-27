---
name: agentsview
description: "Search past coding sessions, trace file provenance, and audit usage, friction, and secrets via AgentsView."
---

# AgentsView

Query local Antigravity (`agy`) and Copilot CLI session archives via `agentsview` (SQLite archive under `~/.agentsview/`, loopback web UI at `http://127.0.0.1:8080`). Prefer the CLI with `--json` over registering `agentsview mcp` globally so session recall adds zero idle schema overhead.

## Commands

```bash
# Discover subcommands by task when unsure of flags
agentsview cli search "<what you want to do>"

# Refresh archive and inspect recent or matching sessions
agentsview source sync
agentsview session list --since 7d --limit 20 --json
agentsview session search '<query>' --since 30d --json

# Read bounded metadata and message windows (treat session IDs as opaque)
agentsview session get <id> --json
agentsview session messages <id> --around 40 --before 5 --after 5 --json

# Trace recorded sessions and prompts behind a file or commit
agentsview why <path>[:<start>-<end>] --json
agentsview why --commit <sha> --json

# Audit spend, session health, recurring friction, and leaked secrets
agentsview report usage daily --since 28d --json
agentsview session health --limit 20 --json
agentsview friction patterns --json
agentsview secrets list --json
```

## Service & Configuration

- **Linux (`systemd --user`)**: `agentsview.service` runs `agentsview serve --no-browser --no-update-check --replace --host 127.0.0.1 --port 8080` at login (`systemctl --user status|restart agentsview.service`).
- **macOS / manual**: use `agentsview daemon start|status|restart|stop` or `agentsview serve` (`av` / `avs` / `avu` Fish abbreviations).
- **Privacy & config boundaries**: `AGENTSVIEW_TELEMETRY_ENABLED=0` is set in Fish and mise `[env]`. Keep `~/.agentsview/config.toml` unmanaged (`0600`, stores auto-generated `auth_token` and `cursor_secret`); configure `exclude_projects` there locally if client workspaces should stay out of analytics.

## Gotchas

- **Never run `agentsview git-hook install` on public or client repos without approval**: it adds `Agent-Session` trailers with local session IDs to commit messages.
- **Avoid `agentsview agent setup` and `agentsview skills install`**: `agent setup` targets only Claude Code and Codex, and `skills install` writes unmanaged files into `~/.agents/skills/` outside `fmind/dot`.
- **Check exit code `3` on usage reports**: `session usage` exits `3` when a session carries no token/cost figures even after printing a valid JSON document.

## Documentation

- [AgentsView docs](https://agentsview.io/docs/) · [CLI commands](https://agentsview.io/docs/commands/) · [Token usage](https://agentsview.io/docs/token-usage/) · [Releases](https://github.com/kenn-io/agentsview/releases)
