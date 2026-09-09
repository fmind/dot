---
name: agy
description: Operate Google Antigravity CLI and remote sessions using current official guidance. Use when configuring agy, resuming conversations, or setting up Remote Control.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/agy
  created: "2026-09-09"
  updated: "2026-09-09"
---

# Antigravity (agy)

Operate the Antigravity harness; use [antigravity-sdk](../antigravity-sdk/SKILL.md) for Python SDK orchestration.

## Workflow

1. Inspect `agy --version` and `agy --help` in the intended workspace; distinguish CLI, desktop, and IDE features.
1. Open the relevant official page below and check the changelog before relying on new flags, settings, models, or availability. If docs and installed help disagree, report the version gap; keep this skill as a link map instead of copying release details.
1. For a session, resolve the project and conversation, then use the documented interactive, headless, or resume interface. For Remote Control, read its dedicated page before changing the service; starting it registers a persistent OS service and needs authority for that scope.
1. Verify the requested outcome with the native session or service status and resulting artifacts; use [agent-project](../agent-project/SKILL.md) for shared skill discovery and [agent-mcp](../agent-mcp/SKILL.md) for MCP registration.

## Official Skills

- [CLI plugins and skills](https://antigravity.google/docs/cli/plugins/) and [desktop skills](https://antigravity.google/docs/skills/): select the documentation for the surface in use.
- [Google's skill catalog](https://github.com/google/skills): product-specific skills; check the selected package's scope rather than assuming it teaches the agy harness. Follow the [vendor-skill policy](../agent-project/references/vendor-skills.md) when installation is requested.

## Top Links

For the wider capability inventory and when to use each feature, read the [feature map](references/features.md). It covers session lifecycle, automation, integrations, customization, execution boundaries, and operations with official links.

- [CLI overview](https://antigravity.google/docs/cli/overview/) · [CLI reference](https://antigravity.google/docs/cli/reference/)
- [Changelog](https://antigravity.google/changelog): choose the relevant product's release notes.
- [Remote Control](https://antigravity.google/docs/remote-control/): desktop access and headless service setup, lifecycle, and troubleshooting.
- [Conversations](https://antigravity.google/docs/cli/conversations/) · [Headless mode](https://antigravity.google/docs/cli/headless/)
- [Settings](https://antigravity.google/docs/cli/settings/) · [Permissions](https://antigravity.google/docs/cli/permissions/) · [Troubleshooting](https://antigravity.google/docs/cli/troubleshooting/)
