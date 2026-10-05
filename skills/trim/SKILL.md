---
name: trim
description: "Shorten docs, prompts, skills, or configs without losing meaning or behavior."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/trim
  created: "2026-10-04"
  updated: "2026-10-05"
---

# Trim

Treat `/trim <path>` or "too verbose", "too complex", "simplify this" as a request to remove words, lines, and settings that carry nothing, while every fact, behavior, and the author's voice survive. Trimming is not summarizing: when the text is the deliverable (an article, a talk) and the user did not ask for a length, tighten sentences but keep its substance and length class. Arguments can set a target (`to 300 words`, `-40%`) or a scope. For code, [repository-maintenance](../repository-maintenance/SKILL.md) owns dead code and abstractions; apply these rules only with tests proving behavior.

## Workflow

1. **Measure**: record lines, words, and estimated tokens (characters / 4) before editing; for skill catalogs and instruction files also run `dot agent context --project . --details` (add `--source .` inside the fmind/dot checkout).

   ```bash
   wc -lwm <path>
   ```

1. **Map what must survive**: list each claim, rule, number, command, flag, link, warning, and authority boundary. For configuration, capture the effective result so the trim can prove it changed nothing: `mise cfg` and `mise settings`, `dprint resolved-config`, `ruff check --show-settings <file>`, `docker compose config`, `chezmoi cat <target>`, or `yq -o json` for plain data.
1. **Cut, in this order**:
   - **Duplication**: the same rule stated twice; keep it at its owner and link from elsewhere.
   - **Restated defaults**: settings equal to the installed tool's default, after verifying that default in its current docs or `--help` (defaults change between versions).
   - **Filler**: introductions, hedges, recaps, "note that", tool narration, history ("previously…"), and generic tutorials the reader's tools already know.
   - **Dead entries**: options for tools, paths, or features that no longer exist (prove absence with `rg` or `fd`).
   - **Verbose constructions**: lists that can be one sentence, sentences that can be a clause, examples that only repeat the rule.
1. **Never cut**: facts with their evidence, numbers and dates, exact commands and flags, non-obvious gotchas with their reason, security and authority boundaries, links and citations, required structure (frontmatter, anchored headings, generated-index markers), the documentation URL comment at the top of a configuration, comments explaining a non-default choice, and anything the user asked to keep. Preserve the author's voice and stance; do not rewrite into a different style.
1. **Prove equivalence**: re-capture the effective configuration and diff it (it must be identical); re-run affected checks and tests; for prose, walk the survival list and confirm each item is still present or deliberately dropped with a reason. Run the repository's formatter and link checks for edited files.
1. **Report**: before/after lines, words, and tokens with the percentage, the categories removed, and any candidate cut you kept because it looked load-bearing. Ask before removing anything ambiguous instead of guessing.

## Gotchas

- **Short is not simple**: replacing three explicit lines with a clever one-liner or a dense regular expression makes the file harder to maintain; prefer deleting to compressing.
- **Defaults drift**: a setting equal to today's default can still be intentional pinning; keep it when a comment or commit explains it.
- **Search before rewording shared phrases**: phrases reused verbatim across files (triggers, error messages, test fixtures) may be matched by tests or other agents; search before rewording.

## Documentation

- Companion skills: [repository-docs](../repository-docs/SKILL.md) (documentation ownership), [skillify](../skillify/SKILL.md) (skill size rules), [prompt-design](../prompt-design/SKILL.md) (application prompts).
