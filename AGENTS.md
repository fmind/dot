# AGENTS.md (Project)

This is `fmind/dot` — chezmoi + mise dotfiles for AI-CLI-first, Python-first development on Linux and macOS. Setup and install documentation lives in `README.md`.

## House rules

- **Chezmoi**: Edit the source tree in this repository, never deployed copies under `$HOME`; automation always runs `chezmoi apply --force`. Naming, templates, and secrets: [chezmoi skill](.agents/skills/chezmoi/SKILL.md).
- **Validation**: Match checks to the task: read-only reviews need only evidence checks; documentation and instruction edits need relevant formatting, links, and contract checks; behavior changes need focused regression tests and affected static checks. Run `mise run all` for cross-cutting changes, dependencies, packaging, releases, or explicit full qualification. Reuse passing results while relevant inputs remain unchanged. The full gate writes files; isolate it with [git-worktree](skills/git-worktree/SKILL.md) when unrelated work is present. Report the checks run and remaining limits.
- **No-Sudo**: Stay user-space; install via `mise`.
- **Tool baseline**: This repository tracks `latest` by default, including Python; `dot_config/mise/config.toml.tmpl` and `dot_config/mise/mise.lock` own the workstation baseline. Other repositories under `~/fmind`, `~/fmind-ai`, and `~/mlops-courses` pin exact versions from it. [Mise](skills/mise/SKILL.md) owns selection and exceptions; [upgrade-tools](skills/upgrade-tools/SKILL.md) owns validated propagation.
- **Optional tools**: Per-machine `[data].extras` selects managed `dot_config/mise/conf.d/*.local.toml.tmpl` fragments. Their `mise.local.lock` stays host-local; never re-add it to the shared baseline. Setup: [README](README.md#optional-tool-extras); maintenance: [mise task conventions](skills/mise/references/task-conventions.md#optional-workstation-extras).
- **Lockfile compatibility**: Keep the managed global mise lockfile at format 1 while Colab needs `uvx_args` to constrain `jupyter-kernel-client`. Format 2 dependency locking rejects that option; migrate only after qualifying its replacement and tracking all generated sidecars.
- **README Scope**: Keep setup and auth instructions in `README.md`; exclude repository tasks, aliases, and workflows.
- **Secrets**: `*.age` files are encrypted; never modify or commit decrypted versions.
- **Fonts**: Use Google Sans for application text and Google Sans Code for code by default; terminal apps inherit GoogleSansCode Nerd Font Mono from Ghostty. Project-specific requirements take precedence.
- **Theme**: [fmind/theme](https://github.com/fmind/theme) owns the palette and native app files. Fetch standalone themes from upstream `main` via chezmoi externals; when tools require merged styles, copy only the native theme block with an upstream source comment. Terminal tools follow the Ghostty ANSI palette or select terminal-aligned themes.
- **Vim mode**: Enable in every TUI that supports it.

## Workflows

Tasks run via `mise run <task>` (if `mise` is not in `$PATH`, call `~/.local/bin/mise` directly). Invoking tasks from `dot/` resolves to the same root definitions.

Key routines:

- **Iterate**: Edit source → run the relevant checks above → preview the affected chezmoi diff → apply when deployment is in scope. Apply executes eligible installation hooks as well as writing managed files. When committing or pushing is authorized, let enabled hooks run their checks; do not duplicate them immediately beforehand unless needed to diagnose a failure. CI retains the full gate.
- **Documentation**: `mise run check:docs` checks documentation contracts; `mise run check:skills` checks both skill catalogs and their local links. [repository-docs](skills/repository-docs/SKILL.md) owns documentation synchronization.
- **Workstation vs Gate**: `mise run verify` and `mise run doctor` inspect local workstation health; `mise run check`, `test`, and `all` validate the repository.
- **Add tool**: Append to `dot_config/mise/config.toml.tmpl` → `mise run tools` → `mise run lock`.
- **Upgrade tools**: `mise run upgrade` updates this workstation's tools and lockfiles; [upgrade-tools](skills/upgrade-tools/SKILL.md) also inventories and aligns the other local repositories. The task alone does not perform that cross-repository migration.
- **Workstation commands**: `dot login`, `setup`, `cache`, and `prune` own native provider operations; mise owns repository installation and validation. Authentication and cleanup are explicit commands, not apply hooks.
- **Usage statistics**: [agent-usage](skills/agent-usage/SKILL.md) owns reports and subscription configuration. Token totals, API equivalents, recorded cost, and subscription charges are separate measurements; preserve immutable generations when changing extraction.
- **CLI (`dot`)**: Follow [dot-development](.agents/skills/dot-development/SKILL.md) for implementation, tests, and installation proof; [dot-cli](skills/dot-cli/SKILL.md) owns command operation.
- **Manage skills**: Follow [dot-skills](.agents/skills/dot-skills/SKILL.md) for global/local catalog changes and validation; [skillify](skills/skillify/SKILL.md) owns authoring and evidence-based admission. Prefer references under existing owners or project scope; global AGENTS.md + global skill discovery and local AGENTS.md + local skill discovery must each be below 5,000 estimated tokens (characters / 4), excluding on-demand bodies; combined totals are informational. `dot agent context --source . --project . --check` reports global, local, and combined instruction/discovery costs; `mise run report:skills` adds diagnostic routing. Classify roots as connector, task, or collection. Guides own name/description metadata and optional resources; `mise run format:skills` generates parent indexes. Never nest `SKILL.md`; descriptions retain distinctive tool names.
- **Release**: Follow [dot-release](.agents/skills/dot-release/SKILL.md) for `mise run release`, recovery, and publication verification.

## Agents

- **Persona**: `dot_agents/AGENTS.md` deploys to `~/.agents/AGENTS.md`, consumed by all agent harnesses.
- **Skills**: Global packages live in `skills/`; `dot_agents/skills/symlink_<name>.tmpl` links each into the real `~/.agents/skills/` directory. Other packages use the same directory and remain independently managed. Never use `exact_` for the shared catalog.

## Layout

- `.agents/`, `.antigravitycli/`, `.claude/`, and `.gemini/` hold repository-scoped agent state, links, and local skills.
- `.github/` owns CI, release, security, audit, and dependency-update automation.
- `dot/` contains the runtime package, repository-only `dot_tasks/`, uv lock, and pytest suite.
- `dot_agents/` is the shared persona source; `dot_claude/`, `dot_codex/`, `dot_copilot/`, `dot_cursor/`, `dot_gemini/`, and `dot_grok/` adapt it to each host (with OpenCode in `dot_config/opencode/`).
- `dot_config/` contains managed application configuration; root `dot_*` sources map directly to home targets.
- `modify_dot_bashrc` and `modify_dot_profile` update existing shell files; `run_once_*` and `run_onchange_*` run installation hooks during apply.
- `.chezmoiexternal.toml.tmpl` fetches the theme files from `fmind/theme` during apply, while style blocks that must be merged are copied into managed sources.
- `skills/` is the global Agent Skill catalog shared by every supported host.
- `mise.toml`, `mise.lock`, `lefthook.yml`, and scanner configs define the reproducible repository gate.
- `README.md`, `AGENTS.md`, `CHANGELOG.md`, `LICENSE`, and `install.sh` are the root project contracts and entrypoints.
