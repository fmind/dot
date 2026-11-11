---
name: dprint
description: "Configure and format JSON, Markdown, TOML, and YAML with dprint."
---

# dprint

Format JSON, Markdown, TOML, and YAML with `dprint` (Python formatting and linting belong to [Ruff](../../python-stack/references/foundation/GUIDE.md#ruff)).

## Configuration

Commit a version-pinned `dprint.json` (or `.config/dprint.json`, 0.64+) at the repo root; never rely on global fallback config in gates, which can prompt before `fmt`.

1. **Copy (default)**: copy `fmind/dot`'s root `dprint.json`, remove dot-specific excludes (`dot_config/mise/locks/**`, `modify_*`), and bump plugins per repo.
1. **Extends**: reference a local path or commit-pinned URL (`"https://raw.githubusercontent.com/fmind/dot/<commit>/dprint.json"`) in `"extends"` and override locally.

## Commands

Add/pin plugins with `dprint add <plugin>` and expose the standard tasks:

```toml
[tasks."format:dprint"]
description = "Format JSON, Markdown, TOML, YAML (dprint)"
run = "dprint fmt --allow-no-files" # mise appends {staged_files}; prevents exit 14 on empty lists

[tasks."check:format"]
description = "Check config and markup formatting (dprint)"
run = "dprint check"
```

## Gotchas

- **Use `npm:` plugin specifiers**: prefer `npm:@dprint/markdown@<version>` over `.wasm` URLs; preview updates with `dprint config update --dry-run` and apply via [upgrade-tools](../../upgrade-tools/SKILL.md).
- **Include plugins for fenced blocks**: Markdown formats fenced JSON/TOML/YAML blocks only when those plugins are also configured.
- **Staged format vs whole-tree check**: hooks pass `{staged_files}` to `format:dprint` while `check:format` checks the full tree; manually use `dprint fmt --staged` or `--dirty` when needed.

## Documentation

- [dprint](https://dprint.dev) · [Configuration](https://dprint.dev/config/) · [CLI](https://dprint.dev/cli/) · [releases](https://github.com/dprint/dprint/releases)
- Companion skills: [mise](../SKILL.md), [lefthook](../../github-actions/references/lefthook.md).
