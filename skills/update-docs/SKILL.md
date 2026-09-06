---
name: update-docs
description: "Synchronize docs, README.md, AGENTS.md, and .agents/skills with repository behavior. Use when code, commands, layout, or conventions change and documentation needs updating."
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/update-docs
  created: "2026-09-02"
  updated: "2026-09-06"
---

# Update Repository Documentation

Reconcile the repository's human and agent documentation with the implementation. [readme-md](../readme-md/SKILL.md) and [agents-md](../agents-md/SKILL.md) own writing conventions; this workflow owns freshness across the documentation set.

## Workflow

1. **Inventory**: locate `README.md`, root and nested `AGENTS.md`, `docs/`, wiki sources, generated help, and `.agents/skills/*/SKILL.md` with their linked resources; include another catalog location when the repository declares one.
1. **Trace the change**: compare claims with entry points, source, tests, manifests, mise tasks, hooks, CI, and current `--help`; verify paths, options, versions, examples, and supported behavior.
1. **Update each audience**: keep setup and usage in README/user docs; maintain agent commands and invariants in AGENTS; update local skill triggers, procedures, references, and required tools together.
1. **Reduce duplication**: keep one canonical explanation, link from consumers, and move reusable multi-step instructions through [skillify](../skillify/SKILL.md); preserve useful granularity and the author's voice.
1. **Verify**: run the repository's relevant docs gate; use `lychee <files>` for external links, `dprint check` for markup, and the site build where applicable. Validate local skill links/contracts and inspect rendered pages after layout changes.
1. **Report**: name what changed and why, the source evidence and checks, and any claim or external workflow that remains unverified.

## Gotchas

- **Stale claims**: correct or remove unsupported statements; a reachable URL does not verify the documented API behavior.
- **Generated documentation**: update its source and regenerate; do not hand-edit a generated changelog or rewrite published history as a cleanup step.
- **Local writes**: documentation maintenance authorizes relevant reversible edits; committing, publishing, or contacting others follows the existing session authority.
- **Historical context**: keep decisions and released behavior labeled by version; update active guidance without erasing useful evidence.

## Documentation

- [lychee](https://lychee.cli.rs) · [dprint](https://dprint.dev)
- Companion skills: [readme-md](../readme-md/SKILL.md), [agents-md](../agents-md/SKILL.md), [skillify](../skillify/SKILL.md), [project-health](../project-health/SKILL.md).
