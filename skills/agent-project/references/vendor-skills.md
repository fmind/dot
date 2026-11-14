# Vendor Skill Packages

Shared review-first policy for third-party skill bundles; tool guides name only the upstream repo and selection. Prefix `skills` commands per invocation with `DISABLE_TELEMETRY=1` (never export globally—Claude Code disables Remote Control when set).

## Workflow

1. **Search and pin a snapshot**: find candidates via `DISABLE_TELEMETRY=1 skills find <query> [--owner <owner>]` or list a repo via `DISABLE_TELEMETRY=1 skills add <source> --list --json`, then resolve the release tag or commit SHA to `https://github.com/<owner>/<repo>/tree/<full-commit>`.
1. **Vet before installing**: inspect `SKILL.md` via `DISABLE_TELEMETRY=1 skills use <snapshot>@<name>` (or `--skill <name>`) and inspect the pinned commit tree directly for `scripts/`, hooks, MCP configs, symlinks, and linked files via [skill-security-review](../../code-security/references/skill-security-review/GUIDE.md).
1. **Install project-scoped**: check [name collisions](#name-collisions), then run `DISABLE_TELEMETRY=1 skills add <snapshot> -s <name> [-a <agent>] [--copy] -y` (never `-g`/`--global`; `-a` targets hosts and `--copy` writes files rather than symlinks). Restore lockfiles on clean CI/setup via `DISABLE_TELEMETRY=1 skills experimental_install [--frozen-lockfile]`.
1. **Validate & update deliberately**: inspect `DISABLE_TELEMETRY=1 skills list --json`, `.agents/skills/`, and `skills-lock.json`, confirm bytes match the reviewed commit, and run the repo gate; run `DISABLE_TELEMETRY=1 skills update -p -y` only on a clean tree and re-vet first.

## Name collisions

Check frontmatter `name` against `~/.agents/skills` and `.agents/skills` ([same-name resolution](host-discovery.md#same-name-resolution)). Never install a duplicate where `~/.agents/skills` loads—read it via `DISABLE_TELEMETRY=1 skills use <snapshot>@<name>` (or `gh skill preview`) instead; install a duplicate only in isolated workers/CI lacking the global catalog and state the trade-off.

## Version Policy

Preview `gh skill preview <owner/repo> <name>@<version>` and `gh skill install <owner/repo> <name> --pin <version>` enforce immutable pins when required without mixing managers on one skill. `fmind/dot` validates first-party skills via `mise run check:skills` (`gh skill publish --dry-run` + local contracts).

## Documentation

- [skills CLI](https://skills.sh/docs/cli) · [gh skill preview](https://cli.github.com/manual/gh_skill_preview) · [gh skill install](https://cli.github.com/manual/gh_skill_install)
