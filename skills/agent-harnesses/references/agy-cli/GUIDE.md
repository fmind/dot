---
name: agy-cli
description: CLI sessions, managed settings, auth, custom agents, and completions.
---

# Antigravity (agy)

Operate the CLI; route Python orchestration to [antigravity-sdk](../antigravity-sdk/GUIDE.md), browser tunnels to [remote-control](../remote-control.md), JSON-schema reviews to [headless-review](../headless-review/GUIDE.md), and prompt chrome to [statusline](../statusline.md).

## Workflow

1. **Check live references**: inspect `agy --help`, `agy changelog`, and `antigravity-guide`, then docs (append `.md` before `?tab=`), reporting drift; [features.md](references/features.md) owns model/feature policy (`Orchestrator`, `Neon`, `Hydrogen`, ACP, credits, sandboxes).
1. **Inspect before configuring**: check settings, `/skills`, and `agy plugin list --json` first; [project-setup](../project-setup.md) owns discovery and [mcp-setup](../mcp-setup.md) owns MCP registration.
1. **Use ephemeral flags and verify**: pass `--model`, `--effort`, `--mode`, or `--settings '<json>'` instead of editing user prefs, and verify via artifacts, panels, or service status.

## Managed setup

Edit `fmind/dot` sources and run `chezmoi apply --force`. CLI settings use `~/.gemini/antigravity-cli/settings.json` (sparse persistence strips default-valued keys at startup), managed Zellij-safe shortcuts (`Alt+E` editor, `Alt+Q` alternate submit, `Alt+W` jump to waiting subagent, preserving stock fallbacks) merge into `~/.gemini/antigravity-cli/keybindings.json` (`/keybindings`), and Remote Control uses `~/.gemini/config/config.json` (`userSettings`, protobuf JSON). Preserve account, trust, ask/deny, and model state; never edit `antigravity_state.pbtxt`.

- **Defaults**: insert-first Vim, `send-immediately` queued messages (`1.5.13+` joins the current turn after the active step), `"medium"` verbosity (`1.5.14+` keeps colorized headers and `│` gutter when expanded), dictation default for `/voice`, non-workspace access, Always Proceed, no tips/surveys, remote wildcards (ask/deny win), and `autoContinueOnMaxGeneratorInvocations` for step prompts. `unsandboxed(...)` is business/enterprise-only (`command(*)` covers inside/outside sandbox).
- **Secret denies**: `read_file(<abs>)` and `read_file(<glob>)` from [cross-harness agents](../cross-harness-agents.md#permission-limits) in `permissions.deny` and `globalPermissionGrants.deny`.
- **Shell env**: `agy` runs `bash -c` without shell init, so `~/.config/fish/functions/agy.fish` (Zellij `Alt a`, Linux daemon) prepends mise shims on `PATH`, clears mise hook state, and sets `GIT_TERMINAL_PROMPT=0`, `GH_PROMPT_DISABLED=1`, and `CLOUDSDK_CORE_DISABLE_PROMPTS=1`. Restart sessions after env changes.
- **Hooks**: global `~/.gemini/config/hooks.json` (host-managed, not in `fmind/dot`) and workspace `.agents/hooks.json` (`/hooks` lists active hooks; `1.5.14+` kills full process groups on timeout/cancel) block until exit, hosting optional `brain-context` on `SessionStart` ([notifications](../notifications.md)). Inject `SessionStart` context via `systemMessage`; `PreInvocation` fires per model call (`invocationNum` resets per turn/loop) and `ephemeralMessage` lasts one turn.
- **Auth**: keep Google-subscription sign-in because alternatives like Pay As You Go bill outside it ([auth](https://antigravity.google/docs/install/), [enterprise](https://antigravity.google/docs/enterprise/)). Never set `"modelProvider": "gemini"` + `GEMINI_API_KEY` (`.env`/`GOOGLE_API_KEY` ignored; Remote Control, `--remote-agent`, `/usage|/quota|/credits` exit 2, and `/voice|/record` disable; `1.5.8`–`1.5.12` add Hydrogen/Carbon/Neon). Avoid `AGY_ADC_AUTH=true`: it exposes `Gemini 4 Neon`, `Hydrogen`, `Carbon`, and `Orchestrator` via ADC/gateways while hiding unentitled Cloud models.
- **Plugins**: `agy plugin validate` checks local dirs, `.zip`, `https://`, GitHub repo/subdir URLs, and `marketplace.json` (`1.5.11+`; `$schema` Agent Plugins manifest fix in `1.5.14+`). Run `mise run completions` for tools with native Fish generators.

## Custom agents

`fmind/dot` compiles `fmind-review-*` reviewers from `dot_agents/supagents/` into `~/.gemini/config/agents/` via `supagents` ([subagent](../../../subagent/SKILL.md)). Built-ins cover `self`, `research`, `image-generator` (`Model="inherit"|"flash_lite"|"flash"|"pro"`), `/browser`, and user-only `/swarm` (`1.5.13+`); inspect via `agy agent` or `/agents`. Per [cross-harness agents](../cross-harness-agents.md), custom roles need an explicit tool allowlist (`send_message`/`manage_task` auto-added), inherit ambient components unless `excludeDefaultComponents: true`, resolve relative paths from the agent dir, and stay absent from headless `init.tools` ([agents panel](https://antigravity.google/docs/cli/commands/agents/), [custom agents](https://antigravity.google/docs/subagents/)).

## Top Links

- [CLI settings and tips](https://antigravity.google/docs/cli/using/) · [Reference](https://antigravity.google/docs/cli/reference/) · [Feature guide](references/features.md)
- Releases: `agy changelog` · [Antigravity changelog](https://antigravity.google/docs/changelog)
- [Settings](https://antigravity.google/docs/settings?tab=cli) · [Permissions](https://antigravity.google/docs/permissions?tab=cli) · [Troubleshooting](https://antigravity.google/docs/cli/troubleshooting/)
