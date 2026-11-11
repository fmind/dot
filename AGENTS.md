# AGENTS.md (Project)

`fmind/dot` — chezmoi + mise dotfiles for AI-CLI-first, Python-first development on Linux and macOS. User setup, usage, and common tasks live in `README.md`.

## House rules

- **Edit chezmoi sources, never `$HOME`**: `chezmoi apply --force` overwrites managed targets; see [chezmoi](.agents/skills/chezmoi/SKILL.md).
- **Treat this repository as public**: exclude untracked local config values (`~/.config/dot.yaml`, `~/.config/git/config.*`) alongside all private identifiers (`dot_agents/AGENTS.md`).
- **Never commit decrypted secrets**: keep `*.age` encrypted and never write plaintext secrets to sources, diffs, logs, or CLI arguments. Native credentials seed only when absent; scoped keys run via `dot secret run` and preserve account overrides ([Secret Management](README.md#secret-management)).
- **Match validation to the task**: read-only reviews run evidence checks; doc/instruction edits run `mise run check:format` and `check:skills`; behavior edits run focused `pytest` and affected static checks. `mise run doctor` checks local workstation health (`dot`, chezmoi, mise); `mise run check`, `test`, and `all` validate the repo (`all` runs read-only whole-tree gates for cross-cutting, dependency, packaging, or release work; isolate `mise run format` when unrelated edits exist). Reuse passing results while inputs stay unchanged.
- **Parallelize independent CLI probes**: use `run_parallel` (`fmind_dot.process`) for independent subprocess, repo, and tool checks so `dot` stays synchronous with bounded concurrency and deterministic order.
- **Never use sudo**: stay user-space and install via `mise`.
- **Choose global tools for agent coding**: `dot_config/mise/config.toml` holds harnesses, connectors, cross-project agent CLIs, and core shell/review tools (LazyVim, lazygit, lazydocker, macOS Docker stack, Fish, Zellij). Pin project tools per project; add a global tool only when required outside projects (such as LazyVim global formatters/linters), explain why in its comment, and never treat it as a substitute for project pins.
- **Lock tools with mise, never edit generated locks**: use lockfile revision 4 (`dot_config/mise/mise.lock` plus `locks/` graphs; Python locks in `dot/uv.lock`) and never hand-edit or format lockfiles. `mise run lock` resolves the isolated baseline; `mise run lock:tool TOOL...` bumps named global tools (run `mise cache clear` if `mise latest TOOL` is stale); `mise run full` installs with `--locked`.
- **Keep README for users; workflows go in skills**: keep setup, auth, daily usage, and the short task table in `README.md`; put contributor workflows in skills and sync via [repository-docs](skills/repository-docs/SKILL.md).
- **Pin themes and terminal defaults**: [fmind/theme](https://github.com/fmind/theme) owns the palette, app themes, `~/.agents/DESIGN.md`, and `~/.agents/themes/` renderer assets (fetched via `.chezmoiexternal.toml.tmpl` pinned to one commit with SHA-256 checksums; `mise run upgrade` advances it). Merged configs copy only the native theme block with an upstream source comment; TUIs use the Ghostty ANSI palette, GoogleSansCode Nerd Font Mono, and Vim mode wherever supported.

## Workflows

See [common tasks](README.md#repository-tasks); `mise tasks` lists all tasks (`mise run <task>`, or `~/.local/bin/mise`; running from `dot/` resolves root tasks).

- **Iterate**: edit source → run focused checks → `mise run diff` → `mise run apply` when deploying (runs eligible hooks and writes managed files). Lefthook gates commits/pushes; CI runs the full gate.
- **Add or upgrade tools**: project pins follow [mise](skills/mise/SKILL.md); global tools go alphabetically inside their `[tools]` group in `dot_config/mise/config.toml` (backend-prefixed, registry, then per-platform tables) → `mise run lock` → `mise run full`. `mise run upgrade` upgrades only this workstation's deps, tools, theme pin, and plugins; upgrade other repos separately per [upgrade-tools](skills/upgrade-tools/SKILL.md).
- **CLI (`dot`) & workstation**: see [dot-development](.agents/skills/dot-development/SKILL.md) for implementation, tests, and install proof, [dot-cli](skills/dot-cli/SKILL.md) for `dot login`, `setup`, `cache`, `prune`, and workspace commands (apply runs only `dot trust`), and [agent usage](skills/dot-cli/references/agent-usage.md) for stats.
- **Completions**: `mise run completions` installs Fish completions from the deployed CLI; `mise run check:completions` runs outside `all` and gates releases.
- **Skills**: [dot-skills](.agents/skills/dot-skills/SKILL.md) owns catalog links and `check:skills`; [skillify](skills/skillify/SKILL.md) owns authoring and admission.
- **Verify & release**: [dot-verify](.agents/skills/dot-verify/SKILL.md) qualifies the tree without committing; `/dot-release` verifies, commits, pushes, and follows [dot-release](.agents/skills/dot-release/SKILL.md) for `mise run release` and post-release checks.

## Layout

- `dot/`: Python CLI (`fmind_dot`; stdlib `argparse`, Pydantic + PyYAML runtime deps only), repo-only `dot_tasks/`, `uv.lock`, and `pytest` suite.
- `dot_agents/AGENTS.md`: global persona (`~/.agents/AGENTS.md`); `private_dot_gemini/` (agy, primary), `private_dot_claude/`, `private_dot_copilot/`, `dot_config/private_opencode/`, and `private_dot_pi/` adapt host settings and hooks (other host state is gitignored). No custom subagent roles are deployed; see [cross-harness agents](skills/agent-project/references/cross-harness-agents.md).
- `skills/` & `.agents/skills/`: global catalog (linked into `~/.agents/skills/`) and repo-local skills (`.claude/skills` links to `.agents/skills`).
- `.chezmoitemplates/` & `.chezmoiignore`: JSON/JSONC/TOML merge, shell block, skill-catalog, and `dot`-path helpers; `.chezmoiignore` gates repo-only, OS/Crostini-specific (including darwin-only `.docker` and `.zprofile`), and age-key-dependent targets.
- `.github/`: CI, release, security, and dependency automation; `.github/assets/` holds README SVG diagrams.
- Mise trust stays machine-local (`mise trust` or unmanaged `~/.config/mise/conf.d/trust.toml`); apply's `run_after_dot-trust` hook trusts configured workspaces and this checkout in coding harnesses only.
