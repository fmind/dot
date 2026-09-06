# AGENTS.md (Project)

This is `fmind/dot` — a chezmoi + mise dotfiles repo for **AI-CLI-first, Python-first** development on Linux and macOS.

User-facing install and usage docs live in `README.md`; this file is for agents working inside the repo.

## House rules

- **Chezmoi**: Edit the source tree (this repository), never deployed copies under `$HOME`; automation always runs `chezmoi apply --force` so a prompt can never block. Naming, templates, and secrets: [chezmoi skill](.agents/skills/chezmoi/SKILL.md).
- **Config Documentation**: On formats supporting comments (TOML, YAML, fish, Lua, KDL), include the official documentation link at the top of the file (e.g. `# Docs: <url>`, placed immediately below any schema directive); never add comments to strict JSON.
- **GitHub Access**: Use `gh` CLI for repository, issue, and PR operations.
- **Git Push to Main**: Direct commit/push to `main` branch is permitted (no feature branch required).
- **Lint-before-done**: `mise run all` (format + check + test + build, the same gate CI runs) must pass before reporting a task complete.
- **Markdown Lists**: Only use `1.` for all numbered list items in markdown files to ensure correct dynamic rendering.
- **No-Hard-Wrap**: Every `*.md` keeps each paragraph on a single line.
- **No-Sudo**: Stay user-space; install via `mise`.
- **README Scope**: Keep setup/auth instructions in `README.md`; exclude repository tasks, aliases, and workflows.
- **Secrets**: `*.age` files are encrypted; never modify or commit decrypted versions.
- **Theme**: **Tokyo Night (Moon)** is default across every tool that supports theming.
- **Vim mode**: Enable in every TUI that supports it.

## Workflows

Tasks run via `mise run <task>`. **Do not use `mr`** — it is an interactive-only fish abbreviation.

The root `mise.toml` owns every repository task; invoking a task from `dot/` resolves to the same definition and build output. Commits run validation hooks without deploying; use `mise run deploy` explicitly to install the current CLI.

Aliases split into two namespaces so a mistyped letter can never fire the wrong kind of task:

- **Common tasks** take the canonical one-letter alias from the mise skill: `a` all, `b` build, `c` check, `f` format, `i` install, `t` test, `w` watch (plus `c*`/`f*` for subtasks, e.g. `cp` check:python, `fd` format:dprint).
- **Project management** tasks take an `m`-prefixed alias: `ma` apply, `md` diff, `me` deploy, `mf` full, `mg` completions, `mh` hooks, `mk` lock, `mo` doctor, `mp` prune, `mr` release, `mt` tools, `mtr` trust, `mu` upgrade, `mv` vim, `mx` verify.

Key routines:

- **First-time setup**: `mise run install` (trust → tools → hooks → vim).
- **Routine update**: `mise run full` (synchronize environment).
- **Iterate**: Edit source → `mise run apply` (`mise run diff` to preview) → `mise run check` (or `mise run all`) → `mise run verify`.
- **Add tool**: Append to `dot_config/mise/config.toml.tmpl` → `mise run tools` → `mise run lock`.
- **Upgrade tools**: `mise run upgrade` (upgrades tool pins and lockfiles).
- **Reclaim disk**: `mise run prune` (reclaim development caches and agent transcripts).
- **Release**: `mise run release` (runs validation, tags, pushes `main` and tag).
- **Manage skills**: Author global skills directly under `skills/` (repo-scoped ones under `.agents/skills/`) with the `skillify` skill and the limits in `dot_agents/AGENTS.md`; register each in `skills/contracts.json`, add a routing probe in `dot/testdata/skills/routing-boundaries.json`, and validate with `mise run check:skills` plus `mise run test`.
- **Create visuals**: Use `fmind-visuals` skill (Typst for decks, Mermaid or D2 for diagrams).

Validation includes Fish and rendered shell syntax, Ruff, ty, pytest coverage, packaging checks, repository contracts, security scans, the Python CLI integration suite, and a disposable-home bootstrap test. CI runs the canonical `mise run all` gate on Linux. `mise run test:starters` separately materializes and executes the reusable Python CLI starter because that slower smoke test is opt-in.

Skill validation enforces package structure, metadata, links, required tools, and fixture consistency. `mise run report:skills` shows word-overlap rankings as an editing aid; prose wording and ranking scores do not gate changes or prove host behavior.

Keep repository checks distinct from workstation checks: `mise run verify` inspects local authentication and installation, while `mise run doctor` checks chezmoi and mise health. `check:tools` validates repository task definitions only. `mise run check:vuln:tools` audits every installed npm and pipx version separately; the repository dependency scan includes development dependencies but does not cover those global tool environments.

> Note: If `mise` fails with `command not found` in an agent shell, call `~/.local/bin/mise` directly.

The unified typed Python `dot` CLI lives in `dot/src/fmind_dot/`; `mise run build` creates its wheel and source distribution, while `mise run deploy` stages a dedicated environment and installs the exact hash-verified runtime graph before switching the local entrypoint. Every command and alias is documented once in [`skills/dot-cli/SKILL.md`](skills/dot-cli/SKILL.md), with the `dot prune` flag matrix in [`references/prune-flags.md`](skills/dot-cli/references/prune-flags.md); `dot <command> --help` remains authoritative for the complete flag list.

Agent registration and hook normalization live in `dot/src/fmind_dot/agent.py` and `agent_parsers.py`; SQLite persistence, query, and usage aggregation live in the corresponding Python modules. All sync paths share that registry and validate sources before persistence.

`dot agent doctor` limits each store scan to `agent.doctor.scan_limit` (4096 files by default). A `truncated=true` result means the scan cannot establish full health; raise that setting in a temporary `--config` file for a larger read-only audit.

## Agents

Two assets are authored once and consumed by all agent CLIs:

- **Persona** — `dot_agents/AGENTS.md` deploys to `~/.agents/AGENTS.md`, symlinked in by Antigravity, Claude, Codex, Copilot, and Grok.
- **Skills** — `skills/` is symlinked to `~/.agents/skills/`.

**Rule: every global skill lives in `skills/`.**

## Layout

- `.agents/`, `.antigravitycli/`, `.claude/`, and `.gemini/` hold repository-scoped agent state, links, and local skills.
- `.github/` owns CI, release, security, audit, and dependency-update automation.
- `dot/` contains the Python package, CLI modules, uv lock, and pytest suite.
- `dot_agents/` is the shared persona source; `dot_claude/`, `dot_codex/`, `dot_copilot/`, `dot_gemini/`, and `dot_grok/` adapt it to each host.
- `dot_config/` contains managed application configuration; `dot_kube/` and the other root `dot_*` sources map directly to home targets.
- `modify_dot_bashrc`, `modify_dot_profile`, and `run_once_*` integrate with files or installation events that chezmoi cannot own wholesale.
- `skills/` is the global Agent Skill catalog shared by every supported host.
- `mise.toml`, `mise.lock`, `lefthook.yml`, and the root formatter or scanner configs define the reproducible repository gate.
- `README.md`, `AGENTS.md`, `CHANGELOG.md`, `LICENSE`, and `install.sh` are the human contract, agent contract, release record, license, and bootstrap entrypoint.
