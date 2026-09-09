---
name: opencode
description: Operate OpenCode terminal AI coding agent with Google ADC, autonomous permissions, subagents, and Python tooling. Use for OpenCode CLI sessions, configuration, or tasks.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/opencode
  created: "2026-09-08"
  updated: "2026-09-08"
---

# OpenCode

Operate OpenCode with the project's provider, permissions, and Python tooling. Preserve the managed user configuration; this skill owns session operation, not a second copy of workstation settings.

## Workflow

1. **Inspect the installed contract**: use `opencode --version`, `opencode run --help`, and project instructions. Resolve the intended workspace and existing session before starting or resuming work.
1. **Resolve the provider**: for Vertex AI, establish the project, location, and ADC identity through [gcloud](../gcloud/SKILL.md). ADC can come from a credential file, an attached identity, or an approved impersonation setup; the presence of one file is not an authentication test.
1. **Run the requested task** with the configured model, or an explicitly selected available `provider/model`. `--auto` approves permissions that are not explicitly denied; it preserves denials and does not expand the user's task authority.

   ```bash
   opencode run --agent plan '<planning task>'
   opencode run --agent build --auto '<authorized implementation task>'
   opencode run --session <session-id> '<continuation>'
   ```

1. **Use the right agent role**: `build` and `plan` are primary agents; `general` and `explore` are built-in subagents. Delegate only when independent work helps; inspect configured agent permissions because overrides can change their defaults.
1. **Verify Python changes** through project `uv` and mise tasks. Auto-formatting and LSP diagnostics depend on installed tools and configuration; they do not replace Ruff, ty, or pytest.
1. **Verify discovery and results**: `opencode debug skill` lists available skills, including shared `.agents/skills` paths. Treat that output as potentially containing private instructions. Inspect the resulting diff and checks; a session ID or event stream is not completion proof.

## Configuration

OpenCode merges user `~/.config/opencode/opencode.json` or `.jsonc` with project configuration. In the dot repository, edit the chezmoi source only when workstation configuration is in scope. Use the [current schema and precedence](https://opencode.ai/docs/config/) for keys; keep project overrides small and avoid copying provider, compaction, or permission settings into this skill.

Use `opencode mcp add --help` for the installed setup interface and [agent-mcp](../agent-mcp/SKILL.md) for transport and trust boundaries. Listing configuration can reveal substituted credentials, so inspect only needed fields and never paste raw resolved config into reports.

## Gotchas

- **Provider errors**: distinguish expired/revoked ADC, wrong project, unavailable model, IAM denial, and quota exhaustion before reauthenticating; never print an access token to diagnose them.
- **Sharing is publication**: `--share` can expose session contents; require explicit sharing authority.
- **Official skills**: the inspected `anomalyco/opencode` tree contains contributor skills and test fixtures, not a general consumer skill. Use official docs and installed help for this workflow.

## Documentation

- [OpenCode CLI](https://opencode.ai/docs/cli/) · [Agents](https://opencode.ai/docs/agents/) · [Skills](https://opencode.ai/docs/skills/) · [Providers](https://opencode.ai/docs/providers/)
- Companion skills: [python-stack](../python-stack/SKILL.md), [gcloud](../gcloud/SKILL.md), [agent-mcp](../agent-mcp/SKILL.md), [agent-project](../agent-project/SKILL.md).
