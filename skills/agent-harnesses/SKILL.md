---
name: agent-harnesses
description: "Operate and configure Claude Code, Copilot, OpenCode, and Pi."
license: MIT
metadata:
  kind: collection
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/agent-harnesses
  created: "2026-09-16"
  updated: "2026-11-10"
---

# Agent Harnesses

Operate the selected coding-agent host without conflating its configuration, permissions, or lifecycle with another host. Antigravity has its own [agy](../agy/SKILL.md) owner. Claude Code has no guide here: use its built-in help and the [docs index](https://code.claude.com/docs/llms.txt).

## Workflow

1. **Check the version-specific reference before declaring a feature unavailable**: installed help can omit supported flags.
1. **Resolve precedence and permission scope before changing execution behavior**: hooks and extensions execute code.
1. **Verify** the result and the host's own instruction or skill discovery. Use [agent-project](../agent-project/SKILL.md) for shared instruction layout and [mcp-setup](../mcp-setup/SKILL.md) for MCP registration.

## Task guides

<!-- guides:start -->

- [copilot](references/copilot/GUIDE.md): Copilot sessions and extensions.
- [notifications](references/notifications.md): Diagnose or change managed turn notifications, brain session-context hooks, and their wiring per host.
- [opencode](references/opencode/GUIDE.md): OpenCode sessions and provider configuration.
- [pi](references/pi.md): Pi sessions, providers, project trust, extensions, and headless runs.

<!-- guides:end -->

## Gotchas

- **Edit managed host keys in fmind/dot**: on this workstation, Claude, Copilot, OpenCode, and Pi settings are merged from `modify_*` chezmoi templates in `~/.local/share/chezmoi`. A direct edit to a managed key (including through `/config` or a host's settings skill) reverts on `chezmoi apply --force`; unmanaged keys survive. Change the source, preview with `mise run diff` (it excludes encrypted targets), then apply.
- **Install vendor skills through the policy**: the Copilot and OpenCode guides name each host's sources, and Pi packages and extensions are code that runs in-process; install a requested package only through the [vendor-skill policy](../agent-project/references/vendor-skills.md) and retain the existing package manager's ownership.
