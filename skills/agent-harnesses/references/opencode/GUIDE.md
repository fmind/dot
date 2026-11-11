---
name: opencode
description: "OpenCode sessions and provider configuration."
---

# OpenCode

Operate OpenCode with the project's provider, permissions, and Python checks while preserving managed workstation settings.

## Workflow

Follow the shared [workflow](../../SKILL.md#workflow); host specifics:

1. **Resolve the provider** via [model-providers](../../../model-providers/SKILL.md). This workstation defaults OpenCode to OpenRouter (`opencode auth login`, `openrouter/` model IDs)—preserve it without dumping resolved config.
1. **Run the task** with the configured or requested `provider/model`; `--auto` approves non-denied tool permissions without expanding task authority:

   ```bash
   opencode run --agent plan '<planning task>'
   opencode run --agent build --auto '<authorized implementation task>'
   opencode run --session <session-id> '<continuation>'
   ```

1. **Pick the agent role**: `build` and `plan` are primary; `general` and `explore` are subagents. Check configured permission overrides before delegating.
1. **Verify Python work** with project `uv` and mise tasks—OpenCode 2.x runs configured formatters but ignores `lsp` blocks, so Ruff, ty, and pytest are the gates.
1. **Verify discovery and diffs**: OpenCode 2.x has no skill-list command; skill IDs are directory names resolved per [same-name resolution](../../../agent-project/references/host-discovery.md#same-name-resolution), and `opencode debug agents` lists agents. Check diffs and gates rather than session IDs.

## Configuration

OpenCode merges `~/.config/opencode/opencode.json`/`.jsonc` with project config; TUI settings (such as theme) live in `~/.config/opencode/cli.json` (migrated once from `tui.json` if absent). Check the [config schema](https://opencode.ai/v2/docs/config/), edit chezmoi sources only when workstation config is in scope, and never paste resolved config (which substitutes secrets). `opencode mcp add` writes project config unless `--global` ([mcp-setup](../mcp-setup.md)).

## Gotchas

- **Classify errors before rotating keys**: separate missing login/override, bad `openrouter/` ID, empty credit, and rate limits per [openrouter](../../../model-providers/references/openrouter.md) without printing keys.
- **Pass `--standalone` on probes**: commands like `auth list` or `debug agents` otherwise spawn `opencode serve --service` and its DB under `$HOME` (`opencode service stop` stops it; `debug paths` and `service` reject `--standalone` in 2.x).
- **Gate sharing, pairing, and export**: `/share` or overriding `"share": "disabled"` publishes transcripts; `opencode pair --remote` opens an OpenTunnel; `opencode auth export` prints secrets (use `opencode auth list --standalone` instead).
- **Use 2.x plugins**: V1 plugins do not run in 2.x; follow the [plugin guide](https://opencode.ai/v2/docs/build/plugins/).

## Official Skills

- [Skill discovery and permissions](https://opencode.ai/v2/docs/skills/) · [anomalyco/opencode](https://github.com/anomalyco/opencode) (do not install internal contributor examples as general skills).

## Documentation

- [Documentation](https://opencode.ai/v2/docs/) · [CLI commands](https://opencode.ai/v2/docs/cli/commands/) · [Migrate from V1](https://opencode.ai/v2/docs/migrate-v1/)
- Releases: [Changelog](https://opencode.ai/changelog) · [GitHub releases](https://github.com/anomalyco/opencode/releases)
- Companion skills: [python-stack](../../../python-stack/references/foundation/GUIDE.md), [model-providers](../../../model-providers/SKILL.md), [mcp-setup](../mcp-setup.md), [agent-project](../../../agent-project/SKILL.md).
