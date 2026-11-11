# Vendor Skill Packages

Shared review-first policy for third-party skill bundles; tool guides name only the upstream repo and selection.

## Workflow

1. **Pin a snapshot**: run `DISABLE_TELEMETRY=1 skills add <source> --list --json` in the target project and resolve the latest compatible release tag (or exact commit when untagged) to `https://github.com/<owner>/<repo>/tree/<full-commit>`.
1. **Vet before installing**: print `SKILL.md` with `DISABLE_TELEMETRY=1 skills use <snapshot> --skill <name>`, inspect the pinned commit's repository tree directly for `scripts/`, hooks, MCP configs, symlinks, and linked files (`skills use` outputs `SKILL.md` text only), and audit the full package via [skill-security-review](../../code-security/references/skill-security-review/GUIDE.md) (skip contributor/sample skills and distinguish wrapper bundles from first-party library skills).
1. **Install project-scoped**: check [name collisions](#name-collisions), then run `DISABLE_TELEMETRY=1 skills add <snapshot> --skill <name> -y` (never `--global`); add plugin hooks, agents, commands, MCP/LSP servers, or cloud resources separately only if needed.
1. **Validate**: inspect `DISABLE_TELEMETRY=1 skills list --json`, `.agents/skills/`, and `skills-lock.json`, confirm content matches the reviewed commit, and run the repo gate.
1. **Update deliberately**: run `DISABLE_TELEMETRY=1 skills update -p -y` only on a clean tree and repeat the full review.

## Name collisions

Check frontmatter `name` against `~/.agents/skills` and `.agents/skills` ([same-name resolution](host-discovery.md#same-name-resolution)). Never install a duplicate where `~/.agents/skills` loads—read it via `DISABLE_TELEMETRY=1 skills use <snapshot> --skill <name>` (or `gh skill preview`) instead; install a duplicate only in isolated workers/CI lacking the global catalog and state the trade-off.

## Version Policy

Use `skills` prefixed per command with `DISABLE_TELEMETRY=1` (never export globally—Claude Code disables Remote Control when set). Preview `gh skill preview <owner/repo> <name>@<version>` and `gh skill install <owner/repo> <name> --pin <version>` enforce immutable pins when required, without mixing both managers on one skill. `fmind/dot` validates first-party skills via `mise run check:skills` (`gh skill publish --dry-run` + local contracts).

## Documentation

- [skills CLI](https://skills.sh/docs/cli) · [gh skill preview](https://cli.github.com/manual/gh_skill_preview) · [gh skill install](https://cli.github.com/manual/gh_skill_install)
