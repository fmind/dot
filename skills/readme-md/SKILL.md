---
name: readme-md
description: "Write a clear README.md for humans with purpose, setup, authentication, and verified usage. Use when creating or restructuring a repository README."
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/readme-md
  created: "2026-09-05"
  updated: "2026-09-05"
---

# Write README.md

Give a new reader enough context to understand the project, install it, and reach the first useful result. [update-docs](../update-docs/SKILL.md) synchronizes existing documentation with source; [agents-md](../agents-md/SKILL.md) owns instructions for agents.

## Workflow

1. **Read the project**: inspect the existing README, entry points, manifests, supported platforms, installation path, and project rules before choosing sections.
1. **Lead with purpose**: explain what the project does, who it serves, and its current capability in a short opening; show a concrete example when it helps.
1. **Make setup reproducible**: state prerequisites, installation, configuration, and authentication in execution order; document variable names and credential storage without real secrets.
1. **Show useful usage**: give the shortest working example, expected result, and links to deeper user guides; verify commands against current help or source.
1. **Add only relevant navigation**: troubleshooting, limitations, support, documentation, and license links. Preserve the author's voice and existing public anchors.
1. **Verify**: check relative links, commands, and rendering with the repository's formatter, link checker, and build; mark external prerequisites that were not exercised.

## Gotchas

- **Audience**: repository maintenance tasks, aliases, agent rules, and contributor workflows belong in `AGENTS.md`, skills, or contributor docs; follow any narrower project README scope.
- **No duplicated manuals**: link to canonical docs for long tutorials or generated CLI references; omit badges and sections that provide no decision-useful information.
- **Honest status**: setup success, tests, hosted CI, deployment, and a published release are separate claims.
- **Markdown**: keep paragraphs unwrapped, use `1.` for ordered lists, label every code fence, and prefer relative links within the repository.

## Documentation

- [GitHub README guidance](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-readmes)
- Companion skills: [agents-md](../agents-md/SKILL.md), [update-docs](../update-docs/SKILL.md), [dprint](../dprint/SKILL.md).
