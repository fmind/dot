# `dot prune` Flags

Every target and depth accepted by `dot prune`; the safety-ordered workflow lives in the [dot CLI skill](../SKILL.md). Nothing runs unless a target is selected, and targets compose freely (`dot prune --agents --python`). The installed CLI's `dot prune --help` stays the live reference.

## Targets

| Flag       | Short | Default / deep level | Removes                                                                                 |
| ---------- | ----- | -------------------- | --------------------------------------------------------------------------------------- |
| `--agents` | `-a`  | `sessions`           | Expired source and archive sessions only when safe successor evidence exists            |
| `--docker` | `-d`  | `build` / `system`   | Docker build cache; deep also removes stopped containers, networks, and dangling images |
| `--python` | `-p`  | `cache` / `all`      | Unused uv cache entries; deep wipes the uv cache and purges pip                          |
| `--mise`   | `-m`  | `cache` / `configs`  | Unused tool versions, cache, and downloads; deep also removes untracked config links     |
| `--tools`  | `-t`  | `cache`              | Configured scanner caches plus the dprint cache                                          |
| `--all`    | `-A`  | configured levels    | Every target; combine with `--deep` for the deepest level of each target                 |

## Modifiers

| Flag        | Short | Effect                                                                                                                                                          |
| ----------- | ----- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `--deep`    |       | Select each chosen target's deepest cleanup level.                                                                                                               |
| `--days N`  | `-D`  | Override age retention for every agent session store; `0` makes every age eligible, and source safety checks still apply. Defaults to each store's `keep_days`. |
| `--dry-run` | `-N`  | Report what would be removed without deleting anything or running cleanup tools.                                                                                 |

## Gotchas

- **Preview first**: `dot prune --dry-run --all --deep` is the safe way to see the deepest possible sweep before committing to it.
- **Memory is never pruned**: long-term agent memory (`memory/`, `MEMORY.md`) is out of scope for every target.
- **Deep Python cleanup is expensive to undo**: the uv cache refills on the next sync, so prefer the configured `cache` depth unless the disk is genuinely full.
