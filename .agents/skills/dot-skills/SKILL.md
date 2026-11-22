---
name: dot-skills
description: "Maintain fmind/dot skills, context budgets, contracts, installed links."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/.agents/skills/dot-skills
  created: "2026-09-09"
  updated: "2026-11-22"
---

# Maintain Dot Skills

Maintain first-party skills and chezmoi links. [skillify](../../../skills/skillify/SKILL.md) and its [package rules](../../../skills/skillify/references/package-rules.md) own authoring, package shape, and portability.

## Workflow

1. **Choose the owner**: inspect `git diff` / `git diff --cached`, check neighboring descriptions, and apply the [admission rule](../../../skills/skillify/references/package-rules.md#categories-and-scope) (`skills/` for reusable skills, `.agents/skills/` for repo-only procedures).
1. **Register within budget**: per scope, `AGENTS.md` + skill discovery must stay below 5,000 estimated tokens and `supagents` discovery below 2,000 ([context budgets](../../../skills/dot-cli/references/context.md)), enforced by `mise run check:skills`. Check `dot context --source . --project .` first; if global headroom is under ~60 tokens, merge or retire an entry in the same change. Every global skill requires `dot_agents/skills/symlink_<name>.tmpl` containing `{{ .chezmoi.sourceDir }}/skills/<name>`.
1. **Wire resources**: set `metadata.kind` (`connector`, `task`, or `collection`), keep one procedure in `SKILL.md` with optional modes at `references/<name>.md` or `references/<name>/GUIDE.md`, never nest `SKILL.md`, and run `mise run format:skills` to sync routing indexes. Sync `AGENTS.md` when ownership shifts (`README.md` stays user-facing).
1. **Validate**: run `mise run check:skills` and edited-file formatters (isolate via [git-worktree](../../../skills/git-delivery/references/git-worktree/GUIDE.md) when unrelated edits exist); add `uv run --frozen --project dot pytest -c dot/pyproject.toml -q tests/test_skill_install_links.py` for link changes. Because the repo skill gate checks links offline, also run `lychee --no-progress --include-fragments=full <edited-files>` online whenever adding or changing external `https://` URLs. `dot context --check` (without `--source`) also checks third-party installs; `--details` prints scope-level on-demand totals, source paths, and coverage (`--json` includes `.entries[]`).
1. **Exercise behavior**: verify changed guidance per [evaluation](../../../skills/skillify/references/evaluation.md) and test host discovery separately when host integration changes.

## Rename or remove

1. **Update atomically**: `rg` the old name/path across `skills/`, `.agents/skills/`, docs, host configs, `dot/`, and `tests/`. Update directory, frontmatter `name`, `metadata.source`, `metadata.updated`, inbound links, and `dot_agents/skills/symlink_*.tmpl` together while keeping historical logs intact.
1. **Retire deployed links**: add retired `.agents/skills/<name>` entries to `.chezmoiremove` per [chezmoi](../chezmoi/SKILL.md); use [installed-link recovery](references/installed-links.md) for manual cleanup or checkout relocation.

## Boundaries

- **Keep `~/.agents/skills/` a real shared directory**: never `exact_` or a whole-catalog symlink; third-party packages coexist there, and apply refuses collisions instead of overwriting.
- **Know check scope**: `mise run check:skills` validates both catalogs (`gh skill publish --dry-run skills` checks only `skills/`); standalone export requires the portability check.

## Documentation

- [Agent Skills specification](https://agentskills.io/specification) · [gh skill](https://cli.github.com/manual/gh_skill) · [skill_contracts.py](../../../dot/dot_tasks/skill_contracts.py) · [test_contracts.py](../../../dot/tests/test_contracts.py)
- Companions: [project-setup](../../../skills/agent-harnesses/references/project-setup.md), [docs/repository](../../../skills/docs/references/repository/GUIDE.md).
