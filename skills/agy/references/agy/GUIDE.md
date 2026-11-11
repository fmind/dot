---
name: agy
description: "CLI sessions, managed settings and auth, custom agents, and completions."
---

# Antigravity (agy)

Operate the CLI; route Python orchestration to [antigravity-sdk](../antigravity-sdk/GUIDE.md), browser tunnels to [remote-control](../remote-control.md), JSON-schema reviews to [headless-review](../headless-review.md), and prompt chrome to [statusline](../statusline.md).

## Workflow

1. **Check live references first**: inspect `agy --help`, `agy changelog`, and the built-in `antigravity-guide` skill, then docs (append `.md` before any `?tab=`), reporting discrepancies; [features.md](references/features.md) records workstation policy.
1. **Inspect before configuring**: check current settings, `/skills`, and `agy plugin list --json` before adding anything; [agent-project](../../../agent-project/SKILL.md) owns discovery and [mcp-setup](../../../agent-harnesses/references/mcp-setup.md) owns MCP registration.
1. **Use session flags and verify outcomes**: pass ephemeral `--model`, `--effort`, `--mode`, or `--settings '<json>'` instead of rewriting user preferences, and verify via artifacts, native panels, or service status rather than allow grants.

## Managed setup

Edit `fmind/dot` chezmoi sources and apply affected targets with `chezmoi apply --force`. CLI settings live in `~/.gemini/antigravity-cli/settings.json`; Remote Control uses `~/.gemini/config/config.json` (`userSettings`, separate protobuf JSON). Preserve account, trust, ask/deny, and model state; never edit `antigravity_state.pbtxt`.

Managed defaults enable insert-first Vim, immediate queued messages, high verbosity, non-workspace access, Always Proceed, and full remote grants (`read_file(*)`, `write_file(*)`, `command(*)`, `read_url(*)`, `execute_url(*)`, `mcp(*)`; ask/deny rules still win). `autoContinueOnMaxGeneratorInvocations` (verified 1.4.7–1.5.5) skips step-budget prompts; `unsandboxed(...)` applies only to business/enterprise accounts (`command(*)` covers inside and outside the sandbox).

Because `agy` runs commands via `bash -c` without shell init files, `~/.config/fish/functions/agy.fish` (also invoked via `fish -c` by Zellij `Alt a` and the Remote Control daemon drop-in) prepends mise shims on `PATH` and sets `GH_PROMPT_DISABLED=1` and `CLOUDSDK_CORE_DISABLE_PROMPTS=1`; restart long sessions after env changes.

Named hooks in `~/.gemini/config/hooks.json` (`notify` on `Stop`, `brain-context` on `SessionStart`; see [notifications](../../../agent-harnesses/references/notifications.md)) block the loop until exit. Inject conversation context on `SessionStart` as a `systemMessage`—`PreInvocation` fires before every model call (`invocationNum` resets per turn/loop) and `ephemeralMessage` expires after one turn.

Keep default Google-subscription sign-in (select Gemini subscription, not Pay As You Go, when prompted since 1.4.11). Never auto-enable `"modelProvider": "gemini"` + exported `GEMINI_API_KEY` (`.env` and `GOOGLE_API_KEY` are ignored) or `AGY_ADC_AUTH=true` (hides unentitled Cloud models); both bill outside the subscription ([auth](https://antigravity.google/docs/install/), [enterprise](https://antigravity.google/docs/enterprise/)).

After upgrades, sync chezmoi's `~/.config/fish/completions/agy.fish` against `--help` (or a native generator if added) and test `agy mic-serve --` and `agy remote-control st`; `mise run completions` updates other tools.

## Custom agents

`fmind/dot` defines no custom roles; the default agent uses shared skills and built-in subagents (`self`, `research`, `image-generator`, `browser`, `pro` on Gemini 4 Argon, `flash` on Gemini 3.8 Flash; check `/agents`). Per [cross-harness agents](../../../agent-project/references/cross-harness-agents.md), custom roles need an explicit tool allowlist (agy auto-adds `send_message` and `manage_task`); Markdown roles inherit ambient skills/rules/subagents unless `excludeDefaultComponents: true`, resolve relative `skills:`/`plugins:`/`rules:`/`agents:`/`hooks:` paths from the agent directory, and are not reflected in headless `init.tools` (which lists the global registry). See [agents panel](https://antigravity.google/docs/cli/commands/agents/) and [custom agents](https://antigravity.google/docs/subagents/).

## Top Links

- [CLI settings and tips](https://antigravity.google/docs/cli/using/) · [Reference](https://antigravity.google/docs/cli/reference/) · [Feature guide](references/features.md)
- Releases: `agy changelog` · [Antigravity changelog](https://antigravity.google/docs/changelog)
- [Settings](https://antigravity.google/docs/settings?tab=cli) · [Permissions](https://antigravity.google/docs/permissions?tab=cli) · [Troubleshooting](https://antigravity.google/docs/cli/troubleshooting/)
