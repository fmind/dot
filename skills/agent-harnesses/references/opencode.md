---
name: opencode
description: "OpenCode sessions and provider configuration."
---

# OpenCode

Operate OpenCode with the project's provider, permissions, and Python checks while preserving managed workstation settings.

## Workflow

Follow the shared [workflow](../SKILL.md#workflow); host specifics:

1. **Resolve the provider** via [model-providers](../../model-providers/SKILL.md). This workstation defaults OpenCode to OpenRouter (`opencode auth login`, `openrouter/` model IDs)—preserve it without dumping resolved config.
1. **Run the task** with the configured or requested `provider/model`; `--auto` approves non-denied tool permissions without expanding task authority:

   ```bash
   opencode run --agent plan '<planning task>'
   opencode run --agent build --auto --format json '<authorized task>'
   opencode run --session <session-id> --fork '<branched continuation>'
   opencode run --worktree --auto '<isolated repo task>'
   ```

   Pass `--thinking` to print reasoning blocks and `opencode session list --format json` to inspect recent project sessions.
1. **Pick the agent role**: `build` and `plan` are primary; `general` and `explore` are subagents. Check configured permission overrides before delegating.
1. **Verify Python work** with project `uv` and mise tasks—OpenCode 2.x runs configured formatters but ignores `lsp` blocks, so Ruff, ty, and pytest are the gates.
1. **Verify discovery and diffs**: OpenCode 2.x has no skill-list command; skill IDs are directory names resolved per [same-name resolution](../../agent-project/references/host-discovery.md#same-name-resolution), and `opencode debug agents` lists agents. Check diffs and gates rather than session IDs.

## Configuration

`dot_config/private_opencode/modify_private_opencode.json` merges `~/.config/opencode/opencode.json` (project `opencode.json`/`.jsonc` overlays it); TUI state (`theme: "fmind"`, `attention: {notifications: false, sound: false}`) lives in `~/.config/opencode/cli.json` via `dot_config/private_opencode/modify_cli.json` (OpenCode 2.x reads only global `cli.json`—migrating `tui.json` once when `cli.json` is absent—ignores `lsp`, and dropped `compaction.prune`). Check the [config schema](https://opencode.ai/v2/docs/config/), edit chezmoi sources when updating managed keys, never paste resolved config, and note `opencode mcp add` writes project config unless `--global` ([mcp-setup](mcp-setup.md)).

## Gotchas

- **Classify errors before rotating keys**: separate missing login/override, bad `openrouter/` ID, empty credit, and rate limits per [openrouter](../../model-providers/references/openrouter.md) without printing keys.
- **Pass `--standalone` on probes**: `auth list` or `debug agents` otherwise spawn `opencode serve --service` under `$HOME` (`opencode service stop` stops it; `debug paths` and `service` reject `--standalone` in 2.x).
- **Gate sharing, ACP, pairing, and export**: `/share`, `share != disabled`, `opencode acp`, and `opencode pair --remote` open external/editor bridges or publish transcripts; `opencode auth export` prints secrets (use `opencode auth list --standalone`).
- **Use 2.x plugins**: V1 plugins do not run in 2.x ([plugin guide](https://opencode.ai/v2/docs/build/plugins/)).

## Official Skills

- [Skill discovery and permissions](https://opencode.ai/v2/docs/skills/) · [anomalyco/opencode](https://github.com/anomalyco/opencode) (do not install contributor examples as general skills).

## Documentation

- [Documentation](https://opencode.ai/v2/docs/) · [CLI commands](https://opencode.ai/v2/docs/cli/commands/) · [Changelog](https://opencode.ai/changelog) · [Releases](https://github.com/anomalyco/opencode/releases)
- Companion skills: [python-stack](../../python-stack/references/foundation/GUIDE.md), [model-providers](../../model-providers/SKILL.md), [mcp-setup](mcp-setup.md), [agent-project](../../agent-project/SKILL.md).
