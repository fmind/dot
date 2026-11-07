# Authoring

Use this reference when writing or restructuring pages, including course lessons. The [Zensical authoring docs](https://zensical.org/docs/authoring/markdown/) hold the full syntax.

## Structure

- **Structure each page consistently**: use one H1 per page and stable headings; set `description` front matter on every page because search snippets, social cards, and `llms.txt` reuse it.
- **Link to source Markdown**: use paths like `../guides/install.md#linux`, never to built URLs, so strict builds validate pages and anchors. Escape literal brackets as `\[`.
- **Redirect moved pages in the same change**: when renaming or moving a published page or heading, add a `redirects` mapping.

## Zensical Markdown

The starter enables the standard Material syntax (admonitions, tabs, annotations, cards, icons). Bodies of admonitions, tabs, and annotations use four-space indentation; keep it when formatting. These rows are the choices that differ from defaults:

| Need                         | Syntax                                                                                                                                                                                                      |
| ---------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Include tested source        | `--8<-- "src/pkg/module.py"` or a marked section `--8<-- "file.py:name"` between `# --8<-- [start:name]` and `[end:name]`; `check_paths` fails strict builds on a missing file                              |
| Diagram                      | ` ```mermaid ` fences for technical pages (flowcharts, sequences, states, classes, ER); [SVG illustrations](../../diagrams-as-code/references/svg/GUIDE.md) in `docs/assets/` for landing and concept pages |
| Glossary and tooltips        | `*[CLI]: Command-Line Interface` in `includes/abbreviations.md`, one per paragraph (blank line between, or formatters merge them); `[link](page.md "Tooltip")`                                              |
| Page controls (front matter) | `hide: [navigation, toc, footer, path, tags]`, `icon: lucide/rocket`, `status: new` (declared in `[project.extra.status]`), `search: {exclude: true}`, `template: custom.html`                              |

## Content practices

- **Show commands with expected output**: use `console` fences and verify them; include source through snippets instead of copying code that can drift.
- **Builds must not execute untrusted code**: run examples in their own bounded test task; enable `markdown-exec` only for trusted repositories.
- **Generate API docs with Zensical**: Python API references use mkdocstrings and the native `api-autonav` (see [configuration](configuration.md#native-plugins)), never pdoc; the python-stack starter already wires them, and an existing pdoc build migrates when its docs are next touched.
- **Keep `llms.txt` useful for agents**: the starter lists every page so each gets the Copy as Markdown button; curate `sections` (and `markdown_description`) when generated pages such as API reference or blog archives add noise, accepting that unlisted pages lose the button.
