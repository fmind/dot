# AGENTS.md (Project)

`fmind/dot` — chezmoi + mise dotfiles for AI-CLI-first, Python-first development on Linux and macOS. User setup, auth, and common tasks live in `README.md`.

## House rules

- **Edit chezmoi sources, never `$HOME`**: `chezmoi apply --force` overwrites managed targets ([chezmoi](.agents/skills/chezmoi/SKILL.md)).
- **Public repo, zero private data or plaintext secrets**: exclude local config (`~/.config/dot.yaml`, `~/.config/git/config.*`) and private identifiers; keep `*.age` encrypted, seed native creds only when absent, and run scoped keys via `dot secret run` ([Secret Management](README.md#secret-management)).
- **Match validation to the task**: read-only reviews run evidence checks; doc/skill edits run `mise run check:format` and `check:skills`; code edits run focused `pytest` and affected static checks (isolate `mise run format` when unrelated edits exist; reuse unchanged results). `doctor` checks workstation health; `check`, `test`, and `all` validate the repo.
- **Stay user-space and parallelize probes**: never use `sudo` (install via `mise`); use `run_parallel` (`fmind_dot.process`) for independent subprocess, repo, and tool checks.
- **Global tools and generated locks**: `dot_config/mise/config.toml` holds harnesses, connectors, cross-project agent CLIs, and core shell/editor tools (with a reason comment when required outside projects — never a substitute for project pins). Never hand-edit or format lockfiles (`dot_config/mise/mise.lock` + `locks/` rev 4, `dot/uv.lock`); use `mise run lock` / `lock:tool TOOL...` (`mise cache clear` if stale) and `mise run full` ([mise](skills/mise/SKILL.md)).
- **Docs and theme pins**: keep `README.md` user-facing and put contributor workflows in skills ([repository-docs](skills/repository-docs/SKILL.md)). [fmind/theme](https://github.com/fmind/theme) owns palette, app themes, `~/.agents/DESIGN.md`, and `~/.agents/themes/` (pinned in `.chezmoiexternal.toml.tmpl`; Ghostty ANSI, GoogleSansCode Nerd Font Mono, and Vim mode across TUIs).

## Workflows

See [common tasks](README.md#repository-tasks) (`mise tasks` lists all; running from `dot/` resolves root tasks).

- **Iterate**: edit source → focused checks → `mise run diff` → `mise run apply` (writes targets and runs `dot trust`). Lefthook gates commits/pushes; CI runs the full gate.
- **Tools & upgrades**: alphabetize global tools inside their `[tools]` group in `dot_config/mise/config.toml` → `mise run lock` → `mise run full`. `mise run upgrade` updates only this workstation; upgrade other repos via [upgrade-tools](skills/upgrade-tools/SKILL.md).
- **CLI (`dot`) & completions**: see [dot-development](.agents/skills/dot-development/SKILL.md) (code/tests/deploy), [dot-cli](skills/dot-cli/SKILL.md) (`login`, `setup`, `cache`, `prune`, `status`, `pull`, `trust`), and [agent usage](skills/dot-cli/references/agent-usage.md). `mise run completions` installs Fish completions; `check:completions` gates releases outside `all`.
- **Skills & releases**: [dot-skills](.agents/skills/dot-skills/SKILL.md) owns catalog links and `check:skills`; [skillify](skills/skillify/SKILL.md) owns authoring. [dot-release](.agents/skills/dot-release/SKILL.md) owns standalone qualification and `/dot-release` publishing.

## Layout

- `dot/`: `fmind_dot` CLI (stdlib `argparse`, Pydantic + PyYAML only), repo-only `dot_tasks/`, `uv.lock`, and `pytest` suite.
- `dot_agents/AGENTS.md` & harnesses: global persona (`~/.agents/AGENTS.md`) plus `private_dot_gemini/` (agy, primary), `private_dot_claude/`, `private_dot_copilot/`, `dot_config/private_opencode/`, and `private_dot_pi/` ([cross-harness agents](skills/agent-project/references/cross-harness-agents.md)).
- `skills/` & `.agents/skills/`: global catalog (`~/.agents/skills/`) and repo-local skills (`.claude/skills` → `.agents/skills`).
- `.chezmoitemplates/`, `.chezmoiignore`, `.github/`: merge/catalog helpers, repo-only/OS/age-key ignores (darwin-only `.docker` and `.zprofile`), README SVGs (`.github/assets/`), and CI/release workflows. Mise trust stays machine-local (`mise trust` or unmanaged `~/.config/mise/conf.d/trust.toml`).
