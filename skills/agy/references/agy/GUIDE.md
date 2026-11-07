---
name: agy
description: "CLI sessions, managed settings and auth, custom agents, and completions."
---

# Antigravity (agy)

Operate the CLI; use [antigravity-sdk](../antigravity-sdk/GUIDE.md) for Python orchestration, [remote-control](../remote-control.md) for browser access, [headless-review](../headless-review.md) for structured reviews, and [statusline](../statusline.md) for the managed renderer.

## Workflow

1. **Verify features before relying on them**: check `agy --help`, `agy changelog`, and the built-in `antigravity-guide` skill first, then the docs (append `.md` to a docs path, before any `?tab=`, for clean Markdown); report disagreements. The [feature guide](references/features.md) holds the owner's choices.
1. **Inspect before adding configuration**: existing settings, `/skills`, `agy plugin list --json`, and the requested integration. Reuse working discovery paths; do not duplicate the shared catalog or install plugins speculatively. [agent-project](../../../agent-project/SKILL.md) owns discovery; [mcp-setup](../../../mcp-setup/SKILL.md) owns MCP registration.
1. **Override per session; verify results**: use session overrides (`--model`, `--effort`, `--mode`, or `--settings '<json>'` for any `settings.json` key, never saved) for task-specific choices; leave saved model and cosmetic preferences to the user. Verify results through artifacts, the native panel, or service status; an allow grant alone does not prove a tool works.

## Managed setup

Edit fmind/dot's chezmoi sources, then preview and apply only affected targets with `chezmoi apply --force`. CLI preferences live in `~/.gemini/antigravity-cli/settings.json`; Remote Control uses `~/.gemini/config/config.json` under `userSettings` with a different protobuf JSON schema. Preserve account fields, trust choices, explicit ask/deny grants, and native model state; never patch `antigravity_state.pbtxt`.

The managed baseline enables Vim with insert-first, immediate queued-message delivery, high verbosity, non-workspace access, and Always Proceed. Remote grants allow every action without prompts: `read_file(*)`, `write_file(*)`, `command(*)`, `read_url(*)`, `execute_url(*)`, and `mcp(*)`; explicit ask/deny rules still take precedence. `autoContinueOnMaxGeneratorInvocations` (undocumented; behavior verified in agy 1.4.7, key still present in the 1.5.2 binary) skips the continue prompt after the step budget. `unsandboxed(...)` rules apply only to business and enterprise accounts; other accounts ignore them with a startup warning, and `command(*)` covers execution inside and outside the sandbox.

Agent commands run as separate `bash -c` calls that read no shell startup files and inherit agy's launch environment. Launches therefore go through the `agy` fish function (`~/.config/fish/functions/agy.fish`; Zellij's `Alt a` and the Remote Control daemon drop-in run it through `fish -c`, which `exec`s the binary when non-interactive): it puts the mise shims first on `PATH`, so each command resolves the current project's tool pins instead of the launch directory's, and sets `GH_PROMPT_DISABLED=1` and `CLOUDSDK_CORE_DISABLE_PROMPTS=1`. Restart long-lived agy sessions after environment changes.

Managed hooks live in `~/.gemini/config/hooks.json` as named hooks: `notify` runs `dot agent hook notify agy stop` on `Stop`, which stays quiet for subagents, unfinished background work, and print-mode runs (dot reads the nearest agy ancestor's `-p`/`--print`/`--prompt` argument), and is the only turn alert: agy's native `notifications` stay off because its OSC 9 alert doubled the hook in Ghostty and never shows in ttyd; `brain-context` runs `~/fmind/brain/settings/hooks/agy-context.py` on `SessionStart` when the brain is checked out. Inject per-conversation context on `SessionStart` as a `systemMessage`: `PreInvocation` re-runs before every model call (its `invocationNum` restarts with each turn and agent loop), and an `ephemeralMessage` is dropped after its turn. Every hook blocks the agent loop until it exits.

The CLI signs in with the Google account and its plan quota by default; keep it there. Two explicit-only alternatives exist: `"modelProvider": "gemini"` plus an exported `GEMINI_API_KEY` (the only variable read; `.env` files and `GOOGLE_API_KEY` are ignored), or `AGY_ADC_AUTH=true` for ADC against an entitled Google Cloud project (models the project cannot access are hidden). Both bill outside the subscription; never enable either from an ambient key. When a Google Cloud sign-in offers a billing model (since 1.4.11), choose the Gemini subscription, not Pay As You Go. See [authentication](https://antigravity.google/docs/install/) and [enterprise](https://antigravity.google/docs/enterprise/).

Shell completions: after upgrades, compare native help with the deployed `~/.config/fish/completions/agy.fish` (chezmoi-managed; edit its source, not the deployed copy). Use a native generator if one becomes available; otherwise maintain this completion. Verify Fish syntax and representative completions, including `agy mic-serve --` and `agy remote-control st`; `mise run completions` regenerates the other configured completions.

## Custom agents

fmind/dot deploys no custom roles; the default agent loads the shared persona and skills and can invoke built-in subagents such as `self`, `research`, `image-generator`, `browser`, `pro` (Gemini 4 Argon), and `flash` (Gemini 3.8 Flash); check `/agents` for the installed list. Before adding a role, read [cross-harness agents](../../../agent-project/references/cross-harness-agents.md): an agy role needs an explicit tool allowlist to act (agy always adds `send_message` and `manage_task`). Markdown agents inherit ambient skills, rules, and subagents unless `excludeDefaultComponents: true`, and relative `skills:`, `plugins:`, `rules:`, `agents:`, and `hooks:` paths resolve against the agent's own directory. The headless `init.tools` list shows the global registry, not a role's effective tools.

See [agents panel](https://antigravity.google/docs/cli/commands/agents/) and [custom agents](https://antigravity.google/docs/subagents/) for current controls.

## Top Links

- [CLI settings and tips](https://antigravity.google/docs/cli/using/) · [Reference](https://antigravity.google/docs/cli/reference/) · [Feature guide](references/features.md)
- Releases: `agy changelog` · [Antigravity changelog](https://antigravity.google/docs/changelog)
- [Settings](https://antigravity.google/docs/settings?tab=cli) · [Permissions](https://antigravity.google/docs/permissions?tab=cli) · [Troubleshooting](https://antigravity.google/docs/cli/troubleshooting/)
