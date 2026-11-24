---
name: lesson-learned
description: "Turn session corrections and decisions into minimal edits to checks, skills, AGENTS.md, or decision logs."
---

# Lesson Learned

Route durable session lessons to one canonical owner without rule bloat. Surface proposals under out-of-scope `Suggestions` (or when asked) after corrections, repeated instructions, non-obvious traps, or durable approved decisions, never after routine implementations. [Skillify](../SKILL.md) owns skill/guide authoring, [trim](trim.md) owns shortening, and [AGENTS.md guidance](../../docs/references/repository/references/agents.md) owns layer boundaries.

## Workflow

1. **Collect candidates**: list corrections, recurring `fmind-review-*` `P1` findings (`>= 2` occurrences across diffs/sessions), approved decisions with reasons, repeated prompts, workarounds, and stale/ignored rules; strip session paths, one-off values, and secrets. After high-stakes docs or announcements are published, also pull human-edited final copies, comments, and thread replies to diff against draft templates across four buckets (**clearer formulations**, **deleted noise**, **recurring reader questions/FAQ**, and **technical edge cases**) and generalize sanitized findings back into templates, skills, and reviewer personas.
1. **Filter strictly**: keep only recurring pitfalls not already covered (`rg -i '<keyword>' AGENTS.md ~/.agents/AGENTS.md ~/.agents/skills/*/ .agents/skills/`); treat ignored existing rules as wording/placement bugs, not missing rules.
1. **Select one owner, strongest first (defect-to-linter ratchet)**:
   1. **mechanical invariant gate** (zero-token, runs on every host, never drifts under load): `ast-grep` rule (`.ast-grep/rules/*.yml` with a remediation `message:` + `ast-grep test`), `import-linter` boundary contract (`[tool.importlinter]`), Ruff/`ty` config, regression test, or code default;
   1. owning skill (via [skillify](../SKILL.md) for multi-line or new-skill changes) — only when the lesson cannot be expressed statically;
   1. project `AGENTS.md` (repo invariant not expressible as a linter);
   1. global persona (`dot_agents/AGENTS.md` in `fmind/dot`);
   1. decision log (via [bf](../../bf/SKILL.md) when present) for dated choices and "do not re-raise" calls.
1. **Sharpen before adding**: tighten or replace existing lines and prune obsoleted text before adding anything new; verify budgets pass (`dot context --project .`, plus `--source .` in `fmind/dot`).
1. **Propose, then apply**: surface brief proposals under out-of-scope `Suggestions` naming owner path and change (or show exact diffs when asked); apply only after explicit user approval and run the owner's checks (`pytest`, `mise run check:skills`, formatters).

## Gotchas

- **Say "no lesson" plainly** when nothing durable changed.
- **Avoid host-only memory**: keep durable rules out of single-host stores (like Claude `memory/`); touch memory only on request and never delete memory cited by a decision log.
- **Route global agy `/learn` edits to `fmind/dot`**: global `/learn` writes `~/.gemini/GEMINI.md` (linked to `~/.agents/AGENTS.md`, overwritten by `chezmoi apply --force`) or unmanaged `~/.gemini/config/{rules,skills}/`; approve `learning_proposal.md` only at project scope and land global lessons in `fmind/dot`.
