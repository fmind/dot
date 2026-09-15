---
name: agy
description: Operate Google Antigravity CLI and remote sessions using current official guidance. Use when configuring agy, resuming conversations, or setting up Remote Control.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/agy
  created: "2026-09-09"
  updated: "2026-09-15"
---

# Antigravity (agy)

Operate the Antigravity harness; use [antigravity-sdk](../antigravity-sdk/SKILL.md) for Python SDK orchestration.

## Workflow

1. Inspect `agy --version` and `agy --help` in the intended workspace; distinguish CLI, desktop, and IDE features.
1. Open the relevant official page below and check the changelog before relying on new flags, settings, models, or availability. If docs and installed help disagree, report the version gap; keep this skill as a link map instead of copying release details.
1. For a session, resolve the project and conversation, then use the documented interactive, headless, or resume interface; use `/model <name> <prompt>` for one-shot consultations without altering the saved default. For Remote Control, read its dedicated page before changing the service; `agy remote-control start|status|stop` registers a persistent OS service and needs authority for that scope.
1. Verify the requested outcome with the native session or service status and resulting artifacts; use [agent-project](../agent-project/SKILL.md) for shared skill discovery and [agent-mcp](../agent-mcp/SKILL.md) for MCP registration.

## Headless Remote Control on the laptop

Use the CLI daemon; installing Antigravity 2.0 desktop is unnecessary. Remote settings live in `~/.gemini/config/config.json` under `userSettings`, separately from `~/.gemini/antigravity-cli/settings.json`. In fmind/dot, edit the chezmoi source modifier and apply that target with `chezmoi apply --force`; preserve the hostname, account fields and explicit permission grants. The managed `read_url(*)`, `execute_url(*)` and `mcp(*)` grants allow web reading, browser interactions and MCP tools; merge them into existing grants without replacing explicit ask or deny rules. The remote schema uses enum names (`CASCADE_COMMANDS_AUTO_EXECUTION_EAGER`, `ARTIFACT_REVIEW_MODE_TURBO`, `AGENT_PERMISSION_PRESET_TURBO`) for Always Proceed, not CLI strings. These fields were checked against agy 1.2.3; verify the installed schema after upgrades.

The remembered remote model lives in `~/.gemini/antigravity-cli/antigravity_state.pbtxt` as `last_selected_agent_model`, not in `userSettings`. The [managed state modifier](../../dot_gemini/antigravity-cli/modify_private_antigravity_state.pbtxt) documents the verified CLI version and model-to-enum mapping. Verify both `agy models` and the installed mapping before updating the modifier after an upgrade; preserve all other native state. Set the machine-local nickname with `agy remote-control start --name <name>`. Existing conversations can retain their own model selection.

Keep repository paths on the laptop in `~/.gemini/config/projects/`, outside versioned dotfiles. Use the [repository index script](scripts/index-repositories.py) with Python 3.12+ and Git:

```bash
python ~/.agents/skills/agy/scripts/index-repositories.py
python ~/.agents/skills/agy/scripts/index-repositories.py --apply
agy remote-control start
agy remote-control status
```

The first command previews counts; `--apply` adds missing local GitHub checkouts without cloning or contacting GitHub. It scans visible directories under home plus the hidden chezmoi source, skips dependencies (including `modules/`) and symlinks, and accepts explicit roots for other hidden locations. It preserves existing projects, grants, names and conversation associations; removed or moved checkouts need a separate reviewed cleanup. Re-run after cloning or moving repositories, then restart the daemon when no remote task is running and verify the project picker in the browser. Registration is metadata discovery, not semantic code indexing. Never commit the generated laptop registry or run a model prompt just to populate it.

## Shell completions

After an agy update, compare `agy --help` and subcommand help with the managed Fish completion in fmind/dot (`dot_config/fish/completions/agy.fish`); agy 1.2.3 has no native generator. Keep agy excluded from Carapace when this completion owns it. Run `dot completion` to refresh all configured generators and shell integration caches, then verify `complete -C "agy remote-control st"` in Fish returns `start`, `status` and `stop`.

## Official Skills

- [CLI plugins and skills](https://antigravity.google/docs/cli/plugins/) and [desktop skills](https://antigravity.google/docs/skills/): select the documentation for the surface in use.
- [Google's skill catalog](https://github.com/google/skills): product-specific skills; check the selected package's scope rather than assuming it teaches the agy harness. Follow the [vendor-skill policy](../agent-project/references/vendor-skills.md) when installation is requested.

## Top Links

For session recovery, automation, and integration decisions, read the [operation links](references/features.md). Use the official documentation index for other capabilities.

- [CLI overview](https://antigravity.google/docs/cli/overview/) · [CLI reference](https://antigravity.google/docs/cli/reference/)
- [Changelog](https://antigravity.google/changelog): choose the relevant product's release notes.
- [Remote Control](https://antigravity.google/docs/remote-control/): desktop access and headless service setup, lifecycle, and troubleshooting.
- [Conversations](https://antigravity.google/docs/cli/conversations/) · [Headless mode](https://antigravity.google/docs/cli/headless/)
- [Settings](https://antigravity.google/docs/cli/settings/) · [Permissions](https://antigravity.google/docs/cli/permissions/) · [Troubleshooting](https://antigravity.google/docs/cli/troubleshooting/)
