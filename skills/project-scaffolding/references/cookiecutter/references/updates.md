# Update Generated Projects with Cruft

Use Cruft when a generated project must receive template changes; [cookiecutter](../GUIDE.md) owns template authoring and generation semantics.

## Workflow

1. Inspect Git status, `.cruft.json`, the recorded template URL/commit/context, and skip rules. Review template hooks and extensions before rendering either revision.
1. Run Cruft as `uvx --from 'cruft==<version>' cruft`, resolving `<version>` to a reviewed exact release; the `cruft` commands below use that pinned invocation. Inspect `cruft --help` and the selected subcommand help. For a new project use `cruft create <template-url> --checkout <reviewed-commit>` into a new destination.
1. For an existing generated project, identify its actual template revision and context before `cruft link <template-url>`; linking guessed provenance can create an invalid update baseline.
1. Run `cruft check` to detect drift and inspect `cruft diff` when investigating differences. These operations may fetch or render template content; they require a trusted source.
1. Apply `cruft update` in a clean isolated candidate. Review template changes, project modifications, conflicts or reject files, and the `.cruft.json` revision together; never auto-skip a conflict.
1. Run the generated project's gate, then repeat the drift check. Rehearse with a local template repository containing two commits and a project edit that must survive the update.

## Gotchas

- `.cruft.json` is maintained state and may contain sensitive context; do not recreate it from memory or store credentials there.
- Skip rules are ownership decisions; skipping failing files to claim an update succeeded hides drift.
- Template updates can delete files, execute hooks, or change dependencies. Preserve the source worktree and review the complete candidate.

Sources: [Cruft](https://cruft.github.io/cruft/).
