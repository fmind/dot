# AGENTS.md (Project)

This is `fmind/dot` — chezmoi + mise dotfiles for AI-CLI-first, Python-first development on Linux and macOS. Setup, usage, and common tasks live in `README.md`.

## House rules

- **Edit chezmoi sources, never deployed copies**: change this repository, not files under `$HOME`; automation always runs `chezmoi apply --force`. Naming, templates, and secrets: [chezmoi skill](.agents/skills/chezmoi/SKILL.md).
- **Match validation to the task**: read-only reviews need only evidence checks; documentation and instruction edits need relevant formatting, links, and contract checks; behavior changes need focused regression tests and affected static checks. Run `mise run all` for cross-cutting changes, dependencies, packaging, releases, or explicit full qualification. Reuse passing results while relevant inputs remain unchanged.
- **Never commit decrypted secrets**: `*.age` files are encrypted; never modify or commit decrypted versions. Native credentials are create-only seeds; scoped keys use `dot secret run`. Preserve account overrides and keep values out of diff/log output; [Secret Management](README.md#secret-management) owns setup and migration.
- **Never use sudo**: stay user-space; install via `mise`.
- **Lock tools with mise, never edit generated locks**: use mise lockfile revision 3 for reproducible tool installs. Keep the global lockfile and its referenced native dependency files together; do not edit or format generated files. `mise run lock` resolves the portable source baseline in isolation and captures its complete bundle; `mise run tools` installs with `--locked`. Python application dependencies remain locked in `dot/uv.lock`.
- **Keep README for users; workflows go in skills**: keep setup, auth, everyday usage, and a short task reference in `README.md`; keep detailed contributor workflows in skills.
- **Pin themes to fmind/theme**: [fmind/theme](https://github.com/fmind/theme) owns the palette and native app files. Fetch standalone themes via chezmoi externals pinned to one upstream commit with SHA-256 checksums (`mise run upgrade` advances the pin); when tools require merged styles, copy only the native theme block with an upstream source comment. Terminal tools follow the Ghostty ANSI palette or select terminal-aligned themes.
- **Inherit terminal fonts from Ghostty**: terminal apps inherit GoogleSansCode Nerd Font Mono from Ghostty.
- **Enable Vim mode in every TUI** that supports it.

## Workflows

See [common tasks](README.md#repository-tasks); `mise tasks` lists all tasks and aliases. Tasks run via `mise run <task>` (if `mise` is not in `$PATH`, call `~/.local/bin/mise` directly). Invoking tasks from `dot/` resolves to the same root definitions.

Key routines:

- **Iterate**: Edit source → run the relevant checks above → preview the affected chezmoi diff → apply when deployment is in scope. Apply executes eligible installation hooks as well as writing managed files. Lefthook runs commit/push checks; pre-run them only to diagnose a failure. CI retains the full gate.
- **Documentation**: `mise run check:skills` checks both skill catalogs, their context budgets, and local links in skills and root documentation. [repository-docs](skills/repository-docs/SKILL.md) owns documentation synchronization.
- **Workstation vs Gate**: `mise run verify` and `mise run doctor` inspect local workstation health; `mise run check`, `test`, and `all` validate the repository. `all` also formats files; isolate it when unrelated edits are present.
- **Add tool**: Insert into `[tools]` in `dot_config/mise/config.toml`, alphabetically within its group (backend-prefixed entries, registry names, then per-platform tables) → `mise run lock` → `mise run tools`.
- **Upgrade tools**: `mise run upgrade` updates this workstation's tools and lockfiles only. Upgrade another repository only on an explicit request for it, inside that repository, per [upgrade-tools](skills/upgrade-tools/SKILL.md).
- **Workstation commands**: `dot login`, `setup`, `cache`, and `prune` own native provider operations; mise owns repository installation and validation. Authentication and cleanup are explicit commands, not apply hooks.
- **Usage statistics**: [agent-usage](skills/agent-usage/SKILL.md) owns reports, subscription configuration, and measurement rules.
- **CLI (`dot`)**: Follow [dot-development](.agents/skills/dot-development/SKILL.md) for implementation, tests, and installation proof; [dot-cli](skills/dot-cli/SKILL.md) owns command operation.
- **Manage skills**: [dot-skills](.agents/skills/dot-skills/SKILL.md) owns catalog changes, validation, and the 5,000-token scope budget; [skillify](skills/skillify/SKILL.md) owns authoring and admission.
- **Completions**: `mise run completions` installs Fish completions from the deployed CLI; the host-dependent `check:completions` runs outside `all` and gates every release.
- **Verify**: [dot-verify](.agents/skills/dot-verify/SKILL.md) qualifies the checkout (review, docs sync, all gates, CLI smoke tests) without committing.
- **Release**: `/dot-release` runs dot-verify, commits, pushes, then follows [dot-release](.agents/skills/dot-release/SKILL.md) for `mise run release`, recovery, and publication verification.

## Agents

- **Subagents**: `dot_agents/supagents/` owns shared roles; `mise run format:agents` (part of `format`) compiles native files using `supagents.yaml`. Never edit generated profiles directly. `check:agents` rejects drift; see [cross-harness agents](skills/agent-project/references/cross-harness-agents.md).
- **Persona**: `dot_agents/AGENTS.md` deploys to `~/.agents/AGENTS.md`, consumed by all agent harnesses.
- **Skills**: `skills/` is the global catalog, linked into the shared `~/.agents/skills/` directory per [dot-skills](.agents/skills/dot-skills/SKILL.md); `.agents/skills/` holds local skills and `.claude/skills` links to it.

## Layout

- `dot/` contains the runtime package, repository-only `dot_tasks/`, uv lock, and pytest suite.
- `dot_claude/`, `dot_codex/`, `dot_copilot/`, `dot_gemini/`, `dot_grok/`, and `dot_config/opencode/` adapt the shared persona to each host; other host state is gitignored.
- `.chezmoitemplates/` holds the JSON/TOML merge, shell managed-block, skill-catalog, and hook `dot`-path helpers; `.chezmoiignore` gates platform-specific targets, including darwin-only `.zprofile` and Crostini-only notification and garcon files.
- `.github/` owns CI, release, security, and dependency-update automation; `.github/assets/` holds the README's SVG illustrations, outside chezmoi deployment.
- Mise trust is machine-local (`mise trust` or unmanaged `~/.config/mise/conf.d/trust.toml`); apply's `run_after_dot-trust` hook pre-trusts harness workspaces and this checkout.
