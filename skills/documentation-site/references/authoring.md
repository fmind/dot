# Authoring

Page structure and syntax beyond standard Material Markdown ([Zensical authoring docs](https://zensical.org/docs/authoring/markdown/)).

## Structure

- **Consistent pages**: one H1, stable headings, and frontmatter `description` on every page (reused by search snippets, social cards, and `llms.txt`).
- **Source `.md` links**: link `../guides/install.md#linux`, never built URLs, so `--strict` checks targets and anchors; escape literal brackets as `\[`.
- **Redirect moves immediately**: add `redirects` mappings whenever a published page or heading moves.

## Zensical Markdown

Admonitions, tabs, annotations, cards, and icons are enabled by the starter; keep 4-space indentation inside admonition/tab/annotation bodies when formatting:

| Need                         | Syntax                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| ---------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Include tested source        | `--8<-- "src/pkg/module.py"` or `--8<-- "file.py:name"` (`# --8<-- [start:name]` .. `[end:name]`); `check_paths` fails strict builds on missing files                                                                                                                                                                                                                                                                                                                                                                                        |
| Diagram                      | ` ```mermaid ` for inline flows/sequences/states/ER (set `config.flowchart.wrappingWidth: 280` or `320` in Mermaid frontmatter and bound on-page SVG `max-width` by `viewBox` aspect ratio via [`extra_javascript`](configuration.md#customization) so narrow vertical diagrams do not stretch); [Typst](../../diagrams-as-code/references/typst.md) (2× PNG + `.typ` source), [D2](../../diagrams-as-code/references/d2.md), or [SVG](../../diagrams-as-code/references/svg/GUIDE.md) assets in `docs/assets/` for landing or concept pages |
| Glossary and tooltips        | `*[CLI]: Command-Line Interface` in `includes/abbreviations.md` separated by blank lines; `[link](page.md "Tooltip")`                                                                                                                                                                                                                                                                                                                                                                                                                        |
| Page controls (front matter) | `hide: [navigation, toc, footer, path, tags]`, `icon: lucide/rocket`, `status: new` (in `[project.extra.status]`), `search: {exclude: true}`, `template: custom.html`                                                                                                                                                                                                                                                                                                                                                                        |

## Content practices

- **Verified commands and snippets**: use `console` fences with checked output and `--8<--` snippets instead of pasted code.
- **No untrusted build execution**: test examples in separate bounded tasks; enable `markdown-exec` only on trusted repos.
- **API docs via Zensical**: use `mkdocstrings` + `api-autonav` ([configuration](configuration.md#native-plugins)), never `pdoc` (migrate legacy `pdoc` when docs are next edited).
- **Curate `llms.txt` when noisy**: the starter includes every page so each gets Copy as Markdown; narrow `sections` (and `markdown_description`) if API or blog archives bloat it, noting unlisted pages lose the button.
