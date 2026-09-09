# AGENTS.md (Project)

This is `fmind/dot` — chezmoi + mise dotfiles for AI-CLI-first, Python-first development on Linux and macOS. Setup and install documentation lives in `README.md`.

## House rules

- **Chezmoi**: Edit the source tree in this repository, never deployed copies under `$HOME`; automation always runs `chezmoi apply --force`. Naming, templates, and secrets: [chezmoi skill](.agents/skills/chezmoi/SKILL.md).
- **Gate**: `mise run all` (format + check + test + build) must pass warning-free before reporting a task complete.
- **No-Sudo**: Stay user-space; install via `mise`.
- **README Scope**: Keep setup and auth instructions in `README.md`; exclude repository tasks, aliases, and workflows.
- **Secrets**: `*.age` files are encrypted; never modify or commit decrypted versions.
- **Theme**: **Tokyo Night (Moon)** is default across every tool that supports theming.
- **Vim mode**: Enable in every TUI that supports it.

## Workflows

Tasks run via `mise run <task>` (if `mise` is not in `$PATH`, call `~/.local/bin/mise` directly). Invoking tasks from `dot/` resolves to the same root definitions.

Key routines:

- **Iterate**: Edit source → `mise run apply` (`mise run diff` to preview) → `mise run check` (or `mise run all`).
- **Workstation vs Gate**: `mise run verify` and `mise run doctor` inspect local workstation health; `mise run check`, `test`, and `all` validate the repository.
- **Add tool**: Append to `dot_config/mise/config.toml.tmpl` → `mise run tools` → `mise run lock`.
- **Upgrade tools**: `mise run upgrade` (upgrades tool pins and lockfiles).
- **CLI (`dot`)**: Python package in `dot/src/fmind_dot/`; `mise run build` creates distributions, `mise run deploy` installs to `~/.local/bin/dot`. Operational docs: [`skills/dot-cli/SKILL.md`](skills/dot-cli/SKILL.md).
- **Manage skills**: Follow [skillify](skills/skillify/SKILL.md) for authoring and catalog rules. Global skills live in `skills/` (repo-scoped in `.agents/skills/`); register in `skills/contracts.json`, add a routing probe in `dot/testdata/skills/routing-boundaries.json`, and validate with `mise run check:skills` plus `mise run test`.
- **Release**: `mise run release` (runs validation, tags, and pushes).

## Agents

- **Persona**: `dot_agents/AGENTS.md` deploys to `~/.agents/AGENTS.md`, consumed by all agent harnesses.
- **Skills**: `skills/` deploys to `~/.agents/skills/`. Rule: every global skill lives in `skills/`.

## Layout

- `.agents/`, `.antigravitycli/`, `.claude/`, and `.gemini/` hold repository-scoped agent state, links, and local skills.
- `.github/` owns CI, release, security, audit, and dependency-update automation.
- `dot/` contains the Python package, CLI modules, uv lock, and pytest suite.
- `dot_agents/` is the shared persona source; `dot_claude/`, `dot_codex/`, `dot_copilot/`, `dot_gemini/`, and `dot_grok/` adapt it to each host (with OpenCode in `dot_config/opencode/`).
- `dot_config/` contains managed application configuration; root `dot_*` sources map directly to home targets.
- `modify_dot_bashrc`, `modify_dot_profile`, and `run_once_*` integrate with files or installation events that chezmoi cannot own wholesale.
- `skills/` is the global Agent Skill catalog shared by every supported host.
- `mise.toml`, `mise.lock`, `lefthook.yml`, and scanner configs define the reproducible repository gate.
- `README.md`, `AGENTS.md`, `CHANGELOG.md`, `LICENSE`, and `install.sh` are the root project contracts and entrypoints.
