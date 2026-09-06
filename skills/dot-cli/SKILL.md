---
name: dot-cli
description: Operate fmind/dot commands for agent sync, transcript SQLite queries, repository pulls, environment verification, and cache pruning. Use when invoking dot.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/dot-cli
  created: "2026-07-31"
  updated: "2026-09-06"
---

# Dot CLI

`dot` is the unified typed Python CLI of `fmind/dot`, installed at `~/.local/bin/dot`. Every command has a one-letter alias (`pull-request` also answers to `pr`); `dot <command> --help` gives the exact flags.

## Commands

| Command            | Alias     | Purpose                                                                                                                                                                |
| ------------------ | --------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `dot agent`        | `a`       | Agent integrations: `clean` (`c`), `doctor` (`d`), `hook` (`h`), `session` (`s`), `usage` (`u`)                                                                        |
| `dot chezmoi`      | `m`       | `clean` (`c`) finds `$HOME` orphans once managed by chezmoi and moves them to timestamped recoverable backups (`--yes`, `--interactive`)                               |
| `dot commit`       | `c`       | AI Conventional Commit from the staged diff; runs `git add -A` first when nothing is staged (`--type`, `--scope`)                                                      |
| `dot completion`   | `g`       | Generate fish completions for `dot` and external CLIs                                                                                                                  |
| `dot config`       | `f`       | `~/.config/dot.yaml`: `show` (`s`), `path` (`p`), `init` (`i`), `edit` (`e`), `validate` (`v`)                                                                         |
| `dot context`      | `t`       | Bounded, redacted project context pack (`--bytes`, `--tokens`, `--format json`)                                                                                        |
| `dot help`         | `h`       | Show help for `dot` or one nested command path                                                                                                                         |
| `dot login`        | `l`       | OAuth login wrappers: `github` (`g`), `workspace` (`w`), `gcp` (`c`)                                                                                                   |
| `dot notify`       | `n`       | Desktop notification: `dot notify <agent> <event>` for hooks, `dot notify <summary> [headline] [details...]` for alerts                                                |
| `dot prune`        | `x`       | Reclaim disk space from agent session logs and caches; flags and safety flow in [references/prune-flags.md](references/prune-flags.md); preview before running it live |
| `dot pull`         | `p`       | Concurrently pull the repositories listed in `~/.config/dot.yaml` (`--push` also pushes clean repos)                                                                   |
| `dot pull-request` | `pr`, `b` | AI PR description then `gh pr create` (`--base`, `--title`, `--draft`, `--label`, `--reviewer`, `--assignee`)                                                          |
| `dot release`      | `r`       | Prepare, tag, and push a dot release (`--yes`); see `.agents/skills/dot-release` inside the dot repository                                                             |
| `dot setup`        | `u`       | `workspace` (`w`) enables GCP APIs on a project and links it to `gws`: `dot setup workspace [PROJECT_ID]`                                                              |
| `dot status`       | `s`       | Unified Git repository and Docker status summary (`--json`)                                                                                                            |
| `dot verify`       | `v`       | Sanity checks on environment, tools, secrets, and install freshness (`--json`, `--fix`)                                                                                |
| `dot version`      | `i`       | Print the installed Python package version                                                                                                                             |

Global flags: `--config/-c <path>` (or `DOT_CONFIG_PATH`) and `--verbose` (or `DOT_VERBOSE`).

## Workflow

1. **Health**: `dot verify`, then `dot agent doctor` for persona, hooks, skills, and session-store health; `dot verify --fix` repairs secret-file permissions, while `dot agent doctor --fix` reapplies managed agent integration targets with chezmoi.
1. **Sessions**: `dot agent session sync` ingests transcripts from each verified source into `~/.agents/sessions/v1/`; `list`, `show`, and `export` read the store.
1. **Legacy sessions**: `dot agent session migrate` dry-runs the selection of the most complete transcript per lineage; `--apply` writes it.
1. **Disk**: `dot prune --dry-run --all --deep` to preview every selected target, inspect the candidate paths, then rerun the same selection without `--dry-run`; every target and depth is in [references/prune-flags.md](references/prune-flags.md), and long-term agent memory (`memory/`, `MEMORY.md`) is never pruned.
1. **Reinstall after source edits**: inside the dot repository, `mise run deploy` builds the Python package and reinstalls it at `~/.local/bin/dot` with uv.

## Gotchas

- **Stale install**: when `dot agent doctor` reports `command-unavailable`, run `mise run deploy` inside the dot repository to sync the installed Python CLI with the deployed hooks.
- **`dot commit` stages everything**: with nothing staged it runs `git add -A` before generating the message; stage selectively first when the tree holds unrelated changes.

## Documentation

- [fmind/dot](https://github.com/fmind/dot) — source, README, and the repository-scoped skills (`.agents/skills/dot-release`, `.agents/skills/chezmoi`).
- Companion skills: [agent-usage](../agent-usage/SKILL.md) (token accounting behind `dot agent usage`), [mise](../mise/SKILL.md) (`mise run deploy`).
