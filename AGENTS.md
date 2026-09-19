# AGENTS.md (Project)

This is `fmind/dot` — chezmoi + mise dotfiles for AI-CLI-first, Python-first development on Linux and macOS. Setup and install documentation lives in `README.md`.

## House rules

- **Chezmoi**: Edit the source tree in this repository, never deployed copies under `$HOME`; automation always runs `chezmoi apply --force`. Naming, templates, and secrets: [chezmoi skill](.agents/skills/chezmoi/SKILL.md).
- **Validation**: Match checks to the task: read-only reviews need only evidence checks; documentation and instruction edits need relevant formatting, links, and contract checks; behavior changes need focused regression tests and affected static checks. Run `mise run all` for cross-cutting changes, dependencies, packaging, releases, or explicit full qualification. Reuse passing results while relevant inputs remain unchanged.
- **Secrets**: `*.age` files are encrypted; never modify or commit decrypted versions.
- **No-Sudo**: Stay user-space; install via `mise`.
- **Tool baseline**: This repository tracks `latest` by default, including Python; `dot_config/mise/config.toml.tmpl` and `dot_config/mise/mise.lock` own the workstation baseline. Other repositories under `~/fmind`, `~/fmind-ai`, and `~/mlops-courses` pin exact versions from it. [Mise](skills/mise/SKILL.md) owns selection and exceptions; [upgrade-tools](skills/upgrade-tools/SKILL.md) owns validated propagation.
- **Dependency locks**: Keep the global mise lockfile at format 1 for version-only npm/pipx installs; do not upgrade its format. The repository lockfile may use format 2 for native tools. npm/pipx entries lock the version only; transitive dependencies can drift on reinstall. Preserve the Colab and pgcli `with` requirements. `mise run lock` captures the shared global lockfile. Python application dependencies remain locked in `dot/uv.lock`.
- **README Scope**: Keep setup and auth instructions in `README.md`; exclude repository tasks, aliases, and workflows.
- **Theme**: [fmind/theme](https://github.com/fmind/theme) owns the palette and native app files. Fetch standalone themes from upstream `main` via chezmoi externals; when tools require merged styles, copy only the native theme block with an upstream source comment. Terminal tools follow the Ghostty ANSI palette or select terminal-aligned themes.
- **Fonts**: Terminal apps inherit GoogleSansCode Nerd Font Mono from Ghostty.
- **Vim mode**: Enable in every TUI that supports it.

## Workflows

Tasks run via `mise run <task>` (if `mise` is not in `$PATH`, call `~/.local/bin/mise` directly). Invoking tasks from `dot/` resolves to the same root definitions.

Key routines:

- **Iterate**: Edit source → run the relevant checks above → preview the affected chezmoi diff → apply when deployment is in scope. Apply executes eligible installation hooks as well as writing managed files. Lefthook runs commit/push checks; pre-run them only to diagnose a failure. CI retains the full gate.
- **Documentation**: `mise run check:docs` checks documentation contracts; `mise run check:skills` checks both skill catalogs and their local links. [repository-docs](skills/repository-docs/SKILL.md) owns documentation synchronization.
- **Workstation vs Gate**: `mise run verify` and `mise run doctor` inspect local workstation health; `mise run check`, `test`, and `all` validate the repository.
- **Add tool**: Insert into `[tools]` in `dot_config/mise/config.toml.tmpl`, alphabetically within its group (backend-prefixed entries, registry names, then per-platform tables) → `chezmoi apply --force ~/.config/mise` → `mise run lock` → `mise run tools`.
- **Upgrade tools**: `mise run upgrade` updates this workstation's tools and lockfiles; [upgrade-tools](skills/upgrade-tools/SKILL.md) also inventories and aligns the other local repositories. The task alone does not perform that cross-repository migration.
- **Workstation commands**: `dot login`, `setup`, `cache`, and `prune` own native provider operations; mise owns repository installation and validation. Authentication and cleanup are explicit commands, not apply hooks.
- **Usage statistics**: [agent-usage](skills/agent-usage/SKILL.md) owns reports and subscription configuration. Token totals, API equivalents, recorded cost, and subscription charges are separate measurements; preserve immutable generations when changing extraction.
- **CLI (`dot`)**: Follow [dot-development](.agents/skills/dot-development/SKILL.md) for implementation, tests, and installation proof; [dot-cli](skills/dot-cli/SKILL.md) owns command operation.
- **Manage skills**: [dot-skills](.agents/skills/dot-skills/SKILL.md) owns catalog changes and validation; [skillify](skills/skillify/SKILL.md) owns authoring and admission. Each scope (AGENTS.md + skill discovery: names, descriptions, and paths) stays below 5,000 estimated tokens (characters / 4, rounded up); on-demand bodies and host/plugin catalogs are not measured, and combined totals are informational. `dot agent context --source . --project . --check` measures both scopes; `mise run report:skills` adds routing diagnostics; `mise run format:skills` regenerates parent indexes. Never nest `SKILL.md`.
- **Completions**: Run `mise run check:completions` before release on the configured workstation; it validates active generators and Fish syntax in temporary directories. This host-dependent check is separate from `all`; inactive optional tools are skipped. `mise run completions` installs the scripts using the deployed CLI.
- **Release**: Follow [dot-release](.agents/skills/dot-release/SKILL.md) for `mise run release`, recovery, and publication verification.

## Agents

- **Persona**: `dot_agents/AGENTS.md` deploys to `~/.agents/AGENTS.md`, consumed by all agent harnesses.
- **Skills**: Global packages live in `skills/`; `dot_agents/skills/symlink_<name>.tmpl` links each into the real `~/.agents/skills/` directory. Other packages use the same directory and remain independently managed. Never use `exact_` for the shared catalog.

## Layout

- `.agents/skills/` holds local skills; `.claude/skills` links to it. Other host state is gitignored.
- `.github/` owns CI, release, security, audit, and dependency-update automation.
- `dot/` contains the runtime package, repository-only `dot_tasks/`, uv lock, and pytest suite.
- `dot_agents/` is the shared persona source; `dot_claude/`, `dot_codex/`, `dot_copilot/`, `dot_gemini/`, and `dot_grok/` adapt it to each host (with OpenCode in `dot_config/opencode/`).
- `dot_config/` contains managed application configuration; root `dot_*` sources map directly to home targets.
- `modify_dot_bashrc`, `modify_dot_profile`, and darwin-only `modify_dot_zprofile` add PATH and mise activation to existing shell files; `run_once_after_*` install Grok and Antigravity; `run_after_bat-theme` rebuilds the bat theme cache when the theme or bat changes.
- `.chezmoiexternal.toml.tmpl` fetches the theme files from `fmind/theme` during apply, while style blocks that must be merged are copied into managed sources.
- `skills/` is the global Agent Skill catalog shared by every supported host.
