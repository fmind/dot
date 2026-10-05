# Zensical Configuration

Use this reference to enable features beyond the [starter](../templates/zensical.toml). Settings live under `[project]` in `zensical.toml`; each official page also shows the `mkdocs.yml` equivalent. Verify a feature against the locked version's [plugin list](https://zensical.org/docs/compatibility/mkdocs/plugins/) and [releases](https://github.com/zensical/zensical/releases) before relying on it.

## Theme features

Add flags to `[project.theme].features`. The starter enables the recommended set; adjust only for a concrete reader need.

| Flag                                                                                            | Effect                                                                                                     | Decision                                                              |
| ----------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------- |
| `navigation.instant` (+ `.prefetch`, `.progress`)                                               | Single-page navigation that keeps the search index and prefetches on hover                                 | Default; needs `site_url`; remove for offline builds                  |
| `navigation.tabs` (+ `.sticky`)                                                                 | Top-level sections become header tabs above 1220 px                                                        | Use with three or more top-level sections                             |
| `navigation.sections`, `navigation.indexes`, `navigation.path`                                  | Grouped sidebar, section overview pages, breadcrumbs                                                       | Default; `indexes` conflicts with `toc.integrate`                     |
| `navigation.prune`                                                                              | Renders only visible navigation, shrinking HTML by a third or more                                         | Sites with hundreds of pages; conflicts with `navigation.expand`      |
| `navigation.footer`, `navigation.top`, `navigation.tracking`, `toc.follow`                      | Previous/next links, back-to-top, URL anchor tracking, TOC follows scroll                                  | Default                                                               |
| `content.code.copy`, `content.code.select`, `content.code.annotate`                             | Copy and line-selection buttons, numbered code annotations                                                 | Default                                                               |
| `content.action.edit`, `content.action.view`                                                    | Edit and view-source buttons derived from `repo_url` and `edit_uri`                                        | Default for public repositories                                       |
| `content.action.copy`                                                                           | Copy as Markdown button                                                                                    | Requires the `llmstxt` plugin; the page must be in a `sections` entry |
| `content.tabs.link`, `content.tooltips`, `content.footnote.tooltips`                            | Linked tab selection across pages, rich tooltips, inline footnotes                                         | Default                                                               |
| `navigation.instant.preview`                                                                    | Hover previews for header links                                                                            | Prefer per-page targets with `zensical.extensions.preview` (below)    |
| `header.autohide`, `announce.dismiss`, `navigation.expand`, `toc.integrate`, `search.highlight` | Hide header on scroll, dismissible announcement, expanded or integrated navigation, highlight search terms | Optional; the announcement itself needs an `announce` block override  |

Enable instant previews for selected targets instead of every link:

```toml
[[project.markdown_extensions.zensical.extensions.preview.configurations]]
targets.include = ["reference/*", "glossary.md"]
```

## Native plugins

These replace MkDocs plugins without extra packages unless noted. Enable a plugin with an empty table, such as `[project.plugins.tags]`; supported plugins reject unknown settings.

| Plugin                                | Since          | Use                                                                                                                      |
| ------------------------------------- | -------------- | ------------------------------------------------------------------------------------------------------------------------ |
| `search`                              | 0.0.3          | Built-in client-side search; language follows `theme.language`; exclude pages with `search.exclude: true` front matter   |
| `llmstxt`                             | 0.0.67         | `llms.txt`, Markdown page copies, optional `full_output`; `sections` is required; glob patterns allowed                  |
| `social`                              | 0.0.67         | Open Graph and Twitter cards rendered at build time; front matter can override `social.cards`; cached in `.cache/`       |
| `minify`                              | 0.0.58         | `minify_html`, plus listed JS and CSS files and inline `<script>`/`<style>`                                              |
| `redirects`                           | 0.0.58         | `redirect_maps` for moved pages and anchors (`"old.md#a" = "new.md#b"`); splitting a page keeps a page-level fallback    |
| `tags`                                | 0.0.58         | Front matter `tags`, search filtering, listings where `<!-- material/tags -->` appears; icons via `[project.extra.tags]` |
| `blog`, `rss`                         | 0.0.64, 0.0.65 | Posts in `docs/blog/posts/` with dates, drafts, categories, `.authors.yml`; RSS and JSON feeds (`match_path`)            |
| `mkdocstrings`, `autorefs`            | 0.0.11, 0.0.22 | Python API docs from `::: package.module`; install `mkdocstrings-python`; set `handlers.python.paths = ["src"]`          |
| `api-autonav`, `autoapi`              | 0.0.66         | Generate one reference page per module plus navigation; needs `mkdocstrings-python`                                      |
| `meta`, `awesome-nav`, `literate-nav` | 0.0.58         | Shared `.meta.yml` front matter; per-directory `.nav.yml`; Markdown `SUMMARY.md` navigation                              |
| `macros`, `table-reader`              | 0.0.40, 0.0.41 | Jinja variables and macros in Markdown; CSV/Excel tables via `{{ read_csv('data.csv') }}`                                |
| `markdown-exec`                       | 0.0.47         | Executes fenced code during the build; install `markdown-exec[ansi]`; never enable for untrusted content                 |
| `glightbox`                           | 0.0.35         | Image lightbox with optional captions                                                                                    |
| `gh-admonitions`, `callouts`          | 0.0.67, 0.0.62 | GitHub `> [!NOTE]` alerts and Obsidian callouts rendered as admonitions                                                  |
| `exclude`                             | 0.0.67         | Remove source files from the site by glob or regex                                                                       |
| `offline`                             | 0.0.3          | File-system browsing with working search; disable instant navigation, analytics, repository facts, and comments          |
| `mike`                                | 0.0.30         | Versioned deployments through the `squidfunk/mike` fork and `mkdocs.yml`; native versioning is planned                   |

Python API reference that builds from source without importing it:

```toml
[project.plugins.mkdocstrings.handlers.python]
paths = ["src"]

[project.plugins.api-autonav]
modules = ["src/<package>"]
```

Add `mkdocstrings-python` with `uv add --dev mkdocstrings-python`; `api-autonav` appends an "API Reference" section to an explicit `nav`. With mkdocstrings enabled, unresolved `[text][identifier]` references fail strict builds as autorefs.

## Look and feel

- **Variant**: `variant = "modern"` for new sites; `classic` reproduces Material for MkDocs and its custom CSS.
- **Palette**: the starter's three entries follow the system scheme first. Named colors use `primary`/`accent` (`indigo`, `blue`, `teal`, …); brand colors use `custom` plus CSS variables in `extra.css`. Tune dark mode with `[data-md-color-scheme="slate"] { --md-hue: 210; }`.
- **Fonts**: `[project.theme.font]` takes Google Fonts names; `font = false` uses system fonts without external requests. Override with `--md-text-font` and `--md-code-font`, never `font-family`.
- **Icons**: Lucide, Material Design, FontAwesome, Octicons, and Simple Icons are bundled; search the [icon reference](https://zensical.org/docs/authoring/icons-emojis/). Custom SVG sets go in `overrides/.icons/<set>/` with `pymdownx.emoji.options.custom_icons`.
- **Footer and header**: `[[project.extra.social]]` links, `copyright`, `extra.generator = false` to remove "Made with Zensical" (upstream asks to keep it), and `extra.homepage` for the logo target.
- **Language**: `theme.language` (60+ locales) and `[project.extra].alternate` for a language selector; search UI is English-only for now.

## Customization

1. **CSS and JavaScript**: list files under `docs/` in `extra_css` and `extra_javascript`. Initialize scripts inside `document$.subscribe(() => { ... })` so they rerun after instant navigation; use `{ path = "...", type = "module" }` for modules.
1. **Template overrides**: set `theme.custom_dir = "overrides"`, extend `base.html` from `overrides/main.html`, and override blocks (`announce`, `extrahead`, `scripts`, `content`, `footer`) with `{{ super() }}` when adding. Templates use MiniJinja: no arbitrary Python calls.
1. **Partials**: replace `overrides/partials/<name>.html`, such as `comments.html` for Giscus; add per-page layouts with the `template` front matter key and an `overrides/404.html`.

## Analytics and privacy

- `[project.extra.analytics]` supports Google Analytics and the "Was this page helpful?" feedback widget; pair it with `[project.extra.consent]` and a `<a href="#__consent">` link in `copyright`.
- **List third-party hosts in privacy reviews**: Mermaid loads from unpkg, MathJax/KaTeX need explicit `extra_javascript`, and Google Fonts load by default. List these hosts in a privacy review; the upstream `privacy` plugin is planned but not yet available.

## Shared and variant content

- **Snippets**: `--8<-- "path/file.py"` with `base_path`, `check_paths = true`, and section markers (`--8<-- "file.py:section"`) to show tested code.
- **Macros**: Jinja variables from `extra` or YAML files; set `on_undefined = "strict"` to fail on typos.
- **Directives** (`@if`, `@var`, `@use` with `catalog.toml` and `ZENSICAL_VARIANT`): early access through Zensical Spark only; not generally available.

## Documentation

- [Basics](https://zensical.org/docs/setup/basics/) · [Navigation](https://zensical.org/docs/setup/navigation/) · [Colors](https://zensical.org/docs/setup/colors/) · [Fonts](https://zensical.org/docs/setup/fonts/) · [Logo and icons](https://zensical.org/docs/setup/logo-and-icons/)
- [Search](https://zensical.org/docs/setup/search/) · [Blog](https://zensical.org/docs/setup/blog/) · [Tags](https://zensical.org/docs/setup/tags/) · [Redirects](https://zensical.org/docs/setup/redirects/) · [Offline](https://zensical.org/docs/setup/offline/) · [Data privacy](https://zensical.org/docs/setup/data-privacy/) · [Analytics](https://zensical.org/docs/setup/analytics/)
