# Authoring and Migration

Use this reference for richer Markdown or an existing documentation site; [course-development](../../course-development/SKILL.md) owns lesson structure and learner assessment.

## Authoring

- Separate tutorials, task guides, reference, and explanations by the reader's goal; keep course navigation in prerequisite order.
- Use one H1 per page and stable headings. Link to source Markdown, including explicit heading anchors when useful, so the builder can validate targets.
- Keep admonitions for decisions and warnings; put essential steps in the normal reading order. Preserve four-space indentation inside admonitions and tabs when formatting.
- The generated configuration enables admonitions, details, fenced code, content tabs, and Mermaid. Retain the corresponding extension settings when trimming it.
- Include tested source through supported snippets when practical. Do not make ordinary documentation builds execute untrusted code; run examples in their own bounded test task.
- Add Python API documentation only when useful. Check Zensical's current mkdocstrings compatibility and handler requirements, or retain an existing pdoc build instead of replacing it implicitly.
- Preview the exact output before accepting typography, math, diagrams, images, or responsive tables; a successful build does not establish accessibility.

## Hugo migration

1. Record current published paths, anchors, navigation, assets, canonical URLs, and redirects before changing the publisher.
1. Create a Zensical scaffold separately. Move prose into `docs/`, replacing Hugo shortcodes and templates with supported Markdown or explicit generated content.
1. Convert front matter selectively; map section indexes to `index.md`, page ordering to `project.nav`, and image references to copied assets.
1. Compare old and new output paths, including trailing slashes and the hosting prefix. Preserve published addresses or implement tested redirects supported by the chosen host or Zensical release.
1. Build strictly, check links and representative rendered pages, then retire Hugo configuration, tasks, theme dependencies, and CI references once their replacement is verified. Publishing remains a separate authorized step.

## MkDocs migration

Zensical accepts MkDocs configuration, so first build the existing configuration and compare output. Inspect every plugin against the [compatibility list](https://zensical.org/docs/compatibility/mkdocs/plugins/); convert to `zensical.toml` only when it improves maintenance. Configuration compatibility does not imply arbitrary Python plugin execution.
