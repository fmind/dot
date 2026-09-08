---
name: repository-docs
description: Create and synchronize README.md, AGENTS.md, and repository documentation against verified behavior. Use when authoring or updating repository docs.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/repository-docs
  created: "2026-09-07"
  updated: "2026-09-07"
---

# Repository Documentation

Keep human and agent documentation aligned with the implementation, with one canonical owner for every claim.

## Workflow

1. **Inventory**: locate `README.md`, root and nested `AGENTS.md`, `docs/`, generated help, and `.agents/skills/*/SKILL.md`; include any additional catalog declared by the repository.
1. **Trace behavior**: compare documentation with entry points, source, tests, manifests, mise tasks, hooks, CI, and current `--help`; verify paths, options, versions, examples, and supported behavior.
1. **Choose the audience**: use [README guidance](references/readme.md) for purpose, setup, authentication, and usage; use [AGENTS guidance](references/agents.md) for commands, constraints, invariants, and layout.
1. **Update canonical owners**: keep setup and usage in human docs, agent commands and invariants in `AGENTS.md`, and reusable procedures in skills; link instead of copying.
1. **Verify**: run the repository's documentation gate, `lychee <files>` for links, `dprint check` for markup, and the site build where applicable; inspect rendered pages after layout changes.
1. **Report**: name what changed, the source evidence and checks, and any external workflow or claim that remains unverified.

## Gotchas

- **Generated documentation**: edit its source and regenerate; never hand-edit generated output or rewrite published history as cleanup.
- **Honest status**: setup, tests, hosted CI, deployment, and publication are separate claims.
- **Local authority**: documentation work authorizes relevant reversible edits; committing, publishing, or contacting others follows the current task authority.
- **Markdown**: preserve repository conventions, public anchors, and the author's voice; never include secrets or transient session state.

## Documentation

- [GitHub README guidance](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-readmes) · [AGENTS.md](https://agents.md) · [Agent Skills](https://agentskills.io/specification)
- Companion skills: [agent-project](../agent-project/SKILL.md) (host setup), [skillify](../skillify/SKILL.md) (reusable procedures), [dprint](../dprint/SKILL.md) (formatting).
