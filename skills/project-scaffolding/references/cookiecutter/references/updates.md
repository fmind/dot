# Update Generated Projects with Cruft

Use Cruft when a generated project must receive template changes; [cookiecutter](../GUIDE.md) owns template authoring and generation semantics.

## Workflow

1. **Inspect state before rendering**: Git status, `.cruft.json`, the recorded template URL/commit/context, and skip rules. Resolve the target to an immutable commit and review template hooks and extensions at both the recorded and target revisions before rendering either.
1. **Pin the Cruft invocation**: run Cruft as `uvx --from 'cruft==<version>' cruft`, resolving `<version>` to a reviewed exact release; the `cruft` commands below use that pinned invocation. For a new project use `cruft create <template-url> --checkout <reviewed-commit> --no-input` into a new destination, supplying reviewed context with `--extra-context` when template defaults are insufficient.
1. **Link only verified provenance**: link only projects without `.cruft.json`. Put verified original template answers in a reviewed local Cookiecutter configuration under `default_context`, then run `cruft link <template-url> --checkout <recorded-commit> --config-file <context-config> --no-input` in an isolated candidate. Compare the resulting `context.cookiecutter` with those answers before using it as an update baseline; preserve existing provenance.
1. **Check drift from trusted sources**: run `cruft check --checkout <reviewed-commit>` to detect drift and inspect `cruft diff --checkout <reviewed-commit>` when investigating differences. These operations may fetch or render template content; they require the reviewed revisions. Inspect diagnostics on a nonzero check to distinguish drift from a source, authentication, or execution failure.
1. **Update in an isolated candidate**: apply `cruft update --checkout <reviewed-commit> --skip-apply-ask` in a clean isolated candidate. Review template changes, project modifications, conflicts or reject files, and the `.cruft.json` revision together; never auto-skip a conflict. The noninteractive flag applies the authorized candidate update; it does not authorize deployment.
1. **Gate, recheck, and rehearse**: run the generated project's gate, then repeat `cruft check --checkout <reviewed-commit>` against the same target. Rehearse with a local template repository containing two commits and a project edit that must survive the update.

## Gotchas

- **Treat `.cruft.json` as maintained state**: it may contain sensitive context; do not recreate it from memory or store credentials there.
- **Skip rules are ownership decisions**: skipping failing files to claim an update succeeded hides drift.
- **Template updates can be destructive**: they can delete files, execute hooks, or change dependencies. Preserve the source worktree and review the complete candidate.

Sources: [Cruft](https://cruft.github.io/cruft/).
