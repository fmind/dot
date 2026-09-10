---
name: cruft
description: Track and update Cookiecutter templates with Cruft. Use for .cruft.json provenance, template drift checks, linking existing projects, and update conflicts.
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/cruft
  created: "2026-09-10"
  updated: "2026-09-10"
---

# Cruft

Use Cruft when a generated project must receive template changes; [cookiecutter](../cookiecutter/SKILL.md) owns template authoring and generation semantics.

## Workflow

1. Inspect Git status, `.cruft.json`, the recorded template URL/commit/context, and skip rules. Review template hooks and extensions before rendering either revision.
1. Inspect `uvx cruft --help` and the selected subcommand help. For a new project use `uvx cruft create <template-url> --checkout <reviewed-commit>` into a new destination.
1. For an existing generated project, identify its actual template revision and context before `uvx cruft link <template-url>`; linking guessed provenance can create an invalid update baseline.
1. Run `uvx cruft check` to detect drift and inspect `uvx cruft diff` when investigating differences. These operations may fetch or render template content; they require a trusted source.
1. Apply `uvx cruft update` in a clean isolated candidate. Review template changes, project modifications, conflicts or reject files, and the `.cruft.json` revision together; never auto-skip a conflict.
1. Run the generated project's gate, then repeat the drift check. Rehearse with a local template repository containing two commits and a project edit that must survive the update.

## Gotchas

- `.cruft.json` is maintained state and may contain sensitive context; do not recreate it from memory or store credentials there.
- Skip rules are ownership decisions; skipping failing files to claim an update succeeded hides drift.
- Template updates can delete files, execute hooks, or change dependencies. Preserve the source worktree and review the complete candidate.

## Official Skills

No consumer Agent Skill was found in the inspected [cruft/cruft](https://github.com/cruft/cruft) repository on 2026-09-10. Use the official documentation below; community packages are not upstream endorsements.

## Documentation

- [Cruft workflow and commands](https://cruft.github.io/cruft/) · [Source](https://github.com/cruft/cruft)
