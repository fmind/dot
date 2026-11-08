---
name: opencode
description: "OpenCode sessions and provider configuration."
---

# OpenCode

Operate OpenCode with the project's provider, permissions, and Python tooling. Preserve the managed user configuration; this skill owns session operation, not a second copy of workstation settings.

## Workflow

Follow the shared [workflow](../../SKILL.md#workflow) and project instructions; host specifics:

1. **Resolve the provider** through [model-providers](../../../model-providers/SKILL.md). This workstation explicitly uses OpenRouter through its native login (`opencode auth login`); its model IDs start with `openrouter/`. Preserve that choice even though new application integrations default to GCP Agent Platform. Check credentials without dumping resolved configuration.
1. **Run the requested task** with the configured model, or an explicitly selected available `provider/model`. `--auto` approves permissions that are not explicitly denied; it preserves denials and does not expand the user's task authority.

   ```bash
   opencode run --agent plan '<planning task>'
   opencode run --agent build --auto '<authorized implementation task>'
   opencode run --session <session-id> '<continuation>'
   ```

1. **Use the right agent role**: `build` and `plan` are primary agents; `general` and `explore` are built-in subagents. Delegate only when independent work helps; inspect configured agent permissions because overrides can change their defaults.
1. **Verify Python changes** through project `uv` and mise tasks. OpenCode 2.x runs configured formatters but no language servers (it accepts and ignores an `lsp` block), so Ruff, ty, and pytest remain the checks.
1. **Verify discovery and results**: OpenCode 2.x has no skill-listing command; a skill's ID is its directory name, not its frontmatter `name`, and [same-name resolution](../../../agent-project/references/host-discovery.md#same-name-resolution) decides which copy loads. `opencode debug agents` lists agents. Inspect the resulting diff and checks; a session ID or event stream is not completion proof.

## Configuration

OpenCode merges user `~/.config/opencode/opencode.json` or `.jsonc` with project configuration. In the dot repository, edit the chezmoi source only when workstation configuration is in scope. Terminal UI settings such as the theme belong in the global `~/.config/opencode/cli.json`, which replaces `tui.json` (migrated once, only when `cli.json` is absent). Use the [current schema and precedence](https://opencode.ai/v2/docs/config/) for keys; keep project overrides small and avoid copying provider, compaction, or permission settings into this skill.

`opencode mcp add` writes the project configuration unless `--global`; [mcp-setup](../../../mcp-setup/SKILL.md) owns transport and trust boundaries. Listing configuration can reveal substituted credentials, so inspect only needed fields and never paste raw resolved config into reports.

## Gotchas

- **Classify provider errors before rotating keys**: distinguish a missing or invalid native login or project credential override, an unavailable `openrouter/` model ID, insufficient credit, and rate limits before rotating the key, following [openrouter](../../../model-providers/references/openrouter.md); never print the key to diagnose them.
- **Probe with `--standalone`**: every `opencode` command that accepts it, even `auth list` or `debug agents`, otherwise starts the background service (`opencode serve --service`) and creates its database under the real HOME; stop a stray one with `opencode service stop`. `debug paths` and `service` reject `--standalone` (2.2.6).
- **Sharing is publication**: `/share` or changing the managed `"share": "disabled"` publishes session contents; require explicit sharing authority.
- **Pairing and credential export expose data**: `opencode pair --remote` exposes the server to the internet through OpenTunnel, and `opencode auth export` prints stored secrets; require explicit authority for either, and check logins with `opencode auth list --standalone`, which prints no secrets.
- **V1 plugins do not run in 2.x**: use the [plugin guide](https://opencode.ai/v2/docs/build/plugins/) for event hooks; do not translate another harness's hook schema into OpenCode settings.

## Official Skills

- [Skill discovery and permissions](https://opencode.ai/v2/docs/skills/): the official consumer-facing contract.
- [Upstream repository](https://github.com/anomalyco/opencode): distinguish contributor skills and fixtures from consumer packages; do not install internal examples as a general OpenCode skill.

## Documentation

- [Documentation](https://opencode.ai/v2/docs/) · [CLI commands](https://opencode.ai/v2/docs/cli/commands/) · [Migrate from V1](https://opencode.ai/v2/docs/migrate-v1/)
- Releases: [Changelog](https://opencode.ai/changelog) · [GitHub releases](https://github.com/anomalyco/opencode/releases)
- Companion skills: [python-stack](../../../python-stack/references/foundation/GUIDE.md), [model-providers](../../../model-providers/SKILL.md), [mcp-setup](../../../mcp-setup/SKILL.md), [agent-project](../../../agent-project/SKILL.md).
