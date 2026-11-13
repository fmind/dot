---
name: claude
description: "Claude Code sessions, managed settings, headless flags, hooks, and background tasks."
---

# Claude Code (`claude`)

Operate Claude Code alongside `fmind/dot` managed configuration; [agent-project](../../agent-project/SKILL.md) owns repo bridges, [mcp-setup](mcp-setup.md) owns MCP servers, and [notifications](notifications.md) owns turn attention and preserved hooks.

## Managed Setup (`fmind/dot`)

`private_dot_claude/modify_private_settings.json` merges `~/.claude/settings.json`:

- **Seeded defaults** (changeable via `/model` and `/effort`): `model: "fable"`, `fallbackModel: ["sonnet"]`, and `effortLevel: "high"` on `claude-fable-5-1`, `claude-fable-5-2`, and `claude-opus-5-5`.
- **Managed keys** (re-applied on `chezmoi apply --force`): `permissions.defaultMode: "bypassPermissions"`, `editorMode: "vim"`, `theme: "light-ansi"`, `tui: "fullscreen"`, `worktree.baseRef: "head"`, `respectGitignore: false`, `autoContinueAtUsageLimit: true`, `remoteControlAtStartup: true`, `agentPushNotifEnabled: true`, `inputNeededNotifEnabled: true`, empty commit/PR attribution, disabled `claude.ai` connectors/plugins/skills sync, and non-interactive CLI env (`GIT_TERMINAL_PROMPT=0`, `GH_PROMPT_DISABLED=1`, `CLOUDSDK_CORE_DISABLE_PROMPTS=1`), preserving host `SessionStart` hooks and retiring legacy `Notification` turn hooks.
- **Global links & trust**: `~/.claude/CLAUDE.md` → `~/.agents/AGENTS.md`, `~/.claude/skills` → `~/.agents/skills`; `dot trust` manages workspace trust and `permissions.additionalDirectories`.

## Workflow

1. **Run non-interactive (`-p` / `--print`)**:

   ```bash
   claude -p "Summarize failing tests" --output-format json --no-session-persistence
   claude -p "Extract findings" --output-format json --json-schema '{"type":"object","properties":{"ok":{"type":"boolean"}},"required":["ok"]}'
   ```

   Pass `--no-session-persistence` on disposable automation (`CLAUDE_CODE_FORCE_SESSION_PERSISTENCE=1` is set in managed env so sub-sessions archive cleanly), and bound unattended runs with `--max-turns <N>` or `--max-budget-usd <amount>`.

1. **Isolate clean-room runs with `--bare`**: skips settings/plugin hooks, LSP, `CLAUDE.md` auto-discovery, auto-memory, and keychain/OAuth reads (`ANTHROPIC_API_KEY`, `apiKeyHelper`, or Vertex/Bedrock credentials only); pass `--system-prompt`, `--settings`, `--mcp-config`, and `--add-dir` explicitly.
1. **Manage background sessions (`--bg`)**: `claude --bg "<prompt>"` prints a session ID controlled via `claude agents` (lists background sessions, **not** custom roles), `claude logs <id>`, `claude attach <id>`, `claude stop <id>`, and `claude rm <id>`.

## Gotchas

- **Project skills need `.claude/skills`**: Claude Code ignores `.agents/skills/` directly unless `.claude/skills -> ../.agents/skills` is linked ([agent-project](../../agent-project/SKILL.md)).
- **MCP scope privacy**: `claude mcp add --scope local` (default) keeps credentials per-project in `~/.claude.json`; `--scope project` writes shared `.mcp.json` (requires approval; `claude mcp reset-project-choices` resets).
- **Never export `DISABLE_TELEMETRY=1` globally**: Claude Code disables Remote Control when `DISABLE_TELEMETRY` is set in the environment; prefix `DISABLE_TELEMETRY=1` per command only for `skills`.

## Documentation

- `claude --help` · [Claude Code docs index](https://code.claude.com/docs/llms.txt) · [Settings](https://code.claude.com/docs/en/settings) · [Hooks](https://code.claude.com/docs/en/hooks)
- Companion guides: [mcp-setup](mcp-setup.md), [notifications](notifications.md), [cross-harness-agents](../../agent-project/references/cross-harness-agents.md).
