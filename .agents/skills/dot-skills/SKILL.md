---
name: dot-skills
description: "Maintain fmind/dot skill packages, catalog budgets, routing contracts, and installed links."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/.agents/skills/dot-skills
  created: "2026-09-09"
  updated: "2026-09-16"
---

# Maintain Dot Skills

Maintain first-party skills and their chezmoi links. [skillify](../../../skills/skillify/SKILL.md) owns authoring; its [package rules](../../../skills/skillify/references/package-rules.md) define package shape, resources, and standalone portability.

## Workflow

1. **Choose the owner**: inspect `git diff` and `git diff --cached`, apply skillify's admission rule, then read neighboring descriptions and extend an existing skill when it owns the workflow. Reusable skills belong in `skills/`; repository procedures belong in `.agents/skills/`. A tool's presence in the environment does not require a global skill.
1. **Register additions**: first check the independent global/local limits: each AGENTS.md plus its skill discovery must be below 5,000 estimated tokens with `mise run report:skills`; reduce overhead without losing distinctive triggers when full. Add each admitted skill and its required CLI tools to [contracts.json](../../../skills/contracts.json), and a primary case to [routing-boundaries.json](../../../dot/testdata/skills/routing-boundaries.json). Each global skill also needs `dot_agents/skills/symlink_<name>.tmpl` containing `{{ .chezmoi.sourceDir }}/skills/<name>`.
1. **Connect resources**: use `metadata.kind` as the single connector, task, or collection tag. Keep a single procedure in the root; preserve substantial optional modes as guides at `references/<name>.md` or `references/<name>/GUIDE.md`, with their owned resources. Run `mise run format:skills` to generate parent routing indexes. Never nest `SKILL.md`. Update project `AGENTS.md` when workflow ownership changes; setup/auth instructions belong in `README.md`.
1. **Validate**: run `mise run check:skills` and formatting checks for edited files. For installation changes, also target `uv run --frozen pytest -q dot/tests/test_skill_links.py`. Follow project `AGENTS.md` for broader qualification; prose-only changes do not require the full Python suite or build. Use [git-worktree](../../../skills/git-worktree/SKILL.md) when formatters could alter unrelated work. Use `dot agent context --source . --project . --check` to measure the source catalog and AGENTS.md costs; omit `--source` to measure installed shared roots. Review `mise run report:skills` when descriptions or routing cases change; its lexical ranking is diagnostic.
1. **Exercise changed guidance**: walk a realistic request through the skill using safe commands and disposable fixtures for writes. When host integration changes, check the affected host separately; catalog checks do not prove discovery or selection.

## Rename or remove

1. Use `rg` to find the old name and path across both catalogs, docs, host configuration, and `dot/`. For a rename, change the directory, frontmatter name, provenance path, and update date together; preserve needed guidance when consolidating packages.
1. Update the manifest, routing entries, inbound links, and global link declaration together. Preserve historical records, then search again and validate as above.
1. Apply leaves retired installed links in place. Use the [installed-link recovery guide](references/installed-links.md) for cleanup, collisions, source relocation, or catalog ownership.

## Boundaries

- Keep `~/.agents/skills/` a real shared directory, never `exact_`. Independently installed packages remain outside this repository and its manifest; names must be unique.
- `mise run check:skills` validates both first-party roots; `gh skill publish --dry-run skills` alone covers only the global directory. Sibling references are allowed here; standalone publication needs the package rules' portability check.

## Documentation

- [Contract tests](../../../dot/tests/test_contracts.py) cover package shape, resources, links, registration, and routing fixture structure.
- Companion skills: [agent-project](../../../skills/agent-project/SKILL.md) (host discovery), [repository-docs](../../../skills/repository-docs/SKILL.md) (documentation ownership).
