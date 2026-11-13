# Zensical Configuration

Options beyond the [starter](../templates/zensical.toml) under `[project]` in `zensical.toml` (official pages also show `mkdocs.yml` equivalents). Check the locked version's [plugin list](https://zensical.org/docs/compatibility/mkdocs/plugins/) and [releases](https://github.com/zensical/zensical/releases) first.

## Theme features

Adjust the starter's `[project.theme].features` only for a concrete need ([navigation flags](https://zensical.org/docs/setup/navigation/)):

- **Instant navigation needs `site_url`**: `navigation.instant` persists the search index; drop it for offline builds.
- **Tabs need ≥3 top-level sections**: `navigation.tabs` appears above 1220 px.
- **Conflicting pairs**: `navigation.indexes` conflicts with `toc.integrate`; `navigation.prune` (for large sites) conflicts with `navigation.expand`.
- **Copy as Markdown needs `llmstxt`**: `content.action.copy` renders only on pages matched by `llmstxt.sections`.
- **Scope link previews**: prefer targeted previews over global `navigation.instant.preview` (exclude Mermaid-leading pages, which leak raw diagram source into hover tooltips, and hero `.md-button` CTAs):

  ```toml
  [[project.markdown_extensions.zensical.extensions.preview.configurations]]
  targets.include = ["reference/*", "glossary.md"]
  ```

## Native plugins

All run on 0.1.1 without extra packages unless noted ([plugin list](https://zensical.org/docs/compatibility/mkdocs/plugins/)). Enable via `[project.plugins.<name>]`; unknown keys error.

- `llmstxt`: generates `llms.txt`, Markdown page copies, and optional `full_output`; requires `sections` (globs allowed).
- `social`: build-time Open Graph cards (`social.cards` frontmatter overrides); cached in `.cache/`.
- `privacy`: vendors Google Fonts and Mermaid at build time and marks external links. Always scope `assets_include` (unscoped downloads ~2 MB of unused theme-referenced players/SDKs/Pyodide into `.cache/plugin/privacy`, cleared by `build --clean`).
- `optimize` (0.0.74+): compresses PNG (`pngquant` on `PATH`) and JPEG assets, including privacy downloads.
- `redirects`: `redirect_maps` for moved pages and anchors (`"old.md#a" = "new.md#b"`), with page-level fallbacks on splits.
- `blog`, `rss`, `tags`: dated posts in `docs/blog/posts/` with drafts, categories, and `.authors.yml`; RSS via `match_path`; tag indexes at `<!-- material/tags -->`.
- `mkdocstrings`, `api-autonav`: Python API docs from `::: package.module` and per-module pages (`uv add --dev mkdocstrings-python`). Unresolved `[text][id]` links fail strict builds as autorefs:

  ```toml
  [project.plugins.mkdocstrings.handlers.python]
  paths = ["src"]

  [project.plugins.api-autonav]
  modules = ["src/<package>"] # appends "API Reference" to explicit nav without importing package
  ```

- `markdown-exec`: runs code fences at build time; never enable on untrusted content.
- `offline`: local `file://` browsing with search; disable instant nav, analytics, repo facts, and comments.
- `mike`: versioned docs via `squidfunk/mike` fork and `mkdocs.yml` until native versioning ships.

## Look and feel

- **Variant**: `"modern"` for new sites; `"classic"` preserves Material for MkDocs CSS compatibility.
- **Brand colors**: `custom` palette with CSS variables under `[data-md-color-scheme="default"]` (like starter `fmind.css`).
- **Fonts**: `font = false` avoids external requests; override via `--md-text-font` and `--md-code-font`, never `font-family`.
- **Language**: search UI stays English regardless of `theme.language`.

## Customization

1. **CSS / JS**: register `docs/` paths in `extra_css` / `extra_javascript` (`{ path = "...", type = "module" }` for ES modules); hook `document$.subscribe(() => { ... })` so scripts re-init on instant navigation.
1. **Templates & partials**: set `theme.custom_dir = "overrides"`, extend `base.html` in `overrides/main.html` (`announce`, `extrahead`, `scripts`, `content`, `footer` with `{{ super() }}`), or replace `overrides/partials/<name>.html` (`comments.html` for Giscus), `overrides/404.html`, and per-page `template` frontmatter. MiniJinja blocks arbitrary Python calls.

## Analytics and privacy

- Pair `[project.extra.analytics]` (Google Analytics + feedback widget) with `[project.extra.consent]` and `<a href="#__consent">` in `copyright`.
- **Audit third-party hosts**: Google Fonts (default), unpkg Mermaid, and custom MathJax/KaTeX `extra_javascript` contact external hosts unless covered by [`privacy`](#native-plugins).

## Shared and variant content

- **Snippets**: `--8<-- "path/file.py"` or `"file.py:section"` with `base_path` and `check_paths = true`.
- **Macros**: Jinja data from `extra` or YAML; set `on_undefined = "strict"`.
- **Directives** (`@if`, `@var`, `@use` + `catalog.toml` / `ZENSICAL_VARIANT`): Zensical Spark early access only.

## Documentation

- [Basics](https://zensical.org/docs/setup/basics/) · [Navigation](https://zensical.org/docs/setup/navigation/) · [Colors](https://zensical.org/docs/setup/colors/) · [Fonts](https://zensical.org/docs/setup/fonts/) · [Logo and icons](https://zensical.org/docs/setup/logo-and-icons/)
- [Search](https://zensical.org/docs/setup/search/) · [Blog](https://zensical.org/docs/setup/blog/) · [Tags](https://zensical.org/docs/setup/tags/) · [Redirects](https://zensical.org/docs/setup/redirects/) · [Offline](https://zensical.org/docs/setup/offline/) · [Data privacy](https://zensical.org/docs/setup/data-privacy/) · [Analytics](https://zensical.org/docs/setup/analytics/)
