---
name: dot-skills
description: "Maintain fmind/dot skill packages, catalog budgets, package contracts, and installed links."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/.agents/skills/dot-skills
  created: "2026-09-09"
  updated: "2026-10-05"
---

# Maintain Dot Skills

Maintain first-party skills and their chezmoi links. [skillify](../../../skills/skillify/SKILL.md) owns authoring; its [package rules](../../../skills/skillify/references/package-rules.md) define package shape, resources, and standalone portability.

## Workflow

1. **Choose the owner**: inspect `git diff` and `git diff --cached`, apply skillify's admission rule, then read neighboring descriptions and extend an existing skill when it owns the workflow. Reusable skills belong in `skills/`; repository procedures belong in `.agents/skills/`. A tool's presence in the environment does not require a global skill.
1. **Register additions**: each scope (AGENTS.md plus skill names, descriptions, and paths) must stay below 5,000 estimated tokens; `mise run check:skills` enforces both scopes from source, while on-demand bodies, host/plugin catalogs, and combined totals are unbudgeted. Check headroom first with `dot agent context --source . --project .` and reduce overhead without losing distinctive triggers when full. Each global skill needs `dot_agents/skills/symlink_<name>.tmpl` containing `{{ .chezmoi.sourceDir }}/skills/<name>`.
1. **Connect resources**: use `metadata.kind` as the single connector, task, or collection tag. Keep a single procedure in the root; preserve substantial optional modes as guides at `references/<name>.md` or `references/<name>/GUIDE.md`, with their owned resources. Run `mise run format:skills` to generate parent routing indexes. Never nest `SKILL.md`. Update project `AGENTS.md` when workflow ownership changes; setup, usage, and the short task reference belong in `README.md`.
1. **Validate**: run `mise run check:skills` and formatting checks for edited files. For installation changes, also target `uv run --frozen --project dot pytest -q dot/tests/test_skill_install_links.py`. Follow project `AGENTS.md` for broader qualification; prose-only changes do not require the full Python suite or build. Use [git-worktree](../../../skills/git-worktree/SKILL.md) when formatters could alter unrelated work. `dot agent context --check` without `--source` also measures independently installed packages in the shared roots. Review `mise run report:skills` when descriptions or guides change; its estimates are diagnostic.
1. **Exercise changed guidance**: walk a realistic request through the skill using safe commands and disposable fixtures for writes. For output changes, compare success and failure cases, exit codes, diagnostics, and completeness markers. When host integration changes, check the affected host separately; catalog checks do not prove discovery or selection.

## Rename or remove

1. **Locate references; rename atomically**: use `rg` to find the old name and path across both catalogs, docs, host configuration, and `dot/`. For a rename, change the directory, frontmatter name, provenance path, and update date together; preserve needed guidance when consolidating packages.
1. **Repoint all links at once**: update inbound links and the global link declaration together. Preserve historical records, then search again and validate as above.
1. **Clean retired links via the guide**: apply leaves retired installed links in place. Use the [installed-link recovery guide](references/installed-links.md) for cleanup, collisions, source relocation, or catalog ownership.

## Boundaries

- **Keep `~/.agents/skills/` a real shared directory**: never `exact_`. Independently installed packages remain outside this repository; names must be unique.
- **Know each check's coverage**: `mise run check:skills` validates both first-party roots; `gh skill publish --dry-run skills` alone covers only the global directory. Sibling references are allowed here; standalone publication needs the package rules' portability check.

## Documentation

- [skill_contracts.py](../../../dot/dot_tasks/skill_contracts.py) enforces package shape, resources, guide indexes, and context budgets; [contract tests](../../../dot/tests/test_contracts.py) cover it and chezmoi link registration; lychee checks Markdown links.
- Companion skills: [agent-project](../../../skills/agent-project/SKILL.md) (host discovery), [repository-docs](../../../skills/repository-docs/SKILL.md) (documentation ownership).
