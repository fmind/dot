---
name: agy
description: "CLI sessions, headless Remote Control, completions, and managed setup."
---

# Antigravity (agy)

Operate the CLI and Remote Control; use [antigravity-sdk](../antigravity-sdk/GUIDE.md) for Python orchestration.

## Workflow

1. Check `agy --version`, `agy --help`, and the relevant subcommand help in the intended workspace. Match CLI, desktop, or IDE documentation to the actual surface.
1. Read the relevant [feature guide](references/features.md) link and [changelog](https://antigravity.google/changelog) before relying on settings, models, or availability. Prefer installed help and built-in `antigravity-guide` / `agy-customizations` for version-specific discovery; report disagreements with web docs.
1. Inspect existing settings, `/skills`, `agy plugin list`, and the requested integration before adding configuration. Reuse working discovery paths; do not duplicate the shared catalog or install plugins speculatively. [agent-project](../../../agent-project/SKILL.md) owns discovery; [mcp-setup](../../../mcp-setup/SKILL.md) owns MCP registration.
1. Use session overrides (`--model`, `--effort`, `--mode`) for task-specific choices; leave saved model and cosmetic preferences to the user. Verify results through artifacts, the native panel, or service status; an allow grant alone does not prove a tool works.

## Managed setup

Edit fmind/dot's chezmoi sources, then preview and apply only affected targets with `chezmoi apply --force`. CLI preferences live in `~/.gemini/antigravity-cli/settings.json`; Remote Control uses `~/.gemini/config/config.json` under `userSettings` with a different protobuf JSON schema. Preserve account fields, trust choices, explicit ask/deny grants, and native model state; never patch `antigravity_state.pbtxt`.

The managed baseline enables Vim with insert-first, notifications, non-workspace access, and Always Proceed. Remote grants allow every action without prompts: `read_file(*)`, `write_file(*)`, `command(*)`, `unsandboxed(*)`, `read_url(*)`, `execute_url(*)`, and `mcp(*)`; explicit ask/deny rules still take precedence. Keep native rendering defaults unless a concrete terminal problem calls for an override. Keep hooks small: synchronous hooks add latency to the agent loop.

## Managed custom agents

`reviewer` inspects supplied diffs and source files with file-reading/search tools; `security-reviewer` also runs read-only security scanners with sandboxed command execution. Both inherit the session model, support main-agent and subagent use, exclude default tools, and disable MCP inheritance. Shell access still allows writes within the security reviewer's sandbox; its no-fixes instruction is not a read-only filesystem guarantee.

Select with `agy --agent reviewer`, `agy --agent security-reviewer`, or `/agents`. For delegation, give the parent the role, scope, acceptance criteria, and relevant diff or evidence paths; the reviewer has no shell to obtain Git diffs itself. Use `agy agents` to verify discovery after applying `~/.gemini/config/agents/`; reopen the panel or start a fresh session to pick up changes.

Supagents compiles shared `dot_agents/supagents/` sources into native definitions under `dot_gemini/private_config/agents/`; chezmoi deploys them. Run `mise run agents` after editing a source and `mise run check:agents` to check drift. See [cross-harness agents](../../../agent-project/references/cross-harness-agents.md) for all host mappings and compiler updates. [Custom agents](https://antigravity.google/docs/subagents/) owns the current schema.

## Headless Remote Control

Use the CLI daemon without installing the desktop app. Read [Remote Control](https://antigravity.google/docs/remote-control/) before changing its persistent OS service. `agy remote-control status` is read-only; `start` registers/restarts and `stop` unregisters it. Restart only when no remote task is running; verify the browser project picker separately.

Keep the repository registry local in `~/.gemini/config/projects/`. The [repository index script](../../scripts/index-repositories.py) requires Python 3.12+ and Git:

```bash
python ~/.agents/skills/agy/scripts/index-repositories.py
python ~/.agents/skills/agy/scripts/index-repositories.py --prune --apply
```

Preview first; `--apply` adds missing local GitHub checkouts without network access, and `--prune` also removes entries whose folders are gone or are submodules. It skips hidden/dependency directories (including `modules/`), Git submodules and symlinks, includes the chezmoi source, and accepts explicit roots. New registry files are published atomically without replacing concurrent entries; failed writes leave no partial JSON. Existing metadata is preserved; preview `--prune` before applying it. This registers projects, not semantic code indexes.

## Shell completions

After upgrades, compare native help with the deployed `~/.config/fish/completions/agy.fish` (chezmoi-managed; edit its source, not the deployed copy). Use a native generator if one becomes available; otherwise maintain this completion and its Carapace exclusion. Verify Fish syntax and representative completions, including `agy mic-serve --` and `agy remote-control st`; `dot completion` refreshes configured generators and caches.

## Official Skills

Use the installed built-in harness guides when available. For product-specific packages, consult [Google's catalog](https://github.com/google/skills) and the [vendor-skill policy](../../../agent-project/references/vendor-skills.md); these do not replace harness guidance.

## Top Links

- [CLI overview](https://antigravity.google/docs/cli/overview/) · [Reference](https://antigravity.google/docs/cli/reference/) · [Feature guide](references/features.md)
- Releases: [Antigravity changelog](https://antigravity.google/changelog)
- [Settings](https://antigravity.google/docs/cli/settings/) · [Permissions](https://antigravity.google/docs/cli/permissions/) · [Troubleshooting](https://antigravity.google/docs/cli/troubleshooting/)
