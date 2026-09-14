# AGENTS.md (Project)

This is `fmind/dot` — chezmoi + mise dotfiles for AI-CLI-first, Python-first development on Linux and macOS. Setup and install documentation lives in `README.md`.

## House rules

- **Chezmoi**: Edit the source tree in this repository, never deployed copies under `$HOME`; automation always runs `chezmoi apply --force`. Naming, templates, and secrets: [chezmoi skill](.agents/skills/chezmoi/SKILL.md).
- **Gate**: `mise run all` (format + check + test + build) must pass warning-free before reporting a task complete. It writes files; when unrelated work is present, validate an exact isolated candidate using [git-worktree](skills/git-worktree/SKILL.md).
- **No-Sudo**: Stay user-space; install via `mise`.
- **Tool baseline**: This repository tracks `latest` by default, including Python; `dot_config/mise/config.toml.tmpl` and `dot_config/mise/mise.lock` own the workstation baseline. Other repositories under `~/fmind`, `~/fmind-ai`, and `~/mlops-courses` pin exact versions from it. [Mise](skills/mise/SKILL.md) owns selection and exceptions; [upgrade-tools](skills/upgrade-tools/SKILL.md) owns validated propagation.
- **README Scope**: Keep setup and auth instructions in `README.md`; exclude repository tasks, aliases, and workflows.
- **Secrets**: `*.age` files are encrypted; never modify or commit decrypted versions.
- **Fonts**: Use Google Sans for application text and Google Sans Code for code by default; terminal apps inherit GoogleSansCode Nerd Font Mono from Ghostty. Project-specific requirements take precedence.
- **Theme**: [fmind/theme](https://github.com/fmind/theme) owns the palette and native app files. Use dark syntax on white: charcoal variables, blue keywords/calls, green strings, orange literals/warnings, red errors, grey comments, purple types/builtins and teal information. Bright fills use contrasting labels. Keep upright GoogleSansCode Nerd Font Mono at 14pt in Ghostty and `bold-is-bright = false`.
  - Edit native files in the upstream app folders directly; there is no generator. Run `mise run all` there to validate syntax roles and 4.5:1 text contrast on normal, selected and diff surfaces. See its README for the full palette and custom colors.
  - `.chezmoiexternal.toml.tmpl` follows upstream `main` with fixed `fmind` selection and no host theme data. `mise run apply` uses `chezmoi apply --force --refresh-externals`; other chezmoi commands cache theme downloads for 24 hours.
  - Prefer native remote references or chezmoi externals for standalone theme files. When a tool requires merging styles, copy only its theme block and add a comment linking to the exact upstream file. Fetch standalone themes from upstream `main` through externals.
  - Copy the native Starship, gh-dash, bottom, Lazydocker, LazyGit and Fastfetch blocks into their managed sources; synchronize these snapshots when the upstream palette changes. bat, Yazi, Atuin and lsd theme files are externals. gh-dash uses nested text/background/border mappings. Lazygit uses explicit light selection surfaces. Keep Zellij pane frames enabled so top/bottom bars and panes remain distinct. Fish selects the external k9s skin with `K9S_SKIN=theme`.
  - bat and delta share the native `fmind.tmTheme`; `run_after_bat-theme.sh.tmpl` rebuilds its derived cache after every apply, including refreshed external themes. Terminal-native tools use the matching ANSI palette; do not remap the xterm cube or greyscale ramp. Ghostty sets `minimum-contrast = 1` to preserve the exact selected colours.
  - Antigravity uses `terminal`, Claude Code uses `light-ansi`, and Grok uses `grokday`. Native Neovim/lualine, Zellij, OpenCode, Fish, fzf and ptpython mappings own their foregrounds and surfaces. README screenshots are recorded locally from synthetic inputs; no generated preview website remains.
- **Vim mode**: Enable in every TUI that supports it.

## Workflows

Tasks run via `mise run <task>` (if `mise` is not in `$PATH`, call `~/.local/bin/mise` directly). Invoking tasks from `dot/` resolves to the same root definitions.

Key routines:

- **Iterate**: Edit source → validate with `mise run check` (or `mise run all`) → preview with `mise run diff` → `mise run apply` when deployment is in scope. Apply executes eligible installation hooks as well as writing managed files.
- **Documentation**: `mise run check:docs` checks documentation contracts; `mise run check:skills` checks both skill catalogs and their local links. [repository-docs](skills/repository-docs/SKILL.md) owns documentation synchronization.
- **Workstation vs Gate**: `mise run verify` and `mise run doctor` inspect local workstation health; `mise run check`, `test`, and `all` validate the repository.
- **Add tool**: Append to `dot_config/mise/config.toml.tmpl` → `mise run tools` → `mise run lock`.
- **Upgrade tools**: `mise run upgrade` updates this workstation's tools and lockfiles; [upgrade-tools](skills/upgrade-tools/SKILL.md) also inventories and aligns the other local repositories. The task alone does not perform that cross-repository migration.
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
- `dot_agents/` is the shared persona source; `dot_claude/`, `dot_codex/`, `dot_copilot/`, `dot_cursor/`, `dot_gemini/`, and `dot_grok/` adapt it to each host (with OpenCode in `dot_config/opencode/`).
- `dot_config/` contains managed application configuration; root `dot_*` sources map directly to home targets.
- `modify_dot_bashrc` and `modify_dot_profile` update existing shell files; `run_once_*` and `run_onchange_*` run installation hooks during apply.
- `.chezmoiexternal.toml.tmpl` fetches the theme files from `fmind/theme` during apply, while style blocks that must be merged are copied into managed sources.
- `skills/` is the global Agent Skill catalog shared by every supported host.
- `mise.toml`, `mise.lock`, `lefthook.yml`, and scanner configs define the reproducible repository gate.
- `README.md`, `AGENTS.md`, `CHANGELOG.md`, `LICENSE`, and `install.sh` are the root project contracts and entrypoints.
