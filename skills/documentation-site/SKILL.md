---
name: documentation-site
description: "Build Zensical docs and course sites: navigation, API docs, Pages, MkDocs/Hugo migration."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/documentation-site
  created: "2026-09-16"
  updated: "2026-10-06"
---

# Documentation Sites

Use Zensical as the default static site generator for project documentation, courses, and blogs; keep an existing generator only when the project depends on it or the user asks. [course-development](../course-development/SKILL.md) owns learning design and executable labs; [repository-docs](../repository-docs/SKILL.md) owns README and AGENTS consistency.

## Workflow

1. **Inspect the project**: keep existing content, URLs, and publication rules. For an MkDocs or Hugo site, follow [migration](references/migration.md) instead of scaffolding over it.
1. **Bootstrap with a locked dependency**: check the [latest release](https://github.com/zensical/zensical/releases), then add it as a dev dependency so `uv run` and `uv sync --locked` include it. Skip `uv init` in an existing Python project; run `zensical new` in a scratch directory when `docs/` or `zensical.toml` already exists, because it never overwrites files.
   ```bash
   uv init --bare <slug> && cd <slug>
   uv add --dev zensical
   uv run zensical new .
   ```
1. **Apply the starter**: replace the generated files with the [zensical.toml](templates/zensical.toml), [index.md](templates/index.md) as `docs/index.md`, [extra.css](templates/extra.css) as `docs/stylesheets/extra.css`, and [abbreviations.md](templates/abbreviations.md) as `includes/abbreviations.md`; delete `docs/markdown.md`. Fill every `<placeholder>`, set the real `site_url` with its hosting prefix, and drop unused sections. The starter enables instant navigation, Copy as Markdown, `llms.txt`, social cards, a glossary, checked snippets, and minified HTML; [configuration](references/configuration.md) explains each feature and the optional ones (blog, tags, redirects, API reference, versions, offline).
1. **Write under `docs/`**: one H1 per page, explicit `nav`, a section `index.md` for overviews, relative `.md` links, and a `description` in front matter for search and social cards. Use [authoring](references/authoring.md) for page types and syntax, and the [lesson template](templates/lesson.md) for courses.
1. **Wire tasks and ignores**: merge [mise.toml](templates/mise.toml) into the task graph and add `site/` and `.cache/` to `.gitignore`. Use [dprint](../dprint/SKILL.md) for Markdown and [python-stack](../python-stack/references/foundation/GUIDE.md) for executable examples.
1. **Validate**: `uv run --locked zensical build --clean --strict` must print `No issues found` and exit 0. Preview with `uv run --locked zensical serve` (default `localhost:8000`) and check navigation, search, both palettes, a 390 px viewport, keyboard use, and code copy; use [playwright](../playwright/SKILL.md) for screenshots. Run lesson code and external links separately.
1. **Publish**: replace the generated `.github/workflows/docs.yml` with the pinned [docs.yml](templates/docs.yml), which builds every pull request strictly and deploys `main` to GitHub Pages; [github-actions](../github-actions/references/ci-cd/GUIDE.md) owns pins and audits. Enabling Pages or deploying needs publication authority.

## Gotchas

- **Diagnostics come first**: a strict failure prints the file, line, and column, then a Python traceback; read the head of the output.
- **Strict mode has gaps**: it catches missing pages, anchors, snippets (`check_paths`), and unresolved autorefs, but unclosed fences and unknown icon shortcodes build silently. Review the rendered pages.
- **`site_url` is load-bearing**: `llmstxt` aborts without it; instant navigation, previews, and the sitemap degrade; a wrong prefix breaks social card and `llms.txt` links.
- **Unsupported plugins are silently ignored**: Zensical never runs MkDocs plugin code. Check the [plugin list](https://zensical.org/docs/compatibility/mkdocs/plugins/) for the locked version before relying on one. `gen-files`, `hooks`, `exclude_docs`, `draft_docs`, and `not_in_nav` are unsupported.
- **Check features before enabling them**: some theme features exclude each other, offline builds drop several, and fonts, Mermaid, and analytics contact third parties; check [configuration](references/configuration.md) before enabling one.
- **Some layouts and modes are unsupported**: `docs_dir` cannot be `.`; uv's symlink link mode is unsupported; `serve` has no strict mode, and a busy port fails with `Address already in use` (pass `-a 127.0.0.1:<port>`).
- **Keep Zensical locked**: Zensical is pre-1.0 (0.0.x) and releases often; keep `uv.lock` committed, upgrade with `uv lock --upgrade-package zensical`, and rebuild `--clean`. The CI template stays cache-free as upstream advises. Tested on 0.0.68.
- **Preserve existing site branding**: the starter applies [fmind/theme](https://github.com/fmind/theme) tokens to the light scheme and Google Sans fonts. Preserve an existing site's identity; follow [fmind-visuals](../fmind-visuals/SKILL.md) for Fmind logos and assets.

## Documentation

- [Get started](https://zensical.org/docs/get-started/) · [Create a site](https://zensical.org/docs/create-your-site/) · [Configuration](https://zensical.org/docs/setup/basics/) · [Authoring](https://zensical.org/docs/authoring/markdown/)
- [Validation](https://zensical.org/docs/setup/validation/) · [Plugins](https://zensical.org/docs/compatibility/mkdocs/plugins/) · [Customization](https://zensical.org/docs/customization/) · [Publishing](https://zensical.org/docs/publish-your-site/)
- Source: [zensical/zensical](https://github.com/zensical/zensical) · [zensical/docs](https://github.com/zensical/docs) · Releases: [Zensical](https://github.com/zensical/zensical/releases)
- Official skills: none upstream in `zensical/zensical` or `zensical/docs` (checked 2026-10-03). [Zensical Studio](https://zensical.org/studio) (VS Code) adds a preview, formatter, linter, and link refactoring for Zensical and MkDocs projects.
