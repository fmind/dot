# Package Rules

Keep discovery compact and load procedures on demand. Static checks (`check:skills`) verify schema and reachability; [catalog review](catalog-review.md) measures load and token budgets.

## Categories and scope

- **Connector** (`metadata.kind: connector`): reusable CLI/I/O boundary (`gws`, `gh`, `pup`, `cf`, `gcloud`). Separate top-level providers; own auth, bounded queries, output format, and guardrails so task skills link instead of duplicating.
- **Task** (`metadata.kind: task`): cross-project workflow (`code-security`, `humanize`, `repository-docs`). Self-contained when short; add `references/` guides only for distinct modes.
- **Collection** (`metadata.kind: collection`): cohesive domain (`python-stack`, `agent-frameworks`, `project-scaffolding`) whose `SKILL.md` routes to guides and states shared prerequisites.
- **Scope (`skills/` vs `.agents/skills/`) is orthogonal to kind**: pick global only for a distinct recurring trigger, non-trivial delta beyond public docs, and startup headroom under [size and budgets](#size-and-budgets); use project scope first otherwise.

## Naming and ownership

- **Name by kind**: CLI/provider names for connectors, outcomes/artifacts for tasks, domain names for collections; avoid redundant aliases after renames.
- **Informative guide names**: task nouns (`foundation`, `bootstrap`, `image-build`) or tool names when tool-specific; never include the parent skill name as a hyphenated segment in a guide filename.
- **Action-led descriptions (`1–180` chars)**: start with work performed plus triggers/tools to disambiguate neighbors; drop hype adjectives. Guide descriptions cover only that guide's branch.

| Request boundary                                    | Owners                                                                                                                                                                                           |
| --------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Browser UI, Python server, docs site, notebook      | [web-frontend](../../web-frontend/SKILL.md), [python-web](../../python-web/SKILL.md), [documentation-site](../../documentation-site/SKILL.md), [marimo](../../python-mlops/references/marimo.md) |
| Mails, docs, slides, visuals, and audience polish   | [humanize](../../humanize/SKILL.md), [draft-mail](../../draft-mail/SKILL.md), [draft-doc](../../draft-doc/SKILL.md), [draft-typst-deck](../../draft-typst-deck/SKILL.md)                         |
| Project creation, upkeep, code audit                | [project-scaffolding](../../project-scaffolding/SKILL.md), [full-review](../../full-review/SKILL.md)                                                                                             |
| Task handoff, app system prompt, model API contract | [task-prompts](../../task-prompts/SKILL.md), [system-prompts](../../agent-frameworks/SKILL.md#system-prompts), [request contracts](../../model-providers/SKILL.md#request-contracts)             |
| Coding hosts, MCP setup, agent protocols            | [agent-harnesses](../../agent-harnesses/SKILL.md), [mcp-setup](../../agent-harnesses/references/mcp-setup.md), [agent-protocols](../../agent-protocols/SKILL.md)                                 |
| Tests, entry-point smoke checks, agent evals        | [python-testing](../../python-stack/references/python-testing/GUIDE.md), [smoke](../../full-review/references/smoke.md), [evaluation](../../agent-frameworks/references/evaluation/GUIDE.md)     |

## Structure and progressive disclosure

- **Single root `SKILL.md`**: never nest `SKILL.md` inside subdirectories (hosts load nested ones at startup); keep dormant skills outside discovery roots.
- **Host routing constraint**: agy reads only `name` and `description` at startup; do not rely on `allowed-tools` or `disable-model-invocation` for routing or permission boundaries.
- **Guide layout**: `references/<name>.md` or `references/<name>/GUIDE.md` (with only `name` and `description` in YAML frontmatter), indexed between `<!-- guides:start -->` and `<!-- guides:end -->` via `mise run format:skills`.
- **Shallow reachability**: `SKILL.md` links every guide; guides link their own resources cleanly; repeat critical safety gates inside directly entered guides.

## Size and budgets

- **Entrypoint targets**: ~300–600 tokens for collection routers, <1,500 tokens for procedures, hard ceiling 500 lines; move schemas, long flags tables, and templates to `references/`, `templates/`, or `assets/`.
- **Startup cap**: global and local `AGENTS.md` + skill discovery each stay below **5,000 tokens** ([context budgets](../../dot-cli/references/context.md)).

## Authoring deltas

- **Cut model-known basics**: omit language syntax, textbook theory, tool marketing, and raw upstream skill copies ([vendor-skills](../../agent-project/references/vendor-skills.md)); encode only non-obvious CLI flags, pitfalls, security gates, and Fmind preferences.
- **Bounded, positive recipes**: state explicit defaults, switch conditions, row/time bounds, and binary checks; reserve negatives for hard security boundaries. Put an official docs URL comment atop comment-capable configs.
- **Local verification**: pass `mise run check:skills` and [adoption checks](adoption-check.md) for meaningful additions or routing changes.
