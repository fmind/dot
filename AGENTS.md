# AGENTS.md (Project)

This is `fmind/dot` — chezmoi + mise dotfiles for AI-CLI-first, Python-first development on Linux and macOS. Setup and install documentation lives in `README.md`.

## House rules

- **Chezmoi**: Edit the source tree in this repository, never deployed copies under `$HOME`; automation always runs `chezmoi apply --force`. Naming, templates, and secrets: [chezmoi skill](.agents/skills/chezmoi/SKILL.md).
- **Gate**: `mise run all` (format + check + test + build) must pass warning-free before reporting a task complete. It writes files; when unrelated work is present, validate an exact isolated candidate using [git-worktree](skills/git-worktree/SKILL.md).
- **No-Sudo**: Stay user-space; install via `mise`.
- **README Scope**: Keep setup and auth instructions in `README.md`; exclude repository tasks, aliases, and workflows.
- **Secrets**: `*.age` files are encrypted; never modify or commit decrypted versions.
- **Theme**: **Tokyo Night (Moon)** is default across every tool that supports theming.
- **Vim mode**: Enable in every TUI that supports it.

## Workflows

Tasks run via `mise run <task>` (if `mise` is not in `$PATH`, call `~/.local/bin/mise` directly). Invoking tasks from `dot/` resolves to the same root definitions.

Key routines:

- **Iterate**: Edit source → validate with `mise run check` (or `mise run all`) → preview with `mise run diff` → `mise run apply` when deployment is in scope. Apply executes eligible installation hooks as well as writing managed files.
- **Documentation**: `mise run check:docs` checks documentation contracts; `mise run check:skills` checks both skill catalogs and their local links. [repository-docs](skills/repository-docs/SKILL.md) owns documentation synchronization.
- **Workstation vs Gate**: `mise run verify` and `mise run doctor` inspect local workstation health; `mise run check`, `test`, and `all` validate the repository.
- **Add tool**: Append to `dot_config/mise/config.toml.tmpl` → `mise run tools` → `mise run lock`.
- **Upgrade tools**: `mise run upgrade` (upgrades tool pins and lockfiles).
- **Workstation commands**: `dot login`, `setup`, `cache`, and `prune` own native provider operations; mise owns repository installation and validation. Authentication and cleanup are explicit commands, not apply hooks.
- **Usage statistics**: [agent-usage](skills/agent-usage/SKILL.md) owns reports and subscription configuration. Token totals, API equivalents, recorded cost, and subscription charges are separate measurements; preserve immutable generations when changing extraction.
- **CLI (`dot`)**: Follow [dot-development](.agents/skills/dot-development/SKILL.md) for implementation, tests, and installation proof; [dot-cli](skills/dot-cli/SKILL.md) owns command operation.
- **Manage skills**: Follow [dot-skills](.agents/skills/dot-skills/SKILL.md) for global/local catalog changes and validation; [skillify](skills/skillify/SKILL.md) owns authoring conventions.
- **Release**: Follow [dot-release](.agents/skills/dot-release/SKILL.md) for `mise run release`, recovery, and publication verification.

## Agents

- **Persona**: `dot_agents/AGENTS.md` deploys to `~/.agents/AGENTS.md`, consumed by all agent harnesses.
- **Skills**: Global packages live in `skills/`; `dot_agents/skills/symlink_<name>.tmpl` links each into the real `~/.agents/skills/` directory. Other packages use the same directory and remain independently managed. Never use `exact_` for the shared catalog.

## Layout

- `.agents/`, `.antigravitycli/`, `.claude/`, and `.gemini/` hold repository-scoped agent state, links, and local skills.
- `.github/` owns CI, release, security, audit, and dependency-update automation.
- `dot/` contains the runtime package, repository-only `dot_tasks/`, uv lock, and pytest suite.
- `dot_agents/` is the shared persona source; `dot_claude/`, `dot_codex/`, `dot_copilot/`, `dot_gemini/`, and `dot_grok/` adapt it to each host (with OpenCode in `dot_config/opencode/`).
- `dot_config/` contains managed application configuration; root `dot_*` sources map directly to home targets.
- `modify_dot_bashrc` and `modify_dot_profile` update existing shell files; `run_once_*` and `run_onchange_*` run installation hooks during apply.
- `skills/` is the global Agent Skill catalog shared by every supported host.
- `mise.toml`, `mise.lock`, `lefthook.yml`, and scanner configs define the reproducible repository gate.
- `README.md`, `AGENTS.md`, `CHANGELOG.md`, `LICENSE`, and `install.sh` are the root project contracts and entrypoints.
