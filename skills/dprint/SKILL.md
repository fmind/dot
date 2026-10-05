---
name: dprint
description: "Format Markdown, JSON, TOML, and YAML with dprint."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/dprint
  created: "2026-06-29"
  updated: "2026-10-05"
---

# dprint

The formatter for configuration and markup files (JSON, Markdown, TOML, YAML); dprint formats only, while Python formatting and linting live in [ruff](../python-stack/references/ruff.md).

## Configuration

dprint searches the current directory upward for `dprint.json(c)` or `.dprint.json(c)` and falls back to the global config (`DPRINT_CONFIG_DIR`) only when nothing is found. Global fallback can prompt before `fmt`; use a local, version-pinned configuration for non-interactive project gates.

1. **Copy (default)**: copy a known-good `dprint.json` into the project root; it is self-contained and version-pinned. The first run downloads uncached plugins; later runs use dprint's local cache. Bump plugin versions per repository.
1. **Extends (DRY)**: set `"extends"` to a single source of truth, a local path or a commit-pinned URL such as `"https://raw.githubusercontent.com/fmind/dot/<commit>/dprint.json"`; override rules or add plugins locally.

## Commands

Repository tasks own the two gate commands; add and pin a plugin with `dprint add <plugin>`.

```toml
[tasks."format:dprint"]
description = "Format JSON, Markdown, TOML, YAML (dprint)"
run = "dprint fmt --allow-no-files" # mise appends the hook's {staged_files}; the flag keeps an empty list from exiting 14

[tasks."check:format"]
description = "Check config and markup formatting (dprint)"
run = "dprint check" # non-zero exit on drift
```

## Gotchas

- **Prefer `npm:` plugin references**: `npm:@dprint/markdown@<version>` over `https://plugins.dprint.dev/...wasm` URLs; both resolve, and the npm form makes the current version one `npm view <plugin> version` away.
- **Plugin order is precedence**: the `plugins` array order decides which plugin claims a file; keep specialized plugins before generic ones.
- **Load plugins for embedded code**: the Markdown plugin formats fenced JSON, TOML, and YAML only when those plugins are loaded too.
- **Format staged, check the whole tree**: `format:dprint` takes `{staged_files}` from the hook, which restages fixes; `check:format` always runs on the whole tree. Outside a hook, `dprint fmt --staged` or `--dirty` selects the staged or uncommitted files itself.

## Documentation

- [dprint](https://dprint.dev) · [Configuration](https://dprint.dev/config/) · [CLI](https://dprint.dev/cli/)
- Releases: [dprint](https://github.com/dprint/dprint/releases)
- Companion skills: [mise](../mise/SKILL.md) (task vocabulary), [lefthook](../github-actions/references/lefthook.md) (the pre-commit hook that calls `format:dprint`).
