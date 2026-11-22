# Package Rules

Keep discovery compact and load procedures on demand. `check:skills` checks schemas and links; [evaluation](evaluation.md) measures transcript loads, startup budgets, and triggers.

## Categories and scope

- **Connector** (`metadata.kind: connector`): reusable CLI or API boundary (e.g., `bf`, `dot-cli`, `fmind`, `gcloud`, `gws`, `sql`); owns auth, bounded queries, output format, and guardrails so task skills link instead of duplicating.
- **Task** (`metadata.kind: task`): cross-project workflow (e.g., `extract`, `finops`, `full-review`, `humanize`, `mise`, `proposal`, `shell`, `skillify`, `subagent`); self-contained unless distinct modes or long schemas warrant `references/`.
- **Collection** (`metadata.kind: collection`): cohesive domain (e.g., `python`, `mlops`, `cloud-ops`, `docs`, `draft`, `github`, `containers`, `agent-frameworks`, `code-security`, `diagrams-as-code`, `agent-harnesses`) whose `SKILL.md` routes to guides and shared prerequisites.
- **Scope (`skills/` vs `.agents/skills/`)**: promote globally only for recurring triggers, non-trivial deltas beyond public docs, and room under [structure and budgets](#structure-budgets-and-authoring); default to repo-local first.

## Naming and ownership

- **Name by kind**: CLI/provider for connectors, outcomes/artifacts for tasks, domain for collections; drop redundant post-rename aliases.
- **Indexed guides vs plain references**:
  - _Indexed sub-guides_ (`references/<name>.md` or `references/<name>/GUIDE.md`): require strictly `name` and `description` in YAML frontmatter (without repeating the parent prefix) and sync between `<!-- guides:start -->` and `<!-- guides:end -->` in `SKILL.md`.
  - _Supporting files_ (`references/<topic>.md` or `references/<name>/references/<topic>.md`): plain Markdown with no YAML frontmatter (`check:skills` rejects non-indexed frontmatter files).
- **Action-led descriptions (1–180 chars)**: open with the work performed plus triggers/tools; keep guide descriptions scoped to their branch.
- **Boundary seams** (avoid overlap when adding/routing guides):
  - **Prose vs channel vs commercial**: [humanize](../../humanize/SKILL.md) owns audience/craft; [draft](../../draft/SKILL.md) owns Workspace/Typst plumbing; [proposal](../../proposal/SKILL.md) owns SOW/WBS/effort; [finops](../../finops/SKILL.md) owns cloud/AI TCO; [extract](../../extract/SKILL.md) owns inbound extraction.
  - **Code vs ML vs agents**: [python](../../python/SKILL.md) owns core Python/web/CLIs; [mlops](../../mlops/SKILL.md) owns tabular/ML/notebooks; [agent-frameworks](../../agent-frameworks/SKILL.md) owns LLM SDKs/evals/RAG; [agent-harnesses](../../agent-harnesses/SKILL.md) owns CLI hosts/MCP/setup.
  - **Docs vs review**: [docs](../../docs/SKILL.md) owns README/AGENTS/ADR/runbooks/postmortems/Zensical; [full-review](../../full-review/SKILL.md) owns repo/PR/smoke audits; [subagent](../../subagent/SKILL.md) owns read-only `fmind-review-*` reviewers.

## Structure, budgets, and authoring

- **Single root `SKILL.md`**: never nest `SKILL.md` in subdirectories; keep dormant skills outside discovery roots. agy reads only `name` and `description` at startup, so do not rely on `allowed-tools` or `disable-model-invocation` for permissions.
- **Size and budgets**: target ~200–500 tokens for collection routers and <1,200 tokens for procedures. `check:skills` enforces **< 1,500 estimated tokens** on every non-template skill Markdown file and a 500-line ceiling; offload long schemas/flags to `references/`, `templates/`, or `assets/`, keeping `AGENTS.md` + skill discovery well under **5,000 tokens** and `supagents` discovery under **2,000 tokens** per scope ([context budgets](../../dot-cli/references/context.md)).
- **Authoring deltas**: encode only non-obvious flags, version quirks, security boundaries, executable validation scripts, and Fmind defaults—drop stdlib trivia and raw vendor dumps ([vendor-skills](../../agent-harnesses/references/vendor-skills.md)). Never write shortcut-licensing slogans; scope YAGNI strictly to unrequested features while requiring full state coverage and rendered verification on agreed work. Calibrate monospace per [humanize](../../humanize/SKILL.md) and keep copy-pasteable commands quiet (`--json`, `--quiet`).

## Promotion and portability

1. **Isolate dependencies**: replace workspace assumptions with self-contained templates, `python3 -I` stdlib scripts (targeting Python `3.14+`, or `uv run --python 3.14 --no-project python -I` inside older-Python repos), PEP 723 `uv` scripts, and explicit upstream links.
1. **Move cleanly**: move files to `<name>/`, update `metadata`, wire catalog links via `dot-skills`, fix cross-references, delete the old guide, and verify with `mise run check:skills` and [evaluation](evaluation.md).
