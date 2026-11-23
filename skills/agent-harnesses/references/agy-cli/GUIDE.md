---
name: agy-cli
description: CLI sessions, managed settings, auth, and custom agents.
---

# Antigravity (agy)

Operate the CLI; route Python orchestration to [antigravity-sdk](../antigravity-sdk/GUIDE.md), browser tunnels to [remote-control](../remote-control.md), JSON-schema reviews to [headless-review](../headless-review/GUIDE.md), and prompt chrome to [statusline](../statusline.md).

## Workflow

1. **Check live references**: inspect `agy --help`, `agy changelog`, `antigravity-guide`, and [settings schema](https://antigravity.google/schemas/v1/settings.json) (may trail new keys: `showThinking`, `orchestrator`, `voice`), then docs (`.md` before `?tab=`); [features.md](references/features.md) owns model/feature policy.
1. **Inspect before configuring**: check settings, `/skills`, and `agy plugin list --json` first; [project-setup](../project-setup.md) owns discovery and [mcp-setup](../mcp-setup.md) owns MCP registration.
1. **Use ephemeral flags and verify**: pass `--model`, `--effort`, `--mode`, `--add-dir` (repeatable), `-i`, or `--settings '<json>'|<file>` instead of editing user prefs, and verify via artifacts, panels, or service status.

## Managed setup

Edit `fmind/dot` sources and run `chezmoi apply --force`. CLI settings (`~/.gemini/antigravity-cli/settings.json`; sparse persistence strips defaults, keeps unknown keys, ignores `hooks`/`enableTelemetry`), Zellij-safe keybindings (`~/.gemini/antigravity-cli/keybindings.json`, `/keybindings`: `Alt+E` editor, `Alt+Q` alternate submit, `Alt+W` waiting subagent, with stock fallbacks), and Remote Control (`~/.gemini/config/config.json` `userSettings`, protobuf JSON) preserve account, trust, ask/deny, and model state. Never edit `antigravity_state.pbtxt`.

- **Defaults**: insert-first Vim, `send-immediately` queued messages (`1.5.13+` joins active turn after current step), `"grouped"` picker and `"medium"` verbosity defaults (`1.5.14+` colored headers + `│` gutter), `/voice` dictation, non-workspace access, Always Proceed, no tips/surveys, remote wildcards (ask/deny win), and `autoContinueOnMaxGeneratorInvocations`. `unsandboxed(...)` is business/enterprise-only (`command(*)` covers inside/outside sandbox).
- **Secret denies**: `read_file(<abs>|<glob>)` from [cross-harness agents](../cross-harness-agents.md#permission-limits) in `permissions.deny` and `globalPermissionGrants.deny` (denying `read_file` also denies `write_file`).
- **Shell env**: `agy` runs `bash -c` without shell init; `~/.config/fish/functions/agy.fish` (Zellij `Alt a`, Linux daemon) prepends mise shims, strips `mise/installs/*` and hook state, and sets `GIT_TERMINAL_PROMPT=0`, `GH_PROMPT_DISABLED=1`, `CLOUDSDK_CORE_DISABLE_PROMPTS=1`. Restart after env changes; set `AGY_CLI_DISABLE_AUTO_UPDATE=true` or remove `~/.gemini/antigravity-cli/updater/update.lock` if updates stall.
- **Hooks**: `~/.gemini/config/hooks.json` (host-managed) and `.agents/hooks.json` (`/hooks`; `1.5.14+` kills process groups on timeout/cancel) block until exit and fail open on non-zero exit (`brain-context` on `SessionStart`; [notifications](../notifications.md)). `PreToolUse`/`PostToolUse` wrap `{matcher, hooks}` (`PreToolUse` supports `overwrite` shallow arg merge); `SessionStart`/`PreInvocation`/`PostInvocation`/`Stop` take flat arrays. Use `systemMessage` (`ephemeralMessage` is deprecated); `Stop` receives `continuation_active` (`1.5.6+`).
- **Auth**: keep Google-subscription sign-in; Pay As You Go bills outside it ([auth](https://antigravity.google/docs/install/), [enterprise](https://antigravity.google/docs/enterprise/)). Avoid `"modelProvider": "gemini"` + `GEMINI_API_KEY` (`.env`/`GOOGLE_API_KEY` ignored; fails if unset; `GOOGLE_GEMINI_BASE_URL` overrides endpoint; disables subscription/remote/voice features per [features.md](references/features.md)) and `AGY_ADC_AUTH=true` (`GOOGLE_CLOUD_QUOTA_PROJECT`/`LOCATION`; `1.5.6+` PAYG ADC gets `Auto`, Enterprise stays admin-controlled; bills GCP, hides unentitled models).
- **Plugins**: `agy plugin validate [--strict] [--json]` checks dirs, `.zip`, `https://`, GitHub repo/subdir URLs, and `marketplace.json` (`1.5.14+` `$schema` fix). Plugins with MCP `variables` install disabled until configured in `/plugin`; plugin hooks run in `<plugin-root>` (use relative paths, not `${PLUGIN_ROOT}`).

## Custom agents

`fmind/dot` compiles `fmind-review-*` from `dot_agents/supagents/` to `~/.gemini/config/agents/` via `supagents` ([subagent](../../../subagent/SKILL.md)). Built-ins: `self`, `research`, `image-generator` (`Model="inherit"|"flash_lite"|"flash"|"pro"`), `/browser`, user-only `/swarm` (`1.5.13+`); inspect via `agy agent` or `/agents` (switching mid-session forks; message via `@<name> <msg>`). Per [cross-harness agents](../cross-harness-agents.md), custom roles need an explicit tool allowlist (`send_message`/`manage_task` auto-added), resolve relative paths from the agent dir, and stay absent from headless `init.tools` ([agents panel](https://antigravity.google/docs/cli/commands/agents/), [custom agents](https://antigravity.google/docs/subagents/)).

## Top Links

- [CLI settings and tips](https://antigravity.google/docs/cli/using/) · [Reference](https://antigravity.google/docs/cli/reference/) · [Feature guide](references/features.md)
- Releases: `agy changelog` · [Antigravity changelog](https://antigravity.google/docs/changelog)
- [Settings](https://antigravity.google/docs/settings?tab=cli) · [Permissions](https://antigravity.google/docs/permissions?tab=cli) · [Troubleshooting](https://antigravity.google/docs/cli/troubleshooting/)
