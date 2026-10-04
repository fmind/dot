---
name: agy
description: "CLI sessions, managed settings and auth, custom agents, and completions."
---

# Antigravity (agy)

Operate the CLI; use [antigravity-sdk](../antigravity-sdk/GUIDE.md) for Python orchestration, [remote-control](../remote-control.md) for browser access, [headless-review](../headless-review.md) for structured reviews, and [statusline](../statusline.md) for the managed renderer.

## Workflow

1. Check `agy --version`, `agy --help`, and the relevant subcommand help in the intended workspace. Match CLI, desktop, or IDE documentation to the actual surface.
1. Read the relevant [feature guide](references/features.md) link and [changelog](https://antigravity.google/changelog) before relying on settings, models, or availability. Prefer installed help and built-in `antigravity-guide` / `agy-customizations` for version-specific discovery; report disagreements with web docs.
1. Inspect existing settings, `/skills`, `agy plugin list`, and the requested integration before adding configuration. Reuse working discovery paths; do not duplicate the shared catalog or install plugins speculatively. [agent-project](../../../agent-project/SKILL.md) owns discovery; [mcp-setup](../../../mcp-setup/SKILL.md) owns MCP registration.
1. Use session overrides (`--model`, `--effort`, `--mode`) for task-specific choices; leave saved model and cosmetic preferences to the user. Verify results through artifacts, the native panel, or service status; an allow grant alone does not prove a tool works.

## Managed setup

Edit fmind/dot's chezmoi sources, then preview and apply only affected targets with `chezmoi apply --force`. CLI preferences live in `~/.gemini/antigravity-cli/settings.json`; Remote Control uses `~/.gemini/config/config.json` under `userSettings` with a different protobuf JSON schema. Preserve account fields, trust choices, explicit ask/deny grants, and native model state; never patch `antigravity_state.pbtxt`.

The managed baseline enables Vim with insert-first, notifications, non-workspace access, and Always Proceed. Remote grants allow every action without prompts: `read_file(*)`, `write_file(*)`, `command(*)`, `read_url(*)`, `execute_url(*)`, and `mcp(*)`; explicit ask/deny rules still take precedence. `autoContinueOnMaxGeneratorInvocations` (undocumented, verified in agy 1.2.16) skips the continue prompt after the step budget. `unsandboxed(...)` rules are deprecated on macOS and Linux (current docs keep them for Windows only, and the CLI warns at startup); `command(*)` covers execution inside and outside the sandbox. Keep hooks small: synchronous hooks add latency to the agent loop.

The CLI signs in with the Google account and its plan quota by default; keep it there. Two explicit-only alternatives exist: `"modelProvider": "gemini"` plus an exported `GEMINI_API_KEY` (the only variable read; `.env` files and `GOOGLE_API_KEY` are ignored), or `AGY_ADC_AUTH=true` for ADC against an entitled Google Cloud project. Both bill outside the subscription; never enable either from an ambient key. See [installation and auth](https://antigravity.google/docs/cli/install/) and [enterprise](https://antigravity.google/docs/enterprise/).

Shell completions: after upgrades, compare native help with the deployed `~/.config/fish/completions/agy.fish` (chezmoi-managed; edit its source, not the deployed copy). Use a native generator if one becomes available; otherwise maintain this completion and its Carapace exclusion. Verify Fish syntax and representative completions, including `agy mic-serve --` and `agy remote-control st`; `dot completion` refreshes configured generators and caches.

## Managed custom agents

Shared roles, such as `code-reviewer`, `security-reviewer`, and `solution-architect`, inherit the session model, support main-agent and subagent use, and list exactly `view_file`, `run_command`, `write_to_file`, `replace_file_content`, `read_url_content`, `search_web`, and `finish`. Verified in agy 1.2.16: omitting `tools` leaves a small read, web, and messaging baseline without shell or edit tools, and an explicit list replaces that baseline (agy always adds `send_message` and `manage_task`). Without `finish`, a `--json-schema` run still exits 0 with `SUCCESS` but omits `structured_output`. Search runs through the shell (`rg`, `fd`), so the legacy `list_dir`, `find_by_name`, and `grep_search` tools, retired from agy's default baseline in 1.2.7, are unnecessary. A misspelled tool name can fail or hang the session; the headless `init.tools` list shows the global registry, not a role's effective tools. Markdown agents inherit ambient skills, rules, and subagents unless `excludeDefaultComponents: true`. Their instructions, not the allowlist, bound actions.

Select with `agy --agent <role>` or `/agents`. For delegation, give the parent the role, scope, acceptance criteria, and relevant diff or evidence paths. Use `agy agents` to verify discovery after applying `~/.gemini/config/agents/` (project roles live in `.agents/agents/`); reopen the panel or start a fresh session to pick up changes.

```bash
agy --agent code-reviewer -i 'Review the working-tree diff. Report verified findings without editing.'
```

That selects the main agent. To spawn subagents, ask the default parent explicitly: “Delegate correctness review to code-reviewer and credential/permission review to security-reviewer. Give each the relevant paths and constraints, have both report without editing, then reconcile findings.” Subagents start with fresh context; include requirements and evidence in the assignment. Use `/agents` to inspect them; `Enter` opens details and `K` terminates a selected subagent. To message an existing subagent, type `@` followed by a space and select it from autocomplete; this differs from `@path` file mentions. [Agents panel](https://antigravity.google/docs/cli/commands/agents/) and the [changelog](https://antigravity.google/docs/changelog) own current controls.

Supagents compiles shared `dot_agents/supagents/` sources into native definitions under `dot_gemini/private_config/agents/`; chezmoi deploys them. Run `mise run agents` after editing a source and `mise run check:agents` to check drift. See [cross-harness agents](../../../agent-project/references/cross-harness-agents.md) for all host mappings and compiler updates. [Custom agents](https://antigravity.google/docs/subagents/) owns the current schema.

## Official Skills

Use the installed built-in harness guides when available. For product-specific packages, consult [Google's catalog](https://github.com/google/skills) and the [vendor-skill policy](../../../agent-project/references/vendor-skills.md); these do not replace harness guidance.

## Top Links

- [CLI overview](https://antigravity.google/docs/cli/overview/) · [Reference](https://antigravity.google/docs/cli/reference/) · [Feature guide](references/features.md)
- Releases: [Antigravity changelog](https://antigravity.google/changelog)
- [Settings](https://antigravity.google/docs/cli/settings/) · [Permissions](https://antigravity.google/docs/cli/permissions/) · [Troubleshooting](https://antigravity.google/docs/cli/troubleshooting/)
