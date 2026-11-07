# Zensical Configuration

Use this reference to enable features beyond the [starter](../templates/zensical.toml). Settings live under `[project]` in `zensical.toml`; each official page also shows the `mkdocs.yml` equivalent. Verify a feature against the locked version's [plugin list](https://zensical.org/docs/compatibility/mkdocs/plugins/) and [releases](https://github.com/zensical/zensical/releases) before relying on it.

## Theme features

The starter's `[project.theme].features` hold the recommended set; adjust only for a concrete reader need. The [navigation](https://zensical.org/docs/setup/navigation/) page lists every flag; these are the decisions:

- **Instant navigation needs `site_url`**: `navigation.instant` keeps the search index across pages; remove it for offline builds.
- **Tabs need three sections**: add `navigation.tabs` only with three or more top-level sections; tabs appear above 1220 px.
- **Avoid conflicting pairs**: `navigation.indexes` conflicts with `toc.integrate`, and `navigation.prune` (for sites with hundreds of pages) with `navigation.expand`.
- **Copy as Markdown needs `llmstxt`**: `content.action.copy` shows only on pages listed in a `llmstxt` `sections` entry.
- **Preview selected targets**: prefer per-page targets over the site-wide `navigation.instant.preview`:

  ```toml
  [[project.markdown_extensions.zensical.extensions.preview.configurations]]
  targets.include = ["reference/*", "glossary.md"]
  ```

## Native plugins

These replace MkDocs plugins without extra packages unless noted, and all run on 0.1.0; the [plugin list](https://zensical.org/docs/compatibility/mkdocs/plugins/) gives each one's settings and first version. Enable a plugin with an empty table, such as `[project.plugins.tags]`; supported plugins reject unknown settings.

- `llmstxt`: `llms.txt`, Markdown page copies, optional `full_output`; `sections` is required; glob patterns allowed.
- `social`: Open Graph cards rendered at build time; front matter can override `social.cards`; cached in `.cache/`.
- `privacy`: self-hosts Google Fonts and Mermaid at build time and annotates external links. Scope downloads with `assets_include`, because the default also vendors about 2 MB of scripts the theme bundle references (video players, ad SDKs, Pyodide); cached in `.cache/plugin/privacy`, which `build --clean` empties.
- `optimize` (0.0.74+): compresses PNG and JPEG images, including privacy downloads; PNG needs `pngquant` on `PATH`.
- `redirects`: `redirect_maps` for moved pages and anchors (`"old.md#a" = "new.md#b"`); splitting a page keeps a page-level fallback.
- `blog`, `rss`, `tags`: posts in `docs/blog/posts/` with dates, drafts, categories, and `.authors.yml`; feeds via `match_path`; tag listings where `<!-- material/tags -->` appears.
- `mkdocstrings`, `api-autonav`: Python API docs from `::: package.module` and one generated page per module; both need `mkdocstrings-python`.
- `markdown-exec`: executes fenced code during the build; never enable it for untrusted content.
- `offline`: file-system browsing with working search; disable instant navigation, analytics, repository facts, and comments.
- `mike`: versioned deployments through the `squidfunk/mike` fork and `mkdocs.yml`; native versioning is planned.

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
- **Brand colors**: use the `custom` palette with CSS variables in `extra.css`, as the starter does.
- **Fonts**: `font = false` uses system fonts without external requests. Override with `--md-text-font` and `--md-code-font`, never `font-family`.
- **Language**: search UI is English-only for now, whatever `theme.language` says.

## Customization

1. **CSS and JavaScript**: list files under `docs/` in `extra_css` and `extra_javascript`. Initialize scripts inside `document$.subscribe(() => { ... })` so they rerun after instant navigation; use `{ path = "...", type = "module" }` for modules.
1. **Template overrides**: set `theme.custom_dir = "overrides"`, extend `base.html` from `overrides/main.html`, and override blocks (`announce`, `extrahead`, `scripts`, `content`, `footer`) with `{{ super() }}` when adding. Templates use MiniJinja: no arbitrary Python calls.
1. **Partials**: replace `overrides/partials/<name>.html`, such as `comments.html` for Giscus; add per-page layouts with the `template` front matter key and an `overrides/404.html`.

## Analytics and privacy

- `[project.extra.analytics]` supports Google Analytics and the "Was this page helpful?" feedback widget; pair it with `[project.extra.consent]` and a `<a href="#__consent">` link in `copyright`.
- **List third-party hosts in privacy reviews**: Mermaid loads from unpkg, MathJax/KaTeX need explicit `extra_javascript`, and Google Fonts load by default. The `privacy` plugin downloads and self-hosts them at build time (list each host in `assets_include`); otherwise list these hosts in the privacy review.

## Shared and variant content

- **Snippets**: `--8<-- "path/file.py"` with `base_path`, `check_paths = true`, and section markers (`--8<-- "file.py:section"`) to show tested code.
- **Macros**: Jinja variables from `extra` or YAML files; set `on_undefined = "strict"` to fail on typos.
- **Directives** (`@if`, `@var`, `@use` with `catalog.toml` and `ZENSICAL_VARIANT`): early access through Zensical Spark only; not generally available.

## Documentation

- [Basics](https://zensical.org/docs/setup/basics/) · [Navigation](https://zensical.org/docs/setup/navigation/) · [Colors](https://zensical.org/docs/setup/colors/) · [Fonts](https://zensical.org/docs/setup/fonts/) · [Logo and icons](https://zensical.org/docs/setup/logo-and-icons/)
- [Search](https://zensical.org/docs/setup/search/) · [Blog](https://zensical.org/docs/setup/blog/) · [Tags](https://zensical.org/docs/setup/tags/) · [Redirects](https://zensical.org/docs/setup/redirects/) · [Offline](https://zensical.org/docs/setup/offline/) · [Data privacy](https://zensical.org/docs/setup/data-privacy/) · [Analytics](https://zensical.org/docs/setup/analytics/)
