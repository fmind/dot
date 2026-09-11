---
name: claude
description: Operate Claude Code sessions and customization using current Anthropic guidance. Use when configuring claude, skills, hooks, plugins, or Remote Control.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/claude
  created: "2026-09-09"
  updated: "2026-09-11"
---

# Claude Code

Operate Claude Code's harness and session features. Application development with the Anthropic API is a separate workflow.

## Workflow

1. Inspect `claude --version` and `claude --help`, then identify the workspace, configuration scope, and session to start or resume.
1. Read the relevant official page and changelog before using evolving flags or settings. Compare installed help with the version-specific CLI reference; help can omit supported flags. Report confirmed version gaps before applying a newer recipe to an older installation.
1. Use the documented session, customization, or Remote Control interface for the requested operation. Read setting precedence before changing permissions or hooks; hook commands execute code.
1. Verify the session result and configuration or skill discovery in Claude Code. Use [agent-project](../agent-project/SKILL.md) for shared instruction layout and [agent-mcp](../agent-mcp/SKILL.md) for MCP registration.

## Official Skills

- [Anthropic skills](https://github.com/anthropics/skills): reusable examples and document skills; inspect each package's license and scope.
- [Official plugin directory](https://github.com/anthropics/claude-plugins-official): browse maintained integrations alongside the skill examples.
- [Skill authoring and discovery](https://code.claude.com/docs/en/skills) · [Plugin discovery](https://code.claude.com/docs/en/discover-plugins).
- Select a needed package through the [vendor-skill policy](../agent-project/references/vendor-skills.md); link to upstream guidance instead of maintaining a copied manual here.

## Top Links

For session recovery, automation, and integration decisions, read the [operation links](references/features.md). Use the official documentation index for other capabilities.

- [Overview](https://code.claude.com/docs/en/overview) · [CLI reference](https://code.claude.com/docs/en/cli-reference)
- [Changelog](https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md)
- [Settings](https://code.claude.com/docs/en/settings) · [Permissions](https://code.claude.com/docs/en/permissions)
- [Remote Control](https://code.claude.com/docs/en/remote-control) · [Headless usage](https://code.claude.com/docs/en/headless)
- [Hooks](https://code.claude.com/docs/en/hooks) · [Subagents](https://code.claude.com/docs/en/sub-agents)
