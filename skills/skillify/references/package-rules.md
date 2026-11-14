# Package Rules

Keep discovery compact and load procedures on demand. `check:skills` checks schemas and links; [evaluation](evaluation.md) measures transcript loads, startup budgets, and triggers.

## Categories and scope

- **Connector** (`metadata.kind: connector`): reusable CLI or API boundary (`bf`, `cf`, `fmind`, `gcloud`, `gh`, `gws`, `pup`); owns auth, bounded queries, output format, and guardrails so task skills link instead of duplicating.
- **Task** (`metadata.kind: task`): cross-project workflow (`code-security`, `humanize`, `repository-docs`, `draft-typst-deck`); self-contained unless distinct modes or long schemas warrant `references/`.
- **Collection** (`metadata.kind: collection`): cohesive domain (`python-stack`, `agent-frameworks`, `diagrams-as-code`, `project-scaffolding`) whose `SKILL.md` routes to guides and shared prerequisites.
- **Scope (`skills/` vs `.agents/skills/`)**: promote globally only for recurring triggers, non-trivial deltas beyond public docs, and room under [structure and budgets](#structure-budgets-and-authoring); default to repo-local first.

## Naming and ownership

- **Name by kind**: CLI/provider for connectors, outcomes/artifacts for tasks, domain for collections; drop redundant post-rename aliases.
- **Indexed guides vs plain references**:
  - _Indexed sub-guides_ (`references/<name>.md` or `references/<name>/GUIDE.md`): require strictly `name` and `description` in YAML frontmatter (without repeating the parent prefix) and sync between `<!-- guides:start -->` and `<!-- guides:end -->` in `SKILL.md`.
  - _Supporting files_ (`references/<topic>.md` or `references/<name>/references/<topic>.md`): plain Markdown with no YAML frontmatter (`check:skills` rejects non-indexed frontmatter files).
- **Action-led descriptions (1–180 chars)**: open with the work performed plus triggers/tools; keep guide descriptions scoped to their branch.
- **Request owners**:
  - UI, Python servers, docs sites, & notebooks: [web-frontend](../../web-frontend/SKILL.md), [python-web](../../python-web/SKILL.md), [documentation-site](../../documentation-site/SKILL.md), [marimo](../../python-mlops/references/marimo.md).
  - Mails, docs, slides, & diagrams: [humanize](../../humanize/SKILL.md), [draft-mail](../../draft-mail/SKILL.md), [draft-doc](../../draft-doc/SKILL.md), [draft-typst-deck](../../draft-typst-deck/SKILL.md), [diagrams-as-code](../../diagrams-as-code/SKILL.md).
  - Project bootstrap, upkeep, docs, & review: [project-scaffolding](../../project-scaffolding/SKILL.md), [repository-docs](../../repository-docs/SKILL.md), [full-review](../../full-review/SKILL.md).
  - Prompts, model APIs, harnesses, & MCP: [task-prompts](../../task-prompts/SKILL.md), [system-prompts](../../agent-frameworks/SKILL.md#system-prompts), [request contracts](../../model-providers/SKILL.md#request-contracts), [agent-harnesses](../../agent-harnesses/SKILL.md), [mcp-setup](../../agent-harnesses/references/mcp-setup.md), [agent-protocols](../../agent-protocols/SKILL.md).
  - Testing, smoke checks, & evals: [python-testing](../../python-stack/references/python-testing/GUIDE.md), [smoke](../../full-review/references/smoke.md), [evaluation](../../agent-frameworks/references/evaluation/GUIDE.md).

## Structure, budgets, and authoring

- **Single root `SKILL.md`**: never nest `SKILL.md` in subdirectories; keep dormant skills outside discovery roots. agy reads only `name` and `description` at startup, so do not rely on `allowed-tools` or `disable-model-invocation` for permissions.
- **Size and budgets**: target ~200–500 tokens for collection routers and <1,200 tokens for procedures. `check:skills` enforces **< 1,500 estimated tokens** on every non-template skill Markdown file and a 500-line ceiling; offload long schemas/flags to `references/`, `templates/`, or `assets/`, keeping global and local startup budgets well under **5,000 tokens** ([context budgets](../../dot-cli/references/context.md)).
- **Authoring deltas**: encode only non-obvious flags, version quirks, security boundaries, executable validation scripts, and Fmind defaults—drop stdlib trivia and raw vendor dumps ([vendor-skills](../../agent-project/references/vendor-skills.md)). Drop prose backticks in human copy and keep copy-pasteable commands quiet (`--json`, `--quiet`).

## Promotion and portability

1. **Isolate dependencies**: replace workspace assumptions with self-contained templates, `python3 -I` stdlib or PEP 723 `uv` scripts, and explicit upstream links.
1. **Move cleanly**: move files to `<name>/`, update `metadata`, wire catalog links via `dot-skills`, fix cross-references, delete the old guide, and verify with `mise run check:skills` and [evaluation](evaluation.md).
