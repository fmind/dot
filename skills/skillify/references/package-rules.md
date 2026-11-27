# Package Rules

Keep discovery compact and load procedures on demand. `check:skills` checks schemas and links; [evaluation](evaluation.md) measures loads, budgets, and triggers. For `fmind/dot` registration, symlinks, and releases, see `dot-skills`.

## Categories and scope

- **Connector** (`metadata.kind: connector`): single CLI/API boundary (e.g., `gcloud`, `gws`, `sql`) owning auth, bounded queries, output formats, and guardrails so task skills link instead of duplicating.
- **Task** (`metadata.kind: task`): cross-project workflow (e.g., `full-review`, `humanize`, `subagent`); self-contained unless distinct modes or long schemas warrant `references/`.
- **Collection** (`metadata.kind: collection`): multi-guide domain router (e.g., `python`, `agent-frameworks`, `agent-harnesses`) owning shared prerequisites across distinct sub-tools—use `connector` for one CLI/API, `collection` when distinct guides share a domain.
- **Scope (`skills/` vs `.agents/skills/`)**: promote globally only for recurring triggers, non-trivial deltas beyond public docs, and room under [budgets](#structure-budgets-and-authoring); default to repo-local first.

## Naming and ownership

- **Name by kind**: CLI/provider for connectors, outcomes/artifacts for tasks, domain for collections; drop redundant aliases.
- **Indexed guides vs plain references**:
  - _Indexed sub-guides_ (`references/<name>.md` or `references/<name>/GUIDE.md`): strictly `name` and double-quoted `description` in YAML frontmatter (no parent prefix), synced between `<!-- guides:start -->` and `<!-- guides:end -->` in `SKILL.md`.
  - _Supporting files_ (`references/<topic>.md` or `references/<name>/references/<topic>.md`): plain Markdown, no YAML frontmatter.
- **Action-led descriptions (1–180 chars)**: open with work performed plus triggers/tools; scope guide descriptions to their branch.
- **Boundary seams**:
  - **Prose / channel / commercial**: [humanize](../../humanize/SKILL.md), [draft](../../draft/SKILL.md), [proposal](../../proposal/SKILL.md), [finops](../../finops/SKILL.md), [extract](../../extract/SKILL.md).
  - **Code / ML / agents**: [python](../../python/SKILL.md), [mlops](../../mlops/SKILL.md), [agent-frameworks](../../agent-frameworks/SKILL.md), [agent-harnesses](../../agent-harnesses/SKILL.md).
  - **Docs / review**: [docs](../../docs/SKILL.md), [full-review](../../full-review/SKILL.md), [subagent](../../subagent/SKILL.md).

## Structure, budgets, and authoring

- **Single root `SKILL.md`**: never nest `SKILL.md`; keep dormant skills outside discovery roots. `agy` reads only `name` and `description` at startup—never use `allowed-tools` or `disable-model-invocation` for permissions.
- **Token budgets**: target `~200–500` tokens for collection routers excluding the generated guide index (`< 1,000` total) and `< 1,200` for procedures. `check:skills` enforces `< 1,500` tokens and `<= 500` lines per non-template Markdown file, `< 5,000` per scope for `AGENTS.md` + skill discovery, and `< 2,000` for `supagents` ([context budgets](../../dot-cli/references/context.md)).
- **Authoring deltas**: keep only non-obvious flags, version quirks, security bounds, validation scripts, and Fmind defaults—drop stdlib trivia and vendor dumps ([vendor-skills](../../agent-harnesses/references/vendor-skills.md)). Scope YAGNI strictly to unrequested features without weakening verification.

## Promotion and portability

1. **Isolate dependencies**: self-contained templates, Python `3.10+` stdlib `python3 -I` scripts, PEP 723 `uv` scripts, and upstream links.
1. **Move cleanly**: relocate to `<name>/`, update `metadata`, fix links, delete the old file, wire global links via `dot-skills`, and verify with `mise run check:skills` and [evaluation](evaluation.md).
