---
name: agy
description: "CLI sessions, managed settings and auth, custom agents, and completions."
---

# Antigravity (agy)

Operate the CLI; use [antigravity-sdk](../antigravity-sdk/GUIDE.md) for Python orchestration, [remote-control](../remote-control.md) for browser access, [headless-review](../headless-review.md) for structured reviews, and [statusline](../statusline.md) for the managed renderer.

## Workflow

1. **Verify features before relying on them**: read the relevant [feature guide](references/features.md) link, `agy --help` / `agy models`, `agy changelog` (bundled CLI release notes; can lag several releases), and `https://antigravity.google/docs/changelog.md` (append `.md` to any Antigravity docs URL for clean Markdown; the web changelog covers App, CLI, IDE, and SDK). Prefer installed help and built-in `antigravity-guide` / `agy-customizations` for version-specific discovery; report disagreements with web docs.
1. **Inspect before adding configuration**: existing settings, `/skills`, `agy plugin list --json`, and the requested integration. Reuse working discovery paths; do not duplicate the shared catalog or install plugins speculatively. [agent-project](../../../agent-project/SKILL.md) owns discovery; [mcp-setup](../../../mcp-setup/SKILL.md) owns MCP registration.
1. **Override per session; verify results**: use session overrides (`--model`, `--effort`, `--mode`) for task-specific choices; leave saved model and cosmetic preferences to the user. Verify results through artifacts, the native panel, or service status; an allow grant alone does not prove a tool works.

## Managed setup

Edit fmind/dot's chezmoi sources, then preview and apply only affected targets with `chezmoi apply --force`. CLI preferences live in `~/.gemini/antigravity-cli/settings.json`; Remote Control uses `~/.gemini/config/config.json` under `userSettings` with a different protobuf JSON schema. Preserve account fields, trust choices, explicit ask/deny grants, and native model state; never patch `antigravity_state.pbtxt`.

The managed baseline enables Vim with insert-first, immediate queued-message delivery, high verbosity, notifications, non-workspace access, and Always Proceed. Remote grants allow every action without prompts: `read_file(*)`, `write_file(*)`, `command(*)`, `read_url(*)`, `execute_url(*)`, and `mcp(*)`; explicit ask/deny rules still take precedence. `autoContinueOnMaxGeneratorInvocations` (undocumented, verified in agy 1.4.7) skips the continue prompt after the step budget. `unsandboxed(...)` rules are deprecated on macOS and Linux (current docs keep them for Windows only, and the CLI warns at startup); `command(*)` covers execution inside and outside the sandbox.

Agent commands run as separate `bash -c` calls that read no shell startup files and inherit agy's launch environment. Launches therefore go through the `agy` fish function (`~/.config/fish/functions/agy.fish`; Zellij's `Alt a` and the Remote Control daemon drop-in run it through `fish -c`, which `exec`s the binary when non-interactive): it puts the mise shims first on `PATH`, so each command resolves the current project's tool pins instead of the launch directory's, and sets `GH_PROMPT_DISABLED=1` and `CLOUDSDK_CORE_DISABLE_PROMPTS=1`. Restart long-lived agy sessions after environment changes.

Managed hooks live in `~/.gemini/config/hooks.json` as named hooks: `notify` runs `dot agent hook notify agy stop` on `Stop`, which stays quiet for subagents, unfinished background work, and print-mode runs (dot reads the nearest agy ancestor's `-p`/`--print`/`--prompt` argument); `brain-context` runs `~/fmind/brain/settings/hooks/agy-context.py` on `SessionStart` when the brain is checked out. Inject per-conversation context on `SessionStart` as a `systemMessage`: `PreInvocation` re-runs before every model call (its `invocationNum` restarts with each turn and agent loop), and an `ephemeralMessage` is dropped after its turn. Every hook blocks the agent loop until it exits.

The CLI signs in with the Google account and its plan quota by default; keep it there. Two explicit-only alternatives exist: `"modelProvider": "gemini"` plus an exported `GEMINI_API_KEY` (the only variable read; `.env` files and `GOOGLE_API_KEY` are ignored), or `AGY_ADC_AUTH=true` for ADC against an entitled Google Cloud project (models the project cannot access are hidden). Both bill outside the subscription; never enable either from an ambient key. See [installation and auth](https://antigravity.google/docs/cli/install/) and [enterprise](https://antigravity.google/docs/enterprise/).

Shell completions: after upgrades, compare native help with the deployed `~/.config/fish/completions/agy.fish` (chezmoi-managed; edit its source, not the deployed copy). Use a native generator if one becomes available; otherwise maintain this completion. Verify Fish syntax and representative completions, including `agy mic-serve --` and `agy remote-control st`; `mise run completions` regenerates the other configured completions.

## Custom agents

fmind/dot deploys no custom roles; the default agent loads the shared persona and skills and can invoke built-in `self`, `research`, and `image-generator` subagents. Before adding a role, read [cross-harness agents](../../../agent-project/references/cross-harness-agents.md): an agy role needs an explicit tool allowlist to act (agy always adds `send_message` and `manage_task`). Markdown agents inherit ambient skills, rules, and subagents unless `excludeDefaultComponents: true`, and relative `skills:`, `plugins:`, `rules:`, `agents:`, and `hooks:` paths resolve against the agent's own directory. The headless `init.tools` list shows the global registry, not a role's effective tools.

To spawn subagents, ask the default parent explicitly, for example: "Delegate a correctness review and a credential/permission review to two subagents. Give each the relevant paths and constraints, have both report without editing, then reconcile findings." Subagents start with fresh context; include requirements and evidence in the assignment. Use `/agents` to inspect them; `Enter` opens details, `Ctrl+K` or `a` answers a pending subagent question, and `K` terminates a selected subagent. To message an existing subagent, type `@` followed by a space and select it from autocomplete; this differs from `@path` file mentions. [Agents panel](https://antigravity.google/docs/cli/commands/agents/), [custom agents](https://antigravity.google/docs/subagents/), and the [changelog](https://antigravity.google/docs/changelog) own current controls.

## Official Skills

Use the installed built-in harness guides when available. For product-specific packages, consult [Google's catalog](https://github.com/google/skills) and the [vendor-skill policy](../../../agent-project/references/vendor-skills.md); these do not replace harness guidance.

## Top Links

- [CLI overview](https://antigravity.google/docs/cli/overview/) · [Reference](https://antigravity.google/docs/cli/reference/) · [Feature guide](references/features.md)
- Releases: `agy changelog` · [Antigravity changelog](https://antigravity.google/docs/changelog)
- [Settings](https://antigravity.google/docs/settings?tab=cli) · [Permissions](https://antigravity.google/docs/cli/permissions/) · [Troubleshooting](https://antigravity.google/docs/cli/troubleshooting/)
