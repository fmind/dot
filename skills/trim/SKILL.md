---
name: trim
description: "Shorten docs, prompts, skills, or configs without losing meaning or behavior."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/trim
  created: "2026-10-04"
  updated: "2026-11-11"
---

# Trim

Handle `/trim <path>` or verbosity complaints by cutting words, lines, and settings that carry nothing while keeping every fact, behavior, and the author's voice. For rewriting external communication for signal and visual hierarchy, use [humanize](../humanize/SKILL.md); for code dead-code/abstractions, use [full-review](../full-review/SKILL.md) (trim code only with behavior tests).

## Workflow

1. **Measure baseline**: `wc -lwm <path>`, plus `dot agent context --project . --details` (add `--source .` in `fmind/dot`) for instructions and skills.
1. **Inventory survivors**: list every claim, rule, number, command, flag, link, warning, and authority boundary. For configs, snapshot effective state first (`mise tasks ls --json --hidden`, `mise ls --current --json`, `mise env --json`, `mise settings`, `dprint resolved-config`, `ruff check --show-settings <file>`, `docker compose config`, `chezmoi cat <target>`, or `yq -o json` with `mikefarah/yq` v4).
1. **Cut in order**:
   - **Duplication**: keep once at the canonical owner; link elsewhere.
   - **Restated defaults**: drop settings matching the installed version's verified default (unless a comment/commit pins them intentionally).
   - **Filler**: intros, hedges, recaps, "note that", narration, history, and generic tool tutorials.
   - **Dead entries**: paths/options proven absent with `rg` or `fd`.
   - **Wordy phrasing**: collapse lists to clauses and drop redundant examples.
1. **Preserve**: evidence-backed facts, numbers/dates, exact commands/flags, non-obvious gotchas with reasons, security/authority boundaries, links, required frontmatter/anchors/index markers, top-of-config docs URL comments, non-default rationale comments, and author voice.
1. **Prove equivalence**: diff recaptured effective config (must match), walk the survival list, and run formatters, link checks, and affected tests.
1. **Report**: before/after lines, words, and `ceil(chars/4)` tokens (`%`), cut categories, and ambiguous candidates held back for approval.

## Gotchas

- **Delete, don't compress**: never trade readable lines for clever one-liners or dense regexes.
- **Search shared strings first**: `rg` before rewording triggers, error strings, or test-matched phrases.

## Documentation

- Companions: [humanize](../humanize/SKILL.md), [repository-docs](../repository-docs/SKILL.md), [skillify](../skillify/SKILL.md), [system-prompts](../agent-frameworks/SKILL.md#system-prompts).
