# Zensical Configuration

Options beyond the [starter](../templates/zensical.toml) under `[project]` in `zensical.toml` (check the locked [plugin list](https://zensical.org/docs/compatibility/mkdocs/plugins/) and [releases](https://github.com/zensical/zensical/releases) first).

## Theme features

Adjust `[project.theme].features` only when needed ([navigation flags](https://zensical.org/docs/setup/navigation/)):

- **Instant nav requires `site_url`**: `navigation.instant` persists the search index; drop it for offline builds.
- **Tabs & conflicts**: `navigation.tabs` requires ≥3 top-level sections (>1220 px). `navigation.indexes` conflicts with `toc.integrate`; `navigation.prune` conflicts with `navigation.expand`.
- **Copy as Markdown**: `content.action.copy` renders only on pages matched by `llmstxt.sections`.
- **Scope link previews**: prefer targeted previews over global `navigation.instant.preview` (avoids raw Mermaid tooltips and hero `.md-button` CTAs):
  ```toml
  [[project.markdown_extensions.zensical.extensions.preview.configurations]]
  targets.include = ["reference/*", "glossary.md"]
  ```

## Native plugins

Built into `0.1.1` unless noted (`gen-files`/`hooks` Python plugins never execute; `exclude_docs`/`draft_docs`/`not_in_nav` need `>=0.0.70`; enable under `[project.plugins.<name>]`, unknown keys error):

- `llmstxt` / `social`: `llms.txt` + page copies (`sections` globs) and `.cache/` Open Graph cards.
- `privacy` / `optimize` (`0.0.74+`): vendor Google Fonts/Mermaid locally—always scope `assets_include` (unscoped pulls ~2 MB of unused players/Pyodide into `.cache/plugin/privacy`); `optimize` compresses PNG (`pngquant` on `PATH`) + JPEG.
- `redirects`: `redirect_maps` for pages/anchors (`"old.md#a" = "new.md#b"`), with page-level fallbacks on splits.
- `blog` / `rss` / `tags`: `docs/blog/posts/` + `.authors.yml`, `match_path` RSS, and `<!-- material/tags -->`.
- `mkdocstrings` / `api-autonav`: `::: package.module` + module pages (`uv add --dev mkdocstrings-python`); unresolved `[text][id]` fails strict autorefs:
  ```toml
  [project.plugins.mkdocstrings.handlers.python]
  paths = ["src"]

  [project.plugins.api-autonav]
  modules = ["src/<package>"] # appends "API Reference" to nav without importing
  ```
- `markdown-exec` / `offline` / `mike`: `markdown-exec` runs fences at build time (never on untrusted content); `offline` builds `file://` search (disable instant nav/analytics/repo/comments); `mike` uses `squidfunk/mike` + `mkdocs.yml`.

## Look and feel

- **Variant & palette**: `"modern"` for new sites (`"classic"` for MkDocs CSS compat); `custom` palette under `[data-md-color-scheme="default"]` (see `fmind.css`).
- **Fonts & language**: `font = false` blocks external requests; override `--md-text-font`/`--md-code-font` (never `font-family`). Search UI stays English regardless of `theme.language`.

## Customization

1. **CSS / JS**: register `docs/` files in `extra_css`/`extra_javascript` (`type = "module"` for ESM) and wrap instant-nav re-init in `document$.subscribe(() => { ... })`.
1. **Templates & partials**: set `theme.custom_dir = "overrides"`, extend `base.html` in `overrides/main.html` (`announce`, `extrahead`, `scripts`, `content`, `footer` with `{{ super() }}`), or replace `overrides/partials/<name>.html` (`comments.html`), `overrides/404.html`, and `template` frontmatter (MiniJinja blocks Python calls).

## Analytics, privacy, & shared content

- Pair `[project.extra.analytics]` with `[project.extra.consent]` and `<a href="#__consent">` in `copyright`; audit Google Fonts, unpkg Mermaid, and custom MathJax/KaTeX against [`privacy`](#native-plugins).
- **Snippets / macros / Spark**: `--8<-- "path/file.py"` (`base_path`, `check_paths = true`), Jinja `extra`/YAML macros (`on_undefined = "strict"`), and `@if`/`@var`/`@use` (`catalog.toml`/`ZENSICAL_VARIANT`, Spark early access).

## Mounted portals

Mount self-contained interactive sub-apps under `site/` **after** `zensical build --clean --strict` (which wipes `site/`) inside `build:docs`, keeping generated HTML out of `docs/` so `docs.yml` deploys one unified GitHub Pages site (in Python/polyglot repos where `all` does not run `build:docs`, either invoke `mise run build:docs` in `docs.yml` or wire `build:docs` into `all`):

- **LikeC4 C4 explorer** ([likec4](../../../../diagrams-as-code/references/likec4.md)): `likec4 build --base /<slug>/architecture/ --use-hash-history --output-single-file -o site/architecture architecture`.
- **Allure 3 BDD acceptance report** ([testing/bdd](../../../../python/references/testing/references/bdd.md)): run `mise run report:bdd` (sanitized `singleFile: true` HTML) then `mkdir -p site/bdd && cp .cache/allure-report/index.html site/bdd/index.html` (never publish private or internal test data to public GitHub Pages).
- **Navigation under `--strict`**: link mounted portals via full `site_url`-rooted `nav` entries (`{ "Architecture (C4)" = "https://<owner>.github.io/<slug>/architecture/" }`, `{ "Acceptance (BDD)" = "https://<owner>.github.io/<slug>/bdd/" }`) so `zensical build --strict` never fails on missing `docs/` files and `navigation.instant` never hijacks SPA routing.

## Documentation

- [Basics](https://zensical.org/docs/setup/basics/) · [Navigation](https://zensical.org/docs/setup/navigation/) · [Data privacy](https://zensical.org/docs/setup/data-privacy/) · [Redirects](https://zensical.org/docs/setup/redirects/) · [Customization](https://zensical.org/docs/customization/)
