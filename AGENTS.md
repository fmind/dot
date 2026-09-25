# AGENTS.md (Project)

This is `fmind/dot` — chezmoi + mise dotfiles for AI-CLI-first, Python-first development on Linux and macOS. Setup, usage, and common tasks live in `README.md`.

## House rules

- **Chezmoi**: Edit the source tree in this repository, never deployed copies under `$HOME`; automation always runs `chezmoi apply --force`. Naming, templates, and secrets: [chezmoi skill](.agents/skills/chezmoi/SKILL.md).
- **Validation**: Match checks to the task: read-only reviews need only evidence checks; documentation and instruction edits need relevant formatting, links, and contract checks; behavior changes need focused regression tests and affected static checks. Run `mise run all` for cross-cutting changes, dependencies, packaging, releases, or explicit full qualification. Reuse passing results while relevant inputs remain unchanged.
- **Secrets**: `*.age` files are encrypted; never modify or commit decrypted versions. Native credentials are create-only seeds; scoped keys use `dot secret run`. Preserve account overrides and keep values out of diff/log output; [Secret Management](README.md#secret-management) owns setup and migration.
- **No-Sudo**: Stay user-space; install via `mise`.
- **Tool baseline**: This repository tracks `latest` by default, including Python; `dot_config/mise/config.toml.tmpl` and `dot_config/mise/mise.lock` own the workstation baseline. Other repositories under `~/fmind`, `~/fmind-ai`, and `~/mlops-courses` pin exact versions from it. [Mise](skills/mise/SKILL.md) owns selection and exceptions; [upgrade-tools](skills/upgrade-tools/SKILL.md) owns validated propagation.
- **Dependency locks**: Use mise format 2 for reproducible tool installs. Keep the global lockfile and its referenced native dependency files together; do not edit or format generated files. Preserve the pgcli `with` requirement. `mise run lock` resolves the portable source baseline in isolation and captures its complete bundle; `mise run tools` installs with `--locked`. Python application dependencies remain locked in `dot/uv.lock`.
- **README Scope**: Keep setup, auth, everyday usage, and a short task reference in `README.md`; keep detailed contributor workflows in skills.
- **Theme**: [fmind/theme](https://github.com/fmind/theme) owns the palette and native app files. Fetch standalone themes from upstream `main` via chezmoi externals; when tools require merged styles, copy only the native theme block with an upstream source comment. Terminal tools follow the Ghostty ANSI palette or select terminal-aligned themes.
- **Fonts**: Terminal apps inherit GoogleSansCode Nerd Font Mono from Ghostty.
- **Vim mode**: Enable in every TUI that supports it.

## Workflows

See [common tasks](README.md#repository-tasks); `mise tasks` lists all tasks and aliases. Tasks run via `mise run <task>` (if `mise` is not in `$PATH`, call `~/.local/bin/mise` directly). Invoking tasks from `dot/` resolves to the same root definitions.

Key routines:

- **Iterate**: Edit source → run the relevant checks above → preview the affected chezmoi diff → apply when deployment is in scope. Apply executes eligible installation hooks as well as writing managed files. Lefthook runs commit/push checks; pre-run them only to diagnose a failure. CI retains the full gate.
- **Documentation**: `mise run check:docs` checks documentation contracts; `mise run check:skills` checks both skill catalogs and their local links. [repository-docs](skills/repository-docs/SKILL.md) owns documentation synchronization.
- **Workstation vs Gate**: `mise run verify` and `mise run doctor` inspect local workstation health; `mise run check`, `test`, and `all` validate the repository. `all` also formats files; isolate it when unrelated edits are present.
- **Add tool**: Insert into `[tools]` in `dot_config/mise/config.toml.tmpl`, alphabetically within its group (backend-prefixed entries, registry names, then per-platform tables) → `chezmoi apply --force ~/.config/mise` → `mise run lock` → `mise run tools`.
- **Upgrade tools**: `mise run upgrade` updates this workstation's tools and lockfiles; [upgrade-tools](skills/upgrade-tools/SKILL.md) also inventories and aligns the other local repositories. The task alone does not perform that cross-repository migration.
- **Workstation commands**: `dot login`, `setup`, `cache`, and `prune` own native provider operations; mise owns repository installation and validation. Authentication and cleanup are explicit commands, not apply hooks.
- **Usage statistics**: [agent-usage](skills/agent-usage/SKILL.md) owns reports and subscription configuration. Token totals, API equivalents, recorded cost, and subscription charges are separate measurements; never let a failed extraction replace an archived measurement.
- **CLI (`dot`)**: Follow [dot-development](.agents/skills/dot-development/SKILL.md) for implementation, tests, and installation proof; [dot-cli](skills/dot-cli/SKILL.md) owns command operation.
- **Manage skills**: [dot-skills](.agents/skills/dot-skills/SKILL.md) owns catalog changes and validation; [skillify](skills/skillify/SKILL.md) owns authoring and admission. dot-skills owns the 5,000-token scope budget and its checks; `mise run format:skills` regenerates parent indexes. Never nest `SKILL.md`.
- **Completions**: Run `mise run check:completions` before release on the configured workstation; it validates active generators and Fish syntax in temporary directories. This host-dependent check is separate from `all`; inactive optional tools are skipped. `mise run completions` installs the scripts using the deployed CLI.
- **Verify**: [dot-verify](.agents/skills/dot-verify/SKILL.md) qualifies the checkout (review, docs sync, all gates, CLI smoke tests) without committing.
- **Release**: `/dot-release` runs dot-verify, commits, pushes, then follows [dot-release](.agents/skills/dot-release/SKILL.md) for `mise run release`, recovery, and publication verification.

## Agents

- **Persona**: `dot_agents/AGENTS.md` deploys to `~/.agents/AGENTS.md`, consumed by all agent harnesses.
- **Skills**: Global packages live in `skills/`; `dot_agents/skills/symlink_<name>.tmpl` links each into the real `~/.agents/skills/` directory. Other packages use the same directory and remain independently managed. Never use `exact_` for the shared catalog.

## Layout

- `.agents/skills/` holds local skills; `.claude/skills` links to it. Other host state is gitignored.
- `.github/` owns CI, release, security, audit, and dependency-update automation.
- `dot/` contains the runtime package, repository-only `dot_tasks/`, uv lock, and pytest suite.
- `dot_agents/` is the shared persona source; `dot_claude/`, `dot_codex/`, `dot_copilot/`, `dot_gemini/`, and `dot_grok/` adapt it to each host (with OpenCode in `dot_config/opencode/`).
- Every root `dot_*` or `private_dot_*` source maps to its home target (`dot_config/` holds application configuration); `.chezmoitemplates/` holds the shared JSON/TOML merge, skill-catalog, and hook `dot`-path helpers used by modify and hook templates.
- `modify_dot_bashrc`, `modify_dot_profile`, and darwin-only `modify_dot_zprofile` add PATH and mise activation to existing shell files; `run_once_after_*` install Grok and Antigravity; `run_after_bat-theme` rebuilds the bat theme cache when the theme or bat changes.
- `run_after_dot-trust` runs `dot trust all` and `dot trust <sourceDir>` so every harness trusts the configured workspaces, their owner-allowlisted repositories, and this checkout. Mise trust is machine-local (`mise trust` or unmanaged `~/.config/mise/conf.d/trust.toml`).
- `.chezmoiexternal.toml.tmpl` fetches the theme files from `fmind/theme` during apply, while style blocks that must be merged are copied into managed sources.
- `skills/` is the global Agent Skill catalog shared by every supported host.
