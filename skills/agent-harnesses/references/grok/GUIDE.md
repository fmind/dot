---
name: grok
description: "Grok Build sessions and configuration."
---

# Grok Build

Operate the Grok Build coding harness. The Grok chat product and model API have different documentation and release streams.

## Workflow

Follow the shared [workflow](../../SKILL.md#workflow); host specifics:

- **Read Build docs, not chat docs**: use the Build documentation and Build changelog, not the chat product's.
- **Let mise own the managed binary**: fmind/dot uses `npm:@xai-official/grok`, the [official npm distribution](https://github.com/xai-org/grok-build/blob/main/crates/codegen/xai-grok-pager/npm/grok/README.md), with platform binaries pinned by the native dependency lock. The short `grok` registry entry currently selects HTTP downloads without published checksums for `mise lock`, so it fails this repository's portable lock validation. Use `mise run upgrade` for updates; `grok update` bypasses the lock. The npm installer also writes binaries and installer settings under `GROK_HOME` (default `~/.grok`); isolate both `MISE_DATA_DIR` and `GROK_HOME` when testing an install. After migration, verify `mise which grok` and shell resolution before retiring any old self-install executable or PATH entry. Preserve `~/.grok` settings, authentication, and sessions.
- **Inspect before changing configuration**: use `grok inspect` locally to check discovered configuration, instructions, and extensions before changing them. Its output can contain private context; report only the fields needed for the task.

## Official Skills

- [Skills, plugins, and marketplaces](https://docs.x.ai/build/features/skills-plugins-marketplaces): official discovery, packaging, and compatibility guidance; follow its current marketplace sources instead of assuming a third-party Grok-named repository is official.
- **Apply the [vendor-skill policy](../../../agent-project/references/vendor-skills.md) to requested packages**: compatibility with another harness's files does not prove identical permissions or execution behavior.

## Top Links

For session recovery, automation, and integration decisions, read the [operation links](references/features.md). Use the official documentation index for other capabilities.

- [Build overview](https://docs.x.ai/build/overview) · [CLI reference](https://docs.x.ai/build/cli/reference)
- [Build changelog](https://x.ai/build/changelog)
- [Headless scripting](https://docs.x.ai/build/cli/headless-scripting) · [Sessions](https://docs.x.ai/build/features/sessions)
- [Settings reference](https://docs.x.ai/build/settings/reference) · [Permissions](https://docs.x.ai/build/features/permissions)
- [Hooks](https://docs.x.ai/build/features/hooks) · [Subagents](https://docs.x.ai/build/features/subagents)
