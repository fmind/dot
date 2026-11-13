---
name: repository-docs
description: "Write and sync README, AGENTS.md, and repo docs with verified behavior."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/repository-docs
  created: "2026-09-07"
  updated: "2026-11-13"
---

# Repository Documentation

Keep human and agent docs aligned with live code, with one canonical owner per claim.

## Workflow

1. **Inventory**: find `README.md`, root/nested `AGENTS.md`, `docs/`, `.github/*.md`, generated help, and `.agents/skills/*/SKILL.md` (plus any repo skill catalog).
1. **Verify against code**: check entry points, source, tests, manifests, `mise` tasks, hooks, CI, and `--help` for every path, flag, version, and example.
1. **Route by audience**: [README guidance](references/readme.md) and [README assets](references/readme-assets.md) for human identity, visuals, badges, and quickstart; [AGENTS guidance](references/agents.md) for agent commands, invariants, and layout; skills for reusable workflows (link instead of copying).
1. **Gate**: run repo doc checks, `typos`, `dot agent context --check` after instruction/skill edits, `lychee --no-progress --include-fragments=full <files>` (checks anchors + `#:~:text=`; add `--include-verbatim` when code-block URLs carry claims), `dprint check`, and any site build; inspect rendered layout changes.
1. **Report**: changed files, verification evidence, and unverified external claims.

## Gotchas

- **Regenerate, never hand-edit** generated docs; report local checks, CI, deploy, and publication statuses separately.
- **Portable Markdown defaults**: `1.` ordered lists, language-tagged fences, one-line paragraphs, relative or `~`-relative paths in skills/`AGENTS.md`, and official docs URL comments atop comment-capable configs (below any schema directive). Preserve public anchors and exclude secrets or session state.
- **Guard `$` tokens and backticks**: `dprint-plugin-markdown` parses two bare `$` characters on one line (such as `$VAR` or brand `$` tokens outside code spans) as inline `$...$` LaTeX math and mangles adjacent backticks and spaces; wrap `$` tokens in inline code or split lines, and check instruction docs for escaped, unmatched, or adjacent backticks.

## Documentation

- [GitHub README guidance](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-readmes) · [AGENTS.md](https://agents.md) · [Agent Skills](https://agentskills.io/specification)
- Companions: [agent-project](../agent-project/SKILL.md), [humanize](../humanize/SKILL.md), [skillify](../skillify/SKILL.md), [dprint](../mise/references/dprint.md), [diagrams-as-code](../diagrams-as-code/SKILL.md).
