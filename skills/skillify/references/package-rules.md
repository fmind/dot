# Package Rules

Keep a small discovery catalog and load procedures only for the task at hand. [skillify](../SKILL.md) owns admission; [catalog review](catalog-review.md) owns measurement. Package checks prove structure, not host selection or successful execution.

## Categories and scope

- **Connector** (`metadata.kind: connector`): a reusable input/output boundary such as gws, gh, acli, gcloud, hf, Kaggle, or Colab. Keep providers separate at the top level; own identity, bounded requests, serialization, and read-back verification. Task skills reference connectors instead of copying their mechanics.
- **Task** (`metadata.kind: task`): an outcome that applies across projects, such as security review, scheduling, or repository documentation. Keep a short procedure self-contained; add guides only for substantial modes.
- **Collection** (`metadata.kind: collection`): a cohesive domain such as Python, application frameworks, or project creation. Its entrypoint selects a guide and states essential shared prerequisites. Group by task/domain coherence, not simply infrequent use.
- Category and installation scope are independent. Reusable global owners live in `skills/`; repository-only owners live in `.agents/skills/`. First-party global owners get individual chezmoi links into the real shared `~/.agents/skills/` directory. Other installed packages remain independently managed.
- `metadata.kind` is the single classification tag; do not duplicate it in `tags`, `type`, directory groups, or description prefixes. Classify by the current workflow: a provider boundary is a connector, one outcome is a task, and several distinct domain workflows form a collection. Metadata supports maintenance; names and descriptions must still route without it.
- Admit a global owner only for a distinct recurring trigger and demonstrated behavioral benefit. First extend an existing owner or choose project scope. An installed tool does not automatically need a skill; rarely used recovery guidance may still deserve direct discovery.

## Naming and ownership

- Name the current capability, not an aspirational umbrella: a Cloud Run deployment procedure is `cloud-run`, and public username reconnaissance is `username-recon`. A collection needs several distinct workflows that justify its broader domain name.
- Keep established CLI or provider names for connectors (`gh`, `gws`, `acli`, `hf`). Name task skills for a recognizable outcome or artifact, and collections for a coherent domain. Add a qualifier when it separates real neighbors; do not enforce grammatical uniformity through cosmetic renames.
- Preserve deliberate user spellings, upstream identities, and established consumer contracts unless their migration has a concrete benefit. Before a rename, inspect project instruction consumers as well as this catalog. Keep historical records and immutable third-party source references unchanged.
- A description starts with the work the skill performs, retains distinctive tools, and distinguishes its closest neighbor when needed. Avoid vague claims such as modern, comprehensive, or best. Describe a guide's own decision branch; never copy the entire parent's description into it.
- Give a general guide an informative name such as `foundation`, `bootstrap`, `image-build`, or `code-review`; reserve tool names for tool-specific guides. Repeating the parent name makes the extra read hard to predict.
- Keep one live canonical name after migration. Update metadata, resources, consumers, contracts, generated indexes, and installed links together; keep a migration table in the change report instead of permanent alias skills or a second catalog.

| Request boundary                                                | Owners                                                                                                                                                                                           |
| --------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Browser UI, Python server, documentation site, notebook         | [web-frontend](../../web-frontend/SKILL.md), [python-web](../../python-web/SKILL.md), [documentation-site](../../documentation-site/SKILL.md), [marimo](../../python-mlops/references/marimo.md) |
| Project creation, repository upkeep, code audit                 | [project-scaffolding](../../project-scaffolding/SKILL.md), [repository-maintenance](../../repository-maintenance/SKILL.md), [repository-review](../../repository-review/SKILL.md)                |
| Task handoff, embedded application prompt, sustained agent work | [task-prompts](../../task-prompts/SKILL.md), [prompt-design](../../prompt-design/SKILL.md), [agent-loops](../../agent-loops/SKILL.md)                                                            |
| Configure coding hosts, connect MCP, implement protocols        | [agent-harnesses](../../agent-harnesses/SKILL.md), [mcp-setup](../../mcp-setup/SKILL.md), [agent-protocols](../../agent-protocols/SKILL.md)                                                      |
| Test code, assess user journeys, evaluate stochastic agents     | [python-testing](../../python-testing/SKILL.md), [quality-assurance](../../quality-assurance/SKILL.md), [agent-evaluation](../../agent-evaluation/SKILL.md)                                      |

## Entrypoints and guides

- Every discovered package has exactly one root `SKILL.md`. Never nest another `SKILL.md` inside it: hosts can recursively expose it at startup. Keep dormant independently installable packages outside discovery roots.
- Root frontmatter requires `name`, a concise `description`, `license: MIT`, and `metadata.kind` plus existing author/provenance/dates. Name matches the directory and uses lowercase hyphenated words. Descriptions state capability and triggers; preserve distinctive tool names and useful boundaries. Maximum 180 characters; a catalog average around 100 is advisory, not a reason to remove useful triggers.
- A lightweight guide is `references/<name>.md`. A guide with owned files is `references/<name>/GUIDE.md`, with its own `references/`, `templates/`, or `scripts/` as needed. Guide frontmatter contains only `name` and `description`; name matches the filename stem or containing directory for `GUIDE.md`. Preserve upstream documents with their original license/provenance as references, not generated first-party guides.
- Parent routing lives between `<!-- guides:start -->` and `<!-- guides:end -->` under `## Task guides`. `mise run format:skills` generates the links and task cues from guide metadata; `check:skills` rejects stale indexes. Do not maintain a second `metadata.guides` list.
- A parent links each guide directly. A guide links its own resources using document-relative paths; the parent need not repeat those files. Every resource must be reachable from the entrypoint. Disconnected cycles do not count as disclosure; scripts and output templates cannot serve as hidden instruction routers.
- Load parent → selected guide → required resource. Avoid further instructional chains; prefer directly linking the necessary supporting document from its owning guide. Never read all children merely because the parent was selected. Jump to an explicitly known guide when shared prerequisites are not needed.
- Keep substantive instructions in one place. Shared procedure belongs in the parent only when every mode requires it; retain essential authority boundaries in guides that support direct entry.
- A single procedure belongs directly in the root; a one-guide router needs a concrete conditional-reading benefit. Keep its examples and templates as resources. Add a collection only when there are multiple useful choices, not to reserve space for hypothetical future tools.

## Size and budgets

- Collection routers should usually cost 300–600 estimated body tokens; ordinary procedures should usually stay below 1,500. These are review targets, not padding requirements or automatic deletion rules. Hard ceiling: 500 lines per entrypoint/guide. Put detailed examples, configurations, and output templates in resources.
- Global instructions + discovery and local instructions + discovery must each stay **below 5,000**, independently. Exactly the limit fails. Combined discovery is informational. Keep headroom for relevant local skills.
- Keep room within each scope for useful instructions and skill descriptions. Recheck the actual project's local catalog before admitting a global entry.
- `dot agent context --source . --project . --check` measures authored inputs; omit `--source` for installed shared roots. Estimates use `ceil(characters / 4)` with names, descriptions, and portable paths. Nested skill files count too. Host/plugin catalogs and ancestor instructions outside selected roots are excluded; verify the actual host prompt separately.
- `mise run report:skills` summarizes category counts, headroom, large task loads, and lexical routing diagnostics. Add `-- --details` for category members and every guide and probe. Resource reads and command output can add more task context. Measure startup and realistic task loads separately; reducing one does not prove the other improved.

## Resources and portability

- References explain decisions or procedures; templates/assets are copied or adapted into output; scripts perform demonstrated deterministic work. Create folders only when they contain useful files. Executables belong under a `scripts/` directory, including one owned by a guide.
- Validate all reachable instructional Markdown for missing or unsafe links. Templates may refer to generated destinations, but must still reject unsafe local URI schemes. Resolve links relative to the containing document.
- Promotion: move the guide and owned resources into a new package, rename its entrypoint to `SKILL.md`, add root metadata, fix relative links, and update callers, manifest, routing probes, and installation declarations. Remove the former guide rather than keeping two copies. Test the resulting package independently before claiming standalone portability.
- A first-party catalog may link across global/local owners. Before publishing one package independently, bundle necessary resources or replace sibling paths with available skill-name routing; validate a disposable copy containing only that package.
- Preserve useful procedures during consolidation, including defaults, non-obvious failures, and authorization boundaries. Git history records obsolete names; do not keep duplicate live instructions merely as aliases.
- Preserve corrections with their reason and scope: durable personal preferences belong in global AGENTS.md, repository invariants in project AGENTS.md, reusable procedures in the owning skill or guide, and detailed evidence in references or existing memory. Keep a prerequisite or non-obvious failure warning before the action it constrains; a reference is sufficient only when the agent can recognize its loading condition. Update memory only when the user explicitly requests it.

## Authoring and verification

- State what the agent should do differently. Omit generic tutorials, repeated persona rules, speculative complexity, private incidents, and transient session facts. Vendor routes identify the authoritative source and personal deviations instead of copying a manual.
- Use an H1, concise intent, actionable workflow, and real gotchas. Tool-specific guidance links primary docs and its subject's release/changelog page. Verify unfamiliar commands against installed help or current primary sources.
- Use language-tagged fences, `1.` numbering, one line per paragraph, and portable paths. Metadata values are strings. Comment-capable configurations start with their official documentation URL below a schema directive.
- Register root owners and required tools in `skills/contracts.json`; give each a primary routing case in `dot/testdata/skills/routing-boundaries.json`. Guide selection belongs in the same fixture when a case needs a specialist route. No separate guide manifest is required.
- Validate formatting, metadata, reachable resources, links, budget boundaries, and changed installation behavior. Test explicit tools, unnamed task requests, neighboring tasks, no-route requests, and promotion. A lexical rank is diagnostic; [adoption checks](adoption-check.md) distinguish static proof from observed host behavior.
- Keep usage review local and requested; count observed skill loads, not catalog mentions. Do not add a telemetry service or automatically retire unobserved skills.

## Host metadata

Add `agents/openai.yaml` only for needed interface metadata, dependencies, or an explicit invocation policy. Link it from the entrypoint; use supported fields and preserve existing user-selected invocation behavior. Host-specific selection settings do not establish cross-host discovery behavior.
