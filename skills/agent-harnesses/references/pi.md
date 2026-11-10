---
name: pi
description: "Pi sessions, providers, project trust, extensions, and headless runs."
---

# Pi

Operate Pi (`pi`), a minimal coding harness: four built-in tools (`read`, `bash`, `edit`, `write`), no approval prompts, and no sandbox, so every run acts with the account's full permissions. Preserve the managed user configuration; this guide owns session operation, not a second copy of workstation settings.

## Workflow

Follow the shared [workflow](../SKILL.md#workflow) and project instructions; host specifics:

1. **Read the installed docs first**: Pi ships its version-matched manual and example extensions beside the binary, under `"$(mise where pi)/pi/docs"` and `pi/examples/extensions`. Settings, flags, and session formats change between minors, so read those files before the website or memory.
1. **Resolve the provider** through [model-providers](../../model-providers/SKILL.md). The managed seed is Agent Platform through ADC (`google-vertex`, high thinking), which needs `GOOGLE_CLOUD_PROJECT` and `GOOGLE_CLOUD_LOCATION` in the launching shell; without them Pi starts on the first provider that has credentials. Check readiness without printing a credential: `pi auth check --provider <id> --json` exits 0 when ready. `/login` signs in to a subscription or stores a key and belongs to the user. Credentials resolve as `--api-key`, then `auth.json`, then a `models.json` `apiKey`, then the environment.
1. **Run headless with stdin closed**: `pi -p` reads piped stdin and waits on one that never closes, so end the command with `</dev/null`.

   ```bash
   pi -p '<task>' </dev/null                          # print the answer and exit
   pi -p --mode json '<task>' </dev/null              # one JSON event per line
   pi -p -c '<follow-up>' </dev/null                  # continue this directory's latest session
   pi -p --model google-vertex/<model-id>:high '<task>' </dev/null
   ```

   `--session <id>` reopens one session, `--fork <id>` branches it into a new file, and `--no-session` writes none. Headless runs skip project resources that were never trusted; pass `-a` to trust them for one run, or `-na` to ignore them.
1. **Verify discovery and results**: Pi reads `~/.pi/agent/AGENTS.md` (the managed persona link), then one context file per directory from the filesystem root down to the working directory (`AGENTS.override.md`, else `AGENTS.md`, else `CLAUDE.md`), and concatenates them. It reads skills from `~/.agents/skills` and project `.agents/skills` natively; `/skill:<name>` forces one. The startup header lists loaded context files, skills, and extensions. Inspect the resulting diff and checks; a session file is not completion proof.

## Configuration

Pi keeps user state in `~/.pi/agent/` (`PI_CODING_AGENT_DIR` relocates it): `settings.json`, `auth.json`, `trust.json`, `mcp.json`, `models.json`, `extensions/`, and `sessions/`. Pi rewrites `settings.json` itself (on `/model`, `/settings`, and after an upgrade) and keeps keys it does not know. In the dot repository, change the chezmoi source under `dot_pi/` only when workstation configuration is in scope. Use the [settings reference](https://pi.dev/docs/latest/settings) for keys; `.pi/settings.json` overrides it per project once the project is trusted.

- **Project trust gates code, not instructions**: a trust decision covers `.pi/settings.json`, `.pi/mcp.json`, `.pi/extensions`, `.pi/skills`, `.pi/prompts`, `.pi/themes`, the `.pi` system-prompt files, and project `.agents/skills`. Context files load without it. A decision applies to every folder below the trusted one, so `dot trust` writes repository roots only; never trust a workspace that holds third-party clones.
- **Extensions are in-process code**: TypeScript files in `~/.pi/agent/extensions/` and trusted `.pi/extensions/` run with full permissions at startup, and `pi install <source>` adds packages that do the same. Review one like a dependency, per the [vendor-skill policy](../../agent-project/references/vendor-skills.md). The managed `dot-notify.ts` is the turn alert ([notifications](notifications.md)).
- **MCP is built in**: `pi mcp add`, `pi mcp list`, and `~/.pi/agent/mcp.json` (`mcpServers`, stdio or streamable HTTP); `--no-mcp` disables it for a run. [mcp-setup](../../mcp-setup/SKILL.md) owns transport and trust boundaries.
- **Sessions are JSONL trees**: `~/.pi/agent/sessions/--<cwd>--/<timestamp>_<session-id>.jsonl` holds every branch of a conversation; `/fork` and `/clone` copy the earlier entries into a new file. `dot agent session sync` archives them and counts a fork's copied entries once, with their parent.

## Gotchas

- **Nothing asks before a command runs**: there is no permission mode to tighten. Limit a run with `--tools read` (an allowlist), `--exclude-tools`, or `--no-tools`, or run Pi inside a container for untrusted work.
- **Keep `fd` and `rg` on PATH**: Pi downloads the latest release of either into `~/.pi/agent/bin` when it is missing; mise provides both, so a download means the launching shell lost its mise PATH.
- **mise owns the version**: `PI_SKIP_VERSION_CHECK=1` and `PI_TELEMETRY=0` are exported by mise and `enableInstallTelemetry` is managed off. Never run `pi update self`; upgrade through [upgrade-tools](../../upgrade-tools/SKILL.md).
- **Sharing is publication**: `/share` uploads the session to a gist or to Radius, and `/bug` uploads diagnostics; require explicit sharing authority for either.

## Documentation

- [Documentation](https://pi.dev/docs/latest/) · [Settings](https://pi.dev/docs/latest/settings) · [Extensions](https://pi.dev/docs/latest/extensions) · [Security](https://pi.dev/docs/latest/security)
- Releases: [GitHub releases](https://github.com/earendil-works/pi/releases) · [changelog](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/CHANGELOG.md)
- Companion skills: [model-providers](../../model-providers/SKILL.md), [mcp-setup](../../mcp-setup/SKILL.md), [agent-project](../../agent-project/SKILL.md).
