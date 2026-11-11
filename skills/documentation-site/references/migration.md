# Migration

Move MkDocs, Material for MkDocs, or Hugo sites to Zensical without touching production until the new build is verified; publishing requires separate authorization.

## Inventory first

1. **Capture the published surface**: paths, anchors, nav, assets, canonical URLs, redirects, feeds, hosting prefix, and sitemap or `find site -name '*.html'`.
1. **Audit build customizations**: plugins, Markdown extensions, overrides, hooks, and CI steps against the [supported plugin list](https://zensical.org/docs/compatibility/mkdocs/plugins/) (unsupported plugins are silently ignored). Compatibility plugins (`nav-weight`, `markdownextradata`, `include-markdown`) bridge migrations; write new content with explicit `nav`, `macros`, and snippets.

## MkDocs and Material for MkDocs

Zensical reads `mkdocs.yml` directly for incremental migration:

1. **Build unchanged `mkdocs.yml`**: `uv add --dev 'zensical>=0.1.1,<0.2'` and run `uv run zensical build --clean --strict`.
1. **Preserve Material styling if needed**: set `theme.variant: classic` when custom CSS/JS expects Material DOM; adopt `modern` separately.
1. **Diff outputs**: compare pages, nav, search, blog/tags/API pages, and redirects against MkDocs.
1. **Replace unsupported features**: `gen-files` → `api-autonav`/`autoapi` or committed files; `hooks` → native plugins or overrides; `mkdocs gh-deploy` → [docs.yml](../templates/docs.yml); `get-deps` → explicit deps. `exclude_docs`, `draft_docs`, and `not_in_nav` require Zensical ≥0.0.70; `remote_branch` and `remote_name` have no equivalent.
1. **Port overrides to MiniJinja**: Material 9.6.18+ templates mostly work; replace Python calls with filters/tests.
1. **Use the mike fork for versions**: `git+https://github.com/squidfunk/mike.git` with `mkdocs.yml`.
1. **Cut over**: switch tasks and CI to `zensical`, drop MkDocs deps, and convert `mkdocs.yml` to `zensical.toml` only if simpler.

## Hugo

1. **Scaffold and port content**: scaffold in scratch, then move prose into `docs/`, replacing shortcodes/templates with Zensical Markdown or generated files.
1. **Map front matter and URLs**: keep `title` and `description`; rename `_index.md` → `index.md`, `weight` → `nav`, `tags` → `tags` plugin. Map Hugo `aliases` (`/posts/old/`) to source `.md` paths in `redirect_maps`, and set `blog` `post_url_format` when default `{date}/{slug}` would alter published URLs.
1. **Move static assets**: place under `docs/` and keep the hosting prefix in `site_url`.
1. **Verify paths and retire Hugo**: diff old/new URLs (including trailing slashes), pass `--strict` + visual review, then remove Hugo config, themes, tasks, and CI.

## Documentation

- [Migrate from MkDocs](https://zensical.org/docs/compatibility/mkdocs/migration/) · [Plugin compatibility](https://zensical.org/docs/compatibility/mkdocs/plugins/) · [Versioning with mike](https://zensical.org/docs/compatibility/mkdocs/mike/) · [Redirects](https://zensical.org/docs/setup/redirects/)
