# AGENTS.md (Project)

This is `fmind/dot` — chezmoi + mise dotfiles for AI-CLI-first, Python-first development on Linux and macOS. Setup, usage, and common tasks live in `README.md`.

## House rules

- **Edit chezmoi sources, never deployed copies**: change this repository, not files under `$HOME`; automation runs `chezmoi apply --force`. Naming, templates, and secrets: [chezmoi skill](.agents/skills/chezmoi/SKILL.md).
- **Treat this repository as public — never leak information**: Never put customer or employer names, domains, emails, project or account IDs, repo or service names, hostnames, local paths, or details from untracked configs (`~/.config/dot.yaml`, `~/.config/git/config.*`). Use only synthetic fixtures on `fmind.dev`, `fmind.ai`, or RFC 2606 domains (`@example.com`, `@example.test`).
- **Never commit decrypted secrets**: `*.age` files stay encrypted; never write plaintext secrets to the source tree, diffs, logs, or command arguments. Native credentials are create-only seeds; scoped keys use `dot secret run` and preserve account overrides ([Secret Management](README.md#secret-management)).
- **Match validation to the task**: read-only reviews need only evidence checks; doc and instruction edits need formatting, link, and contract checks (`mise run check:skills`); behavior changes need focused pytest runs and affected static checks. `mise run doctor` checks local workstation health (`dot`, chezmoi, and mise); `mise run check`, `test`, and `all` validate the repository (`all` runs whole-tree gates without rewriting files, while `mise run format` writes the tree — isolate formatting when unrelated edits are present; run `all` for cross-cutting changes, dependencies, packaging, releases, or full qualification). Reuse passing results while inputs remain unchanged.
- **Parallelize independent CLI probes**: use `run_parallel` (`fmind_dot.process`) for independent subprocess, repository, and tool checks so `dot` stays synchronous while bounding concurrent I/O and preserving deterministic output order.
- **Never use sudo**: stay user-space; install via `mise`.
- **Choose global tools for agent coding**: `dot_config/mise/config.toml` serves AI-agent coding (harnesses, service connectors, and cross-project CLIs agents run), plus a few human review/shell tools (LazyVim, lazygit, lazydocker, the macOS Docker stack, Fish, Zellij). Pin project tools in their project; keep one global only when it must work outside projects (such as formatters and linters LazyVim runs on any file) and state why in its comment; a global copy never replaces a project pin.
- **Lock tools with mise, never edit generated locks**: use mise lockfile revision 3 and keep `dot_config/mise/mise.lock` with its referenced `locks/` dependency graphs; never hand-edit or format generated locks. `mise run lock` resolves the portable baseline in isolation; `mise run full` installs with `--locked`; Python dependencies lock in `dot/uv.lock`.
- **Keep README for users; workflows go in skills**: keep setup, auth, everyday usage, and the short task table in `README.md`; put contributor workflows in skills and sync docs via [repository-docs](skills/repository-docs/SKILL.md).
- **Pin themes and terminal defaults**: [fmind/theme](https://github.com/fmind/theme) owns the palette, native app files, and `~/.agents/DESIGN.md`. Fetch standalone themes via `.chezmoiexternal.toml.tmpl` pinned to one commit with SHA-256 checksums (`mise run upgrade` advances the pin); when tools require merged styles, copy only the native theme block with an upstream source comment. Terminal tools follow the Ghostty ANSI palette, inherit GoogleSansCode Nerd Font Mono from Ghostty, and enable Vim mode in every TUI that supports it.

## Workflows

See [common tasks](README.md#repository-tasks); `mise tasks` lists all tasks and aliases (`mise run <task>`, or `~/.local/bin/mise` if not in `$PATH`; running from `dot/` resolves to the root tasks).

- **Iterate**: edit source → run focused checks → `mise run diff` → `mise run apply` when deployment is in scope (runs eligible hooks and writes managed files). Lefthook runs commit/push checks; CI runs the full gate.
- **Add or upgrade tools**: for project pins see [mise](skills/mise/SKILL.md); for global tools insert into `[tools]` in `dot_config/mise/config.toml` alphabetically within its group (backend-prefixed entries, registry names, then per-platform tables) → `mise run lock` → `mise run full`. `mise run upgrade` upgrades this workstation's dependencies, tools, theme pin, and plugins only; upgrade other repos separately per [upgrade-tools](skills/upgrade-tools/SKILL.md).
- **CLI (`dot`) & workstation**: follow [dot-development](.agents/skills/dot-development/SKILL.md) for implementation, tests, and installation proof, [dot-cli](skills/dot-cli/SKILL.md) for `dot login`, `setup`, `cache`, `prune`, and workspace commands (explicit commands, never apply hooks), and [agent-usage](skills/agent-usage/SKILL.md) for usage reports.
- **Completions**: `mise run completions` installs Fish completions from the deployed CLI; `mise run check:completions` runs outside `all` and gates releases.
- **Skills**: [dot-skills](.agents/skills/dot-skills/SKILL.md) owns catalog changes, links, and `check:skills`; [skillify](skills/skillify/SKILL.md) owns authoring and admission.
- **Verify & release**: [dot-verify](.agents/skills/dot-verify/SKILL.md) qualifies the checkout without committing; `/dot-release` runs dot-verify, commits, pushes, and follows [dot-release](.agents/skills/dot-release/SKILL.md) for `mise run release` and publication checks.

## Layout

- `dot/`: Python CLI package (`fmind_dot`), repo-only `dot_tasks/`, `uv.lock`, and `pytest` suite.
- `dot_agents/AGENTS.md`: global persona deployed to `~/.agents/AGENTS.md` for all harnesses; `dot_gemini/` (agy, primary), `dot_claude/`, `dot_copilot/`, and `dot_config/opencode/` adapt it per host (other host state is gitignored). No custom subagent roles are deployed; see [cross-harness agents](skills/agent-project/references/cross-harness-agents.md).
- `skills/` & `.agents/skills/`: global catalog (linked into `~/.agents/skills/`) and repo-local skills (`.claude/skills` links to `.agents/skills`).
- `.chezmoitemplates/` & `.chezmoiignore`: JSON/TOML merge, shell block, skill-catalog, and `dot`-path helpers; `.chezmoiignore` gates repo-only, OS/Crostini-specific (including darwin-only `.docker` and `.zprofile`), and age-key-dependent targets.
- `.github/`: CI, release, security, and dependency automation; `.github/assets/` holds the README's SVG diagrams.
- Mise trust stays machine-local (`mise trust` or unmanaged `~/.config/mise/conf.d/trust.toml`); apply's `run_after_dot-trust` hook pre-trusts configured workspaces and this checkout in the coding harnesses, not in mise.
