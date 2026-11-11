---
name: lesson-learned
description: "Turn session corrections and decisions into minimal edits to checks, skills, AGENTS.md, or decision logs."
---

# Lesson Learned

Route durable session lessons to one canonical owner without rule bloat. Trigger on `(Lesson Learned)` proposals after an implementation, approved decision, correction, or repeated instruction. [Skillify](../SKILL.md) owns skill/guide authoring, [trim](../../trim/SKILL.md) owns shortening, and [AGENTS.md guidance](../../repository-docs/references/agents.md) owns layer boundaries.

## Workflow

1. **Collect candidates**: list corrections, approved decisions with reasons, repeated prompts, workarounds, and stale/ignored rules; strip session paths, one-off values, and secrets.
1. **Filter strictly**: keep only recurring pitfalls not already covered (`rg -i '<keyword>' AGENTS.md ~/.agents/AGENTS.md ~/.agents/skills/*/ .agents/skills/`); treat ignored existing rules as wording/placement bugs, not missing rules.
1. **Select one owner, strongest first**:
   1. automated check, test, lint rule, script, or code default;
   1. owning skill (via [skillify](../SKILL.md) for multi-line or new-skill changes);
   1. project `AGENTS.md` (repo invariant);
   1. global persona (`dot_agents/AGENTS.md` in `fmind/dot`);
   1. decision log (via [bf](../../bf/SKILL.md) when present) for dated choices and "do not re-raise" calls.
1. **Sharpen before adding**: tighten or replace existing lines and prune obsoleted text before adding anything new; verify budgets pass (`dot agent context --project .`, plus `--source .` in `fmind/dot`).
1. **Propose, then apply**: present ranked `(Lesson Learned)` diffs naming owner path and old/new text; apply only after explicit user approval and run the owner's checks (`pytest`, `mise run check:skills`, formatters).

## Gotchas

- **Prefer checks over prose**: checks run on every host at zero context cost; prose costs tokens and can be ignored.
- **Say "no lesson" plainly** when nothing durable changed.
- **Avoid host-only memory**: keep durable rules out of single-host stores (like Claude `memory/`); touch memory only on request and never delete memory cited by a decision log.
- **Route global agy `/learn` edits to `fmind/dot`**: global `/learn` writes `~/.gemini/GEMINI.md` (linked to `~/.agents/AGENTS.md`, overwritten by `chezmoi apply --force`) or unmanaged `~/.gemini/config/{rules,skills}/`; approve `learning_proposal.md` only at project scope and land global lessons in `fmind/dot`.
