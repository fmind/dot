# `dot prune` Flags

`dot prune` is a dry-run unless `--apply` is present. No cleanup runs until a target is selected, and targets compose freely. Use `dot prune --help` as the installed reference.

## Targets

| Flag                | Short | Default / deep level | Removes |
| ------------------- | ----- | -------------------- | ------- |
| `--agents`          | `-a`  | `sessions`           | Expired raw and archived sessions only with verified successor evidence. |
| `--agent-artifacts` |       | `all`                | Generated `.agents/prompts`, `.agents/proposals`, and `.agents/reports` contents. |
| `--docker`          | `-d`  | `build` / `system`   | Docker build cache; deep also removes stopped containers, networks, and dangling images. |
| `--python`          | `-p`  | `cache` / `all`      | Unused uv cache entries; deep clears the uv cache and purges pip. |
| `--mise`            | `-m`  | `cache` / `configs`  | Unused tool versions, cache, and downloads; deep also removes untracked config links. |
| `--tools`           | `-t`  | `cache`              | Configured scanner caches and the dprint cache. |
| `--all`             | `-A`  | configured levels    | Every target, including agent artifacts; combine with `--deep` for maximum levels. |

## Modifiers

| Flag       | Short | Effect |
| ---------- | ----- | ------ |
| `--deep`   |       | Select each chosen target's deepest cleanup level. |
| `--days N` | `-D`  | Override agent-session retention; source successor checks still apply. |
| `--apply`  |       | Delete selected data and run cleanup tools. Without it, the command only reports the plan. |

Preview the broadest cleanup with `dot prune --all --deep`. Apply it only with `dot prune --all --deep --apply` after reviewing the reported targets.

Long-term agent memory (`memory/` and `MEMORY.md`) is outside every prune target.
