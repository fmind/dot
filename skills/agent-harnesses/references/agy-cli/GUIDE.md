---
name: agy-cli
description: "Operate agy CLI sessions, managed settings, auth, hooks, and custom agents."
---

# Antigravity (`agy`)

Operate the CLI; route SDK runs to [antigravity-sdk](../antigravity-sdk/GUIDE.md), tunnels to [remote-control](../remote-control.md), JSON-schema reviews to [headless-review](../headless-review/GUIDE.md), and prompt chrome to [statusline](../statusline.md).

## Workflow

1. **Check live refs**: `agy --help`, `agy changelog`, [settings schema](https://antigravity.google/schemas/v1/settings.json) (may trail `showThinking`/`orchestrator`/`voice`); [features.md](references/features.md) owns model/feature policy.
1. **Inspect first**: check settings, `/skills`, `agy plugin list --json`; [project-setup](../project-setup.md) owns discovery, [mcp-setup](../mcp-setup.md) owns MCP.
1. **Ephemeral flags**: use `--model`, `--effort`, `--mode`, `--add-dir`, `-i`, `--settings '<json>'|<file>` over prefs; verify via artifacts or status.

## Managed setup

Edit `fmind/dot` sources and run `chezmoi apply --force` (never edit `antigravity_state.pbtxt`).

- **Settings & keys**: `~/.gemini/antigravity-cli/settings.json` (sparse; ignores `hooks`/`enableTelemetry`), `keybindings.json` (Zellij-safe `Alt+E`/`Alt+Q`/`Alt+W`), and `~/.gemini/config/config.json` (`userSettings`, Remote Control) preserve account, trust, ask/deny, and model state.
- **Defaults & denies**: insert-first Vim, `send-immediately`, `"grouped"` picker, `"medium"` verbosity, `/voice`, Always Proceed, non-workspace access, remote wildcards (ask/deny win), and strips legacy `autoContinueOnMaxGeneratorInvocations` so long loops pause before hitting 500k context. `unsandboxed(...)` is business/enterprise-only. Secret denies use `read_file(<abs>|<root-rel>)` (exact paths/dirs and workspace-root filenames; no wildcards—see [cross-harness-agents](../cross-harness-agents.md#permission-limits); blocks `write_file` too).
- **Shell env**: `agy` runs `bash -c` without init; `agy.fish` prepends mise shims, strips `mise/installs/*` and hook state, sets `GIT_TERMINAL_PROMPT=0`, `GH_PROMPT_DISABLED=1`, `CLOUDSDK_CORE_DISABLE_PROMPTS=1`. Restart after env edits; set `AGY_CLI_DISABLE_AUTO_UPDATE=true` or remove `~/.gemini/antigravity-cli/updater/update.lock` if updates stall.
- **Hooks**: `~/.gemini/config/hooks.json` and `.agents/hooks.json` (`/hooks`) block until exit and fail open ([notifications](../notifications.md)). `PreToolUse`/`PostToolUse` wrap `{matcher, hooks}` (`overwrite` on `PreToolUse`); other hooks take flat arrays (`systemMessage`; `Stop` gets `continuation_active`).
- **Auth & plugins**: keep subscription sign-in ([auth](https://antigravity.google/docs/install/)). Avoid `"modelProvider": "gemini"` + `GEMINI_API_KEY` (`GOOGLE_GEMINI_BASE_URL` overrides) and `AGY_ADC_AUTH=true` (bills GCP). Run `agy plugin validate [--strict] [--json]`; MCP `variables` need `/plugin` setup; plugin hooks run in `<plugin-root>`.

## Custom agents

- **Discovery**: `fmind/dot` compiles `fmind-review-*` into `~/.gemini/config/agents/` ([subagent](../../../subagent/SKILL.md)). `agy agent` lists **global roles only**—check `.agents/agents/` via `/agents` or `agy --agent <role>`.
- **Built-ins & limits**: `self`, `research`, `image-generator`, `/browser`, user-only `/swarm` (`@<name> <msg>`). Custom roles need explicit tool allowlists (`send_message`/`manage_task` auto-added), resolve relative paths from agent dir, and omit headless `init.tools` ([cross-harness-agents](../cross-harness-agents.md)).

## Top Links

- [CLI reference](https://antigravity.google/docs/cli/reference/) · [Features](references/features.md) · [Changelog](https://antigravity.google/docs/changelog) · [Settings](https://antigravity.google/docs/settings?tab=cli) · [Permissions](https://antigravity.google/docs/permissions?tab=cli) · [Subagents](https://antigravity.google/docs/subagents/)
