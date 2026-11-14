# Package Rules

Keep discovery compact and load procedures on demand. Static checks (`check:skills`) verify schema and reachability; [evaluation](evaluation.md) measures real transcript loads, startup budgets, and trigger adoption.

## Categories and scope

- **Connector** (`metadata.kind: connector`): reusable CLI or API boundary (`bf`, `cf`, `fmind`, `gcloud`, `gh`, `gws`, `pup`). Separate top-level providers; own auth, bounded queries, output format, and guardrails so task skills link instead of duplicating.
- **Task** (`metadata.kind: task`): cross-project workflow (`code-security`, `humanize`, `repository-docs`, `draft-typst-deck`). Keep short procedures self-contained; add `references/` guides only for distinct modes or long schemas.
- **Collection** (`metadata.kind: collection`): cohesive domain (`python-stack`, `agent-frameworks`, `diagrams-as-code`, `project-scaffolding`) whose `SKILL.md` routes to guides and states shared prerequisites.
- **Scope (`skills/` vs `.agents/skills/`) is orthogonal to kind**: choose global scope only for a distinct recurring trigger, non-trivial delta beyond public docs, and sufficient headroom under [size and budgets](#size-and-budgets); default to project scope first otherwise.

## Naming and ownership

- **Name by kind**: CLI/provider names for connectors, outcomes/artifacts for tasks, domain names for collections; avoid redundant aliases after renames.
- **Guide vs plain reference**:
  - _Indexed sub-guide_ (`references/<name>/GUIDE.md`): has strictly `name` and `description` in YAML frontmatter (without repeating the parent skill's hyphenated name) and appears between `<!-- guides:start -->` and `<!-- guides:end -->` in `SKILL.md`.
  - _Supporting reference_ (`references/<name>.md`): plain Markdown with NO YAML frontmatter (`check:skills` rejects non-indexed guides with frontmatter unless directly linked as sub-guides), linked inline from `SKILL.md`.
- **Action-led descriptions (1–180 chars)**: start with work performed plus triggers/tools to disambiguate neighbors; drop filler adjectives. Guide descriptions cover only that guide's branch.

| Request boundary                                    | Owners                                                                                                                                                                                                                        |
| --------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Browser UI, Python server, docs site, notebook      | [web-frontend](../../web-frontend/SKILL.md), [python-web](../../python-web/SKILL.md), [documentation-site](../../documentation-site/SKILL.md), [marimo](../../python-mlops/references/marimo.md)                              |
| Mails, docs, slides, visuals, and audience polish   | [humanize](../../humanize/SKILL.md), [draft-mail](../../draft-mail/SKILL.md), [draft-doc](../../draft-doc/SKILL.md), [draft-typst-deck](../../draft-typst-deck/SKILL.md), [diagrams-as-code](../../diagrams-as-code/SKILL.md) |
| Project creation, upkeep, docs sync, code audit     | [project-scaffolding](../../project-scaffolding/SKILL.md), [repository-docs](../../repository-docs/SKILL.md), [full-review](../../full-review/SKILL.md)                                                                       |
| Task handoff, app system prompt, model API contract | [task-prompts](../../task-prompts/SKILL.md), [system-prompts](../../agent-frameworks/SKILL.md#system-prompts), [request contracts](../../model-providers/SKILL.md#request-contracts)                                          |
| Coding hosts, MCP setup, agent protocols            | [agent-harnesses](../../agent-harnesses/SKILL.md), [mcp-setup](../../agent-harnesses/references/mcp-setup.md), [agent-protocols](../../agent-protocols/SKILL.md)                                                              |
| Tests, entry-point smoke checks, agent evals        | [python-testing](../../python-stack/references/python-testing/GUIDE.md), [smoke](../../full-review/references/smoke.md), [evaluation](../../agent-frameworks/references/evaluation/GUIDE.md)                                  |

## Structure and progressive disclosure

- **Single root `SKILL.md`**: never nest `SKILL.md` inside subdirectories (hosts load nested ones at startup); keep dormant skills outside discovery roots.
- **Host routing constraint**: agy reads only `name` and `description` at startup; do not rely on `allowed-tools` or `disable-model-invocation` for routing or permission boundaries.
- **Shallow reachability**: `SKILL.md` links every reference, script, and template directory cleanly; repeat hard safety gates inside directly entered guides.

## Size and budgets

- **Entrypoint targets**: ~200–500 tokens for collection routers, <1,200 tokens for procedures, hard ceiling 500 lines; move schemas, long flags tables, and starter files into `references/`, `templates/`, or `assets/`.
- **Startup cap**: global and local `AGENTS.md` + skill discovery each stay comfortably below **5,000 tokens** ([context budgets](../../dot-cli/references/context.md)).

## Authoring deltas

- **Encode only the model delta**: strip standard library trivia, textbook definitions, ritual `--version`/`--help` commands, and raw upstream skill dumps ([vendor-skills](../../agent-project/references/vendor-skills.md)). Keep only non-obvious CLI flags, version quirks, security boundaries, executable validation scripts, and explicit Fmind defaults.
- **Enforce humanize hygiene in human-facing guides**: keep prose tight, drop unnecessary prose backticks around non-code nouns, and keep executable commands copy-pasteable with quiet/JSON flags (`--json`, `--quiet`).
- **Verify locally**: pass `mise run check:skills` and follow [evaluation](evaluation.md) after meaningful additions or routing changes.

## Promotion and portability

When promoting a project skill or guide into a standalone skill (or publishing independently):

1. **Isolate dependencies**: replace workspace-relative assumptions and parent references with self-contained templates, scripts (`python3 -I` stdlib or PEP 723 `uv` scripts), and explicit upstream links.
1. **Move cleanly without duplicates**: move owned files into the target `<name>/` package, update `metadata`, wire installation/symlink targets ([dot-skills](../../../.agents/skills/dot-skills/SKILL.md)), fix all cross-references across the catalog, and delete the old guide copy.
1. **Verify standalone**: run `mise run check:skills`, confirm zero unintended host or workspace leaks, and validate independent triggers ([evaluation](evaluation.md)).
