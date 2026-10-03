# Migration

Use this reference to move an existing MkDocs, Material for MkDocs, or Hugo site to Zensical. Keep the current production deployment unchanged until the new build is verified; publishing remains a separate authorized step.

## Inventory first

1. Record published paths, anchors, navigation, assets, canonical URLs, redirects, feeds, and the hosting prefix; save a sitemap or `find site -name '*.html'` listing from the current build.
1. List every plugin, Markdown extension, template override, hook, and CI step; check plugins against the [supported list](https://zensical.org/docs/compatibility/mkdocs/plugins/). Unsupported plugins are silently ignored, so a missing feature is not an error.

## MkDocs and Material for MkDocs

Zensical reads `mkdocs.yml`, so migration can be gradual and reversible:

1. Add Zensical beside MkDocs (`uv add --dev zensical`) and run `uv run zensical build --clean --strict` against the unchanged `mkdocs.yml`.
1. Set `theme.variant: classic` when custom CSS or JavaScript depends on Material's appearance; switch to `modern` later as a deliberate redesign.
1. Compare representative pages, navigation, search, generated pages (blog, tags, API reference), and redirects with the MkDocs output.
1. Replace unsupported pieces: `gen-files` with `api-autonav`/`autoapi` or committed generated files; `hooks` with supported plugins or template overrides; `exclude_docs` with the `exclude` plugin; `mkdocs gh-deploy` with the [docs.yml](../templates/docs.yml) workflow; `get-deps` with explicit dependencies. `draft_docs`, `not_in_nav`, `remote_branch`, and `remote_name` have no equivalent.
1. Port template overrides to MiniJinja: Material 9.6.18+ overrides usually work; replace Python function calls with filters and tests.
1. For `mike` versioning, install the `git+https://github.com/squidfunk/mike.git` fork and keep `mkdocs.yml`.
1. Switch local tasks and CI to `zensical`, remove MkDocs packages, then convert to `zensical.toml` only when it simplifies maintenance; `mkdocs.yml` remains supported.

## Hugo

1. Create a Zensical scaffold in a scratch directory. Move prose into `docs/`, replacing shortcodes and templates with Zensical Markdown (admonitions, tabs, snippets, cards) or explicit generated content.
1. Convert front matter selectively: `title` and `description` carry over; map section `_index.md` to `index.md`, `weight` ordering to `nav`, and `tags` to the `tags` plugin. Convert each Hugo alias URL (`/posts/old/`) to the `.md` source path it would have under `docs_dir` before adding it to `redirect_maps`. Dated posts can move to the `blog` plugin; set `post_url_format` to reproduce the old URLs, because the default `{date}/{slug}` changes them.
1. Copy static assets under `docs/` and fix image references; keep the hosting prefix in `site_url`.
1. Compare old and new paths, including trailing slashes; preserve published addresses or add tested redirects.
1. Build strictly and review rendered pages, then retire Hugo configuration, themes, tasks, and CI references once their replacement is verified.

## Documentation

- [Migrate from MkDocs](https://zensical.org/docs/compatibility/mkdocs/migration/) · [Plugin compatibility](https://zensical.org/docs/compatibility/mkdocs/plugins/) · [Versioning with mike](https://zensical.org/docs/compatibility/mkdocs/mike/) · [Redirects](https://zensical.org/docs/setup/redirects/)
