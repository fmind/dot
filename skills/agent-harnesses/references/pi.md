---
name: pi
description: "Pi sessions, providers, project trust, extensions, and headless runs."
---

# Pi

Operate Pi (`pi`), a minimal harness (`read`, `bash`, `edit`, `write`) with no approval prompts or sandbox—every run uses full account permissions. Preserve managed workstation settings.

## Workflow

Follow the shared [workflow](../SKILL.md#workflow); host specifics:

1. **Read bundled docs first**: inspect `"$(mise where pi)/pi/docs"` and `pi/examples/extensions` before web docs, since minors change flags, settings, and session formats.
1. **Resolve the provider** via [model-providers](../../model-providers/SKILL.md). Managed default is `google-vertex` (ADC, high thinking): set `GOOGLE_CLOUD_PROJECT` (or `GCLOUD_PROJECT`) per shell or project (`google-vertex.ts` defaults `GOOGLE_CLOUD_LOCATION` to `global` when unset; pass `GOOGLE_CLOUD_LOCATION=global` explicitly for `pi auth check --provider google-vertex --json`, which skips extensions). `/login` is user-owned; credentials resolve as `--api-key` > `auth.json` > `models.json` `apiKey` > env.
1. **Close stdin on headless runs**: `pi -p` blocks on open stdin; append `</dev/null`:

   ```bash
   pi -p '<task>' </dev/null                          # print the answer and exit
   pi -p --mode json '<task>' </dev/null              # one JSON event per line
   pi -p -c '<follow-up>' </dev/null                  # continue this directory's latest session
   pi -p --model google-vertex/<model-id>:high '<task>' </dev/null
   ```

   Use `--session <id>`, `--fork <id>`, or `--no-session`. Untrusted project resources are skipped headlessly unless `-a` trusts them once (`-na` ignores them).
1. **Verify discovery and diffs**: Pi concatenates `~/.pi/agent/AGENTS.md` plus one file per ancestor directory from `/` to cwd (`AGENTS.override.md` > `AGENTS.md` > `CLAUDE.md`), and loads `~/.agents/skills` plus trusted `.agents/skills` (`/skill:<name>` forces one; startup header lists loaded items). Verify diffs and checks, not session files.

## Configuration

User state lives in `~/.pi/agent/` (`PI_CODING_AGENT_DIR`): `settings.json` (rewritten by Pi while preserving unknown keys; edit `private_dot_pi/` for managed keys, see [settings](https://pi.dev/docs/latest/settings)), `auth.json`, `trust.json`, `mcp.json`, `models.json`, `extensions/`, and `sessions/`.

- **Project trust gates code, not context files**: trust enables `.pi/settings.json`, `.pi/mcp.json`, `.pi/{extensions,skills,prompts,themes}`, `.pi` system prompts, and `.agents/skills` for the folder and all subdirectories—`dot trust` writes repo roots only; never trust a parent directory holding third-party clones.
- **Extensions run in-process**: TypeScript in `~/.pi/agent/extensions/`, trusted `.pi/extensions/`, and `pi install <source>` packages run with full permissions at startup; vet per [vendor-skill policy](../../agent-project/references/vendor-skills.md). Managed `google-vertex.ts` resolves dynamic Vertex location and startup model/thinking state.
- **Built-in MCP**: `pi mcp add`/`list` and `~/.pi/agent/mcp.json` (`mcpServers`, stdio or streamable HTTP; `--no-mcp` disables per run) per [mcp-setup](mcp-setup.md).
- **JSONL session trees**: `~/.pi/agent/sessions/--<cwd>--/<timestamp>_<session-id>.jsonl` stores branches; `/fork` and `/clone` copy prior entries, which `dot agent session sync` deduplicates with the parent.

## Gotchas

- **Restrict tools explicitly**: there is no prompt mode—pass `--tools read`, `--exclude-tools`, `--no-tools`, or isolate untrusted work in a container.
- **Keep `fd` and `rg` on PATH**: if missing, Pi downloads latest binaries into `~/.pi/agent/bin` (signaling a missing mise PATH).
- **Let mise own upgrades**: mise sets `PI_SKIP_VERSION_CHECK=1` and `PI_TELEMETRY=0` (`enableInstallTelemetry` is off); never run `pi update self`—use [upgrade-tools](../../upgrade-tools/SKILL.md).
- **Sharing publishes data**: `/share` (gist/Radius) and `/bug` upload data; require explicit approval.

## Documentation

- [Documentation](https://pi.dev/docs/latest/) · [Settings](https://pi.dev/docs/latest/settings) · [Extensions](https://pi.dev/docs/latest/extensions) · [Security](https://pi.dev/docs/latest/security)
- Releases: [GitHub releases](https://github.com/earendil-works/pi/releases) · [changelog](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/CHANGELOG.md)
- Companion skills: [model-providers](../../model-providers/SKILL.md), [mcp-setup](mcp-setup.md), [agent-project](../../agent-project/SKILL.md).
