# Authoring

Page structure and syntax beyond standard Markdown ([Zensical authoring](https://zensical.org/docs/authoring/markdown/) and [humanize visuals](../../humanize/references/primitives.md#channel-primitives)).

## Structure

- **Consistent pages**: one H1, stable headings, and frontmatter `description` on every page (reused by search snippets, social cards, and `llms.txt`).
- **Source `.md` links**: link `../guides/install.md#linux`, never built URLs, so `--strict` checks targets and anchors; escape literal brackets as `\[`.
- **Redirect moves immediately**: add `redirects` mappings whenever a published page or heading moves.

## Zensical Markdown

Keep 4-space indentation inside admonition, tab, and annotation bodies ([primitives](../../humanize/references/primitives.md#channel-primitives)); never emit GitHub-only `> [!IMPORTANT]` blocks in Zensical docs:

- **Highlight, callouts & tabs**: use `==mark==` sparingly for key phrases, `!!! note|tip|warning|danger` or collapsible `???` admonitions for takeaways, `=== "Tab"` for alternatives, and `<div class="grid cards" markdown>` for scan cards.
- **Include tested source**: `--8<-- "src/pkg/module.py"` or `--8<-- "file.py:name"` (`# --8<-- [start:name]` .. `[end:name]`); `check_paths` fails strict builds on missing files.
- **Diagrams**: inline ` ```mermaid ` (set `config.flowchart.wrappingWidth: 280` or `320` in Mermaid frontmatter and bound on-page SVG `max-width` by `viewBox` aspect ratio via [`extra_javascript`](configuration.md#customization)), or [Typst](../../diagrams-as-code/references/typst.md) / [D2](../../diagrams-as-code/references/d2.md) / [SVG](../../diagrams-as-code/references/svg/GUIDE.md) assets in `docs/assets/`.
- **Glossary & tooltips**: `*[CLI]: Command-Line Interface` in `includes/abbreviations.md` separated by blank lines; `[link](page.md "Tooltip")`.
- **Page frontmatter**: `hide: [navigation, toc, footer, path, tags]`, `icon: lucide/rocket`, `status: new`, `search: {exclude: true}`, `template: custom.html`.

## Content practices

- **Verify snippets and links**: use `console` fences with checked output, `--8<--` tested snippets, and `lychee --offline --no-progress docs/` (`check:links`) for local link validation.
- **No untrusted build execution**: test examples in separate bounded tasks; enable `markdown-exec` only on trusted repos.
- **API docs via Zensical**: use `mkdocstrings` + `api-autonav` ([configuration](configuration.md#native-plugins)), never `pdoc`.
- **Curate `llms.txt` when noisy**: narrow `sections` (and `markdown_description`) if archives bloat it, noting unlisted pages lose Copy as Markdown.
