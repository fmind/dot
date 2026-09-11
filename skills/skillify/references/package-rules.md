# Package Rules

Personal authoring conventions and catalog constraints; workflow extraction lives in [skillify](../SKILL.md). `gh skill publish --dry-run` and the catalog tests validate package structure, metadata budgets, links, and fixtures; they do not prove prose quality or host behavior.

## Authoring limits

- **Admission**: create a global skill only when it captures a meaningful personal choice, a reusable procedure or artifact, a demonstrated failure worth preventing, or a useful route to maintained upstream guidance. General product knowledge alone is insufficient; the absence of an official skill does not justify a local substitute.
- **One purpose**: choose one distinct task or decision boundary, not one entrypoint per tool. Extend an existing owner or add an on-demand reference when that preserves the workflow; keep project-specific guidance in the project.
- **Useful difference**: state what a capable agent should do differently after reading the skill. Retain concrete defaults, artifacts, and failure lessons; omit product introductions, routine API tutorials, and repeated persona rules. Use the [adoption check](adoption-check.md) for borderline additions instead of assuming more instructions improve outcomes.
- **Vendor routes**: identify the official source, relevant selection, personal deviations, and a few specific pitfalls. Link to maintained guidance instead of copying its tutorial or feature inventory; review and installation follow the shared vendor policy.
- **Size**: aim for fewer than 100 lines in `SKILL.md`; the hard limit is 500. Keep bullets to one short idea and move long examples, templates, and configuration into directly linked resources.
- **Frontmatter**: `name` matches the lowercase, hyphenated directory name. `description` states capability and trigger in one sentence using "Use when ..." or an equally clear trigger; at most 240 characters, with a catalog average of 175 or less. Avoid indistinguishable descriptions.
- **Shape**: include an H1, concise intent, and an actionable workflow. Add `Gotchas` for real failure modes, `Official Skills` for vendor routing, and primary documentation or provenance when external tools or APIs are involved.
- **Defaults**: adapt stack defaults, coverage targets, and layouts to the project. Never restate the global persona or embed transient session facts, private prompts, or customer details.
- **Style**: keep commands in language-tagged fences, numbered items as `1.`, and paragraphs on one line. Paths are relative or `~`-relative; config examples use official documentation comments when their format permits.
- **Placement**: global skills are authored in the dot repository's standard `skills/` catalog; individual chezmoi declarations expose them in the real `~/.agents/skills/` directory. Project-only skills live in `.agents/skills/`. Other packages use the same directory and require their own setup on each computer; installed names must be unique.
- **Registration**: every first-party skill in this repository needs `skills/contracts.json` and a primary routing probe in `dot/testdata/skills/routing-boundaries.json`. Global skills also need an individual link declaration under `dot_agents/skills/`. Independently installed packages do not need registration here. Update inbound references and link declarations on renames or removal, then run the catalog tests and full gate.

## Catalog portability

- The first-party suite installs as one catalog and may link between packages under `skills/` and `.agents/skills/`.
- Catalog containment does not prove that one copied folder is independently distributable under the [file-reference rule](https://agentskills.io/specification#file-references).
- Before standalone publication, replace sibling links with skill-name routing or bundle the dependency, copy only that folder to a disposable directory, and validate it there.

## Direct disclosure

- Keep progressive-disclosure resources one level deep (`references/`, `templates/`, `scripts/`).
- Every resource other than host-owned `agents/openai.yaml` must be named directly by the root `SKILL.md` or by a local path in that OpenAI metadata; a nested reference does not make another file discoverable.
- Nested instructional Markdown is validated for missing or unsafe package links; output templates under `templates/` may point at destinations that exist only after materialization but still reject unsafe local schemes.
- Resolve Markdown links relative to the containing document: root links use `references/file.md`, while a reference links to a sibling as `file.md`. The repository validator uses this same document-relative rule; direct disclosure from `SKILL.md` remains a separate requirement.
- Test helpers live in a disposable directory; document required tools and side effects; keep executable code minimal and paths relative.

## `agents/openai.yaml`

- Add it only when Codex needs interface metadata or dependencies.
- Use the supported `interface`, `dependencies.tools`, and `policy` fields, mention `$skill-name` in `interface.default_prompt`, and link the file from `SKILL.md`.
