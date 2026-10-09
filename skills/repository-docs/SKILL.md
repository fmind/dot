---
name: repository-docs
description: "Write and sync README, AGENTS.md, and repo docs with verified behavior."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/repository-docs
  created: "2026-09-07"
  updated: "2026-10-09"
---

# Repository Documentation

Keep human and agent documentation aligned with the implementation, with one canonical owner for every claim.

## Workflow

1. **Inventory**: locate `README.md`, root and nested `AGENTS.md`, `docs/`, community files such as `.github/SECURITY.md`, generated help, and `.agents/skills/*/SKILL.md`; include any additional catalog declared by the repository.
1. **Trace behavior**: compare documentation with entry points, source, tests, manifests, mise tasks, hooks, CI, and current `--help`; verify paths, options, versions, examples, and supported behavior.
1. **Choose the audience**: use [README guidance](references/readme.md) for project identity, proof of value, and the first successful use, adapting its starter for new projects; add [README assets](references/readme-assets.md) for SVG logos, illustrations, and badges. Use [AGENTS guidance](references/agents.md) for commands, constraints, invariants, and layout.
1. **Update canonical owners**: keep setup and usage in human docs, agent commands and invariants in `AGENTS.md`, and reusable procedures in skills; link instead of copying.
1. **Verify**: run the repository's documentation gate, `lychee --include-fragments <files>` for links and anchors, `dprint check` for markup, and the site build where applicable; inspect rendered pages after layout changes.
1. **Report**: name what changed, the source evidence and checks, and any external workflow or claim that remains unverified.

## Gotchas

- **Edit generated documentation at its source**: regenerate it; never hand-edit generated output or rewrite published history as cleanup.
- **Report each status claim separately**: setup, tests, hosted CI, deployment, and publication are separate claims.
- **Documentation work authorizes relevant reversible edits**: committing, publishing, or contacting others follows the current task authority.
- **Preserve conventions; exclude secrets**: preserve repository conventions, public anchors, and the author's voice; never include secrets or transient session state.

## Documentation

- [GitHub README guidance](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-readmes) · [AGENTS.md](https://agents.md) · [Agent Skills](https://agentskills.io/specification)
- Companion skills: [agent-project](../agent-project/SKILL.md) (host setup), [skillify](../skillify/SKILL.md) (reusable procedures), [dprint](../dprint/SKILL.md) (formatting), [diagrams-as-code](../diagrams-as-code/SKILL.md) (SVG illustrations and Mermaid).
