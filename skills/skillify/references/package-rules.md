# Package Rules

Keep discovery compact and load procedures on demand. This page owns admission and structure; [catalog review](catalog-review.md) owns measurement. Static checks prove structure, not host selection or execution.

## Categories and scope

- **Connector** (`metadata.kind: connector`): reusable I/O boundary (`gws`, `gh`, `acli`, `gcloud`, `hf`, `kaggle`, `colab`). Keep providers separate at top level; own auth, bounded queries, serialization, and read-back checks. Task skills link connectors instead of copying them.
- **Task** (`metadata.kind: task`): cross-project outcome (`code-security`, `scheduled-jobs`, `repository-docs`). Self-contained when short; add guides only for substantial modes.
- **Collection** (`metadata.kind: collection`): cohesive domain (`python-stack`, `agent-frameworks`, `project-scaffolding`) whose entrypoint routes to guides and states shared prerequisites. Group by domain coherence, not low frequency.
- **Scope is orthogonal to kind**: any kind can live globally (`skills/`) or repo-locally (`.agents/skills/`).
- **Single classification tag**: use only `metadata.kind` (no `tags`, `type`, subfolders, or description prefixes); names and descriptions must route without it.
- **Evidence gate for global entries**: extend an existing owner or use project scope first. Add a global skill only for a distinct recurring trigger, non-trivial behavioral value beyond public docs, and headroom within [size and budgets](#size-and-budgets). Installed tools do not automatically need skills, though rare high-stakes recovery procedures may.

## Naming and ownership

- **Name by kind**: CLI/provider names for connectors (`gh`, `gws`), outcomes/artifacts for tasks (`cloud-run`), coherent domains for collections. Add qualifiers only to separate real neighbors; skip cosmetic renames unless migration yields concrete value across consumers.
- **Action-led descriptions**: start with the work performed, include distinctive tools/triggers, differentiate close neighbors, and drop hype ("modern", "comprehensive", "best"). Guide descriptions state only that guide's branch.
- **Informative guide names**: use task nouns (`foundation`, `bootstrap`, `image-build`, `code-review`), reserving tool names for tool-specific guides; never repeat the parent's name or keep alias packages after a rename.

| Request boundary                                               | Owners                                                                                                                                                                                             |
| -------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Browser UI, Python server, documentation site, notebook        | [web-frontend](../../web-frontend/SKILL.md), [python-web](../../python-web/SKILL.md), [documentation-site](../../documentation-site/SKILL.md), [marimo](../../python-mlops/references/marimo.md)   |
| Project creation, repository upkeep, code audit                | [project-scaffolding](../../project-scaffolding/SKILL.md), [full-review](../../full-review/SKILL.md)                                                                                               |
| Task handoff, embedded application prompt                      | [task-prompts](../../task-prompts/SKILL.md), [system-prompts](../../agent-frameworks/SKILL.md#system-prompts), [request contracts](../../model-providers/SKILL.md#request-contracts)               |
| Configure coding hosts, connect MCP, implement protocols       | [agent-harnesses](../../agent-harnesses/SKILL.md), [mcp-setup](../../agent-harnesses/references/mcp-setup.md), [agent-protocols](../../agent-protocols/SKILL.md)                                   |
| Test code, smoke-test entry points, evaluate stochastic agents | [python-testing](../../python-stack/references/python-testing/GUIDE.md), [smoke](../../full-review/references/smoke/GUIDE.md), [evaluation](../../agent-frameworks/references/evaluation/GUIDE.md) |

## Entrypoints and guides

- **Single root `SKILL.md`**: never nest `SKILL.md` (hosts expose nested ones at startup); keep dormant packages outside discovery roots.
- **Root frontmatter**: `name` (lowercase hyphenated, matches directory, ≤64 chars), `description` (1–180 chars), `license: MIT`, and string-valued `metadata.{kind,author,source,created,updated}` (quoted `YYYY-MM-DD`, `updated >= created`). Use `compatibility` only for non-obvious runtime constraints (like `bf`); never rely on `allowed-tools` or `disable-model-invocation` for routing/permissions since agy reads only `name` and `description`.
- **Guides under `references/`**: `references/<name>.md` or `references/<name>/GUIDE.md` (with owned `references/`, `templates/`, `scripts/`). First-party guide frontmatter has **only** `name` (stem or parent dir) and `description` (preserve upstream provenance/license files as plain references).
- **Generated guide indexes**: keep `<!-- guides:start -->` … `<!-- guides:end -->` under `## Task guides`, synced via `mise run format:skills` (no `metadata.guides`).
- **Shallow, complete reachability**: `SKILL.md` links every guide; guides link owned resources via document-relative paths (`parent → guide → resource`). Disconnected cycles, scripts, and output templates do not satisfy reachability. Keep shared steps in the parent only when every mode needs them; repeat critical authority gates in directly entered guides.

## Size and budgets

- **Body targets**: ~300–600 estimated tokens for collection routers, <1,500 for ordinary procedures, hard ceiling 500 lines per entrypoint/guide; move heavy examples, configs, and templates to resources.
- **5,000-token startup ceiling per scope**: global and local `AGENTS.md` + discovery stay below 5,000 tokens independently ([context budgets](../../dot-cli/references/context.md)), measured via [catalog review](catalog-review.md).

## Resources and portability

- **Standard folders only**: `references/` (decisions/procedures), `templates/` and `assets/` (copied outputs), `scripts/` (executables and deterministic helpers). Validate links across reachable Markdown; follow [portability](portability.md) for promotion or standalone export, and route durable fixes to one owner per [lesson-learned](lesson-learned.md) (update memory only on user request).

## Authoring and verification

- **Delta-only instructions**: state what the agent must do differently (one default + switch condition, vendor source + local deviations); cut tutorials, persona recaps, speculative options, and private incidents.
- **Actionable phrasing**: keep "never X" for hard gates; write positive output recipes and binary done conditions ([study heuristic](https://github.com/obra/superpowers/blob/2ce8aa15d05bd57213e6f746f953aafb7ded7a8b/docs/superpowers/specs/2026-06-10-positive-instruction-redesign-design.md)).
- **Bounded examples**: filter fields, paths, windows, and limits up front while preserving pagination markers, warnings, error locations, and exit codes ([mise output conventions](../../mise/references/task-conventions.md#concise-output)).
- **Conventions & proof**: H1 + concise intent + workflow + gotchas + primary docs/releases links; [bold-summary rules](../../repository-docs/references/agents.md) and [repository-docs](../../repository-docs/SKILL.md) Markdown style; official docs URL comment atop comment-capable configs. Validate static contracts plus [adoption checks](adoption-check.md); keep load counting local via `skill_loads.py` without telemetry or auto-deletion.
