# AGENTS.md (Project)

`fmind/dot` — chezmoi + mise dotfiles for AI-CLI/Python development on Linux and macOS. User setup, auth, and common tasks live in [README.md](README.md); repo procedures live in `.agents/skills/` (`chezmoi`, `dot-development`, `dot-skills`, `dot-release`).

## House Rules

- **Edit sources, never `$HOME`**: `chezmoi apply --force` overwrites targets ([chezmoi](.agents/skills/chezmoi/SKILL.md)).
- **Public repo, zero secrets/PII**: exclude local config (`~/.config/dot.yaml`, `~/.config/git/config.*`) and private IDs; keep `*.age` encrypted and scope runtime keys via `with-secret` (`0600`/`0400` `~/.config/dot/secrets/<NAME>`).
- **User-space & parallel probes**: never `sudo` (use `mise`); use `run_parallel` (`fmind_dot.process`) for independent checks.
- **Global tools**: `dot_config/mise/config.toml` holds cross-project CLIs, harnesses, and core tools (comment why each is global; never replace project pins).
- **Generated locks**: never hand-edit or format `mise.lock`, `dot_config/mise/mise.lock`, `dot_config/mise/locks/`, or `dot/uv.lock`; regenerate via `mise run lock` (`lock:tool TOOL...`; [mise](skills/mise/SKILL.md)).
- **Docs & theme pins**: keep `README.md` user-facing and workflows in skills ([docs](skills/docs/SKILL.md)). [fmind/theme](https://github.com/fmind/theme) owns palette/themes, `~/.agents/DESIGN.md`, and `~/.agents/themes/` (pinned in `.chezmoiexternal.toml.tmpl`).

## Validation & Workflows

Run `mise tasks` to list all tasks. Iterate: edit source → targeted checks → `mise run diff` → `mise run apply` (plus `mise run deploy` after `dot/` edits).

- **Docs, skills, persona**: `mise run check:format check:skills check:vale` + `dot context --source . --project .` ([dot-skills](.agents/skills/dot-skills/SKILL.md)).
- **Supagents**: `mise run format:supagents check:supagents` + `uv run --frozen --project dot pytest -c dot/pyproject.toml -q tests/test_reviewer_subagents.py` ([subagent](skills/subagent/SKILL.md)).
- **Code & templates**: targeted `pytest` + affected `check:*` ([dot-development](.agents/skills/dot-development/SKILL.md)).
- **Tools & releases**: alphabetize `[tools]` in `dot_config/mise/config.toml` → `mise run lock` → `mise run full`; releases follow [dot-release](.agents/skills/dot-release/SKILL.md).

## Key Paths

- `dot/`: `fmind_dot` CLI, `with-secret`, and `dot_tasks/`.
- `tests/`: repository, Fish, starter, and contract tests.
- `dot_agents/`: global `AGENTS.md` and `supagents/` (compiled to `private_dot_gemini/` and `private_dot_copilot/` via `supagents.yaml`).
- `skills/` & `.agents/skills/`: global reusable skills and repo-local workflow skills.
- `dot_config/`: tool configs and `vale` prose rules.
