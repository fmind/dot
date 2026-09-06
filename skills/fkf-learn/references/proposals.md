# FKF Learning Proposals

Verify this recipe against the selected base and installed FKF release before use.

### 3. Stage a unified diff

For log candidates, let fkf create the deterministic proposal:

```bash
fkf learn propose
fkf learn review <proposal> --diff
```

For a concept or project change, first write an LF-terminated unified diff whose targets are only flat `wiki/*.md` or `projects/*.md` pages. Name it `.agents/tmp/learn/<sha256>.diff`, where `<sha256>` is the lowercase full-file digest. The content-addressed name binds later approval to the exact reviewed bytes:

```diff
--- a/wiki/existing.md
+++ b/wiki/existing.md
@@ -4,3 +4,4 @@
 Existing context.
+Verified finding with its evidence.
```

Use `--- /dev/null` for a new page. Do not propose deletion, rename, nested paths, generated `wiki/index.md` blocks, or any file outside those two layers.

Every promoted trace belongs in the target page's `sources:` frontmatter, preserving existing entries:

```yaml
sources:
  - ../tasks/2026-08-24/window-sources/TASKS.md#learned
```

That citation marks the trace harvested. Add a declared `relations:` entry too only when the trace should be navigable in the graph.
