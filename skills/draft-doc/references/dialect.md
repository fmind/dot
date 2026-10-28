# Google Docs Native Markdown (`.md`) Dialect, Figures, and Drive Assets

Reference for authoring, compiling, and uploading native Markdown (`.md`, `mimeType: text/markdown`) documents opened in the Docs editor (`https://docs.google.com/document/d/<FILE_ID>/edit`).

## Live Rendering Results (2026-10-28)

Verified by uploading a test document with [`scripts/compile_markdown_doc.py`](../scripts/compile_markdown_doc.py), reading it back with `gws docs documents get`, and inspecting a PDF export of a `.gdoc` copy. Docs opened the native `.md` file in pageless mode.

| Construct                                      | Status        | Evidence and rule                                                                                                                            |
| ---------------------------------------------- | ------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| ATX headings (`#`, `##`)                       | Verified      | `HEADING_1` and `HEADING_2` paragraphs.                                                                                                      |
| Hard line break (`\` at line end)              | Verified      | Line break inside one paragraph.                                                                                                             |
| Ordered list (`1.`)                            | Verified      | `DECIMAL` list.                                                                                                                              |
| Checklist (`- [ ]`, `- [x]`)                   | Verified      | Checkbox list; the checked state showed in the `.gdoc` copy (the Docs API does not expose it).                                               |
| GFM pipe table with alignment                  | Verified      | 3 × 2 table; right alignment kept.                                                                                                           |
| Footnote (`[^1]`)                              | Verified      | `footnoteReference` plus a footnote body.                                                                                                    |
| Equations (`$x^2$`, `$$...$$`)                 | Verified      | `equation` elements (the API does not expose their content). Converting to `.gdoc` turns them into literal `$...$` text.                     |
| Base64 PNG reference image (`![alt][fig-N]`)   | Verified      | `inlineObjects` with the alt text as description. Size is pixels × 0.75 pt; PNG `pHYs` DPI is ignored, so the compiler caps width at 600 px. |
| `---` after a blank line or under a list item  | Verified      | `horizontalRule`, as CommonMark specifies.                                                                                                   |
| HTML comment (`<!-- ... -->`)                  | Unsupported   | Rendered as a literal text paragraph in the native `.md` document (hidden only after `.gdoc` conversion). The checker rejects it.            |
| Setext underline (`---`/`===` under paragraph) | CommonMark    | Makes the paragraph a heading; the checker rejects it. Not live-tested.                                                                      |
| YAML frontmatter, GitHub alerts, raw HTML tags | Not re-tested | Still rejected, as in the original skill; CommonMark reads a closing frontmatter `---` as a setext underline.                                |
| Fenced `mermaid` blocks, `.svg` images         | Not re-tested | Compile them to PNG references; Docs has no Mermaid renderer.                                                                                |
| Emphasis, links, code blocks, blockquotes      | Not tested    | Standard CommonMark; confirm in a read-back when a document depends on them.                                                                 |
| `drive.files.export` of a native `.md` file    | Unsupported   | Fails with "Export only supports Docs Editors files"; download the source with `alt=media`.                                                  |

## Figures and Drive Assets

The compiler turns every fenced `mermaid` block and local `![alt](path.svg)` link into a short reference in the body and appends the Base64 definitions at the bottom of the file, so the body stays readable:

```markdown
![Figure 1 — Nightly batch execution flow on spot virtual machines][fig-1]

_Figure 1. Automatic retries keep reclaimed spot machines within the 07:00 window._

[fig-1]: data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...
```

- **Alt text for Mermaid**: an explicit `%% alt: <description>` line inside the block, else the italic caption line right after it, else `Figure N — Architecture diagram`.
- **Rendering**: Mermaid runs through the pinned Mermaid CLI with `mise exec` and system Chrome; SVG figures are checked with the [diagrams-as-code SVG checker](../../diagrams-as-code/references/svg/GUIDE.md) and rasterized by isolated headless Chrome with JavaScript and network disabled. Both render at `--scale` (1 to 4, default 2) but never wider than 600 px (450 pt), which fits Letter and A4 text columns. SVG figures therefore use a 600 px canvas (`--svg-width`, default 600), so 12 px labels read at 9 pt; a wider canvas shrinks text by 600 divided by its width (960 px shows 12 px labels at about 5.6 pt). Keep Mermaid diagrams narrow (`flowchart TD` over `LR`) for the same reason.
- **Drive assets**: with `--drive-folder` or `--file-id`, the compiler exports the `.src.md`, `fig-N.mmd` sources, `.svg` figures, and `fig-N.png` rasters to `--assets-dir` (default `assets/<doc-slug>/` next to `--output`), upserts them into `assets/<doc-slug>/` in Drive, and returns `drive.docs_url`, `drive.assets_folder_url`, and `drive.uploaded_assets`.
- **Updates by file ID**: `--file-id` keeps the document's Drive name and parent folder and derives `<doc-slug>` from that name; only `--doc-name` renames it.

## Official Google Documentation

- [Docs Help: View and edit Markdown (.md) files in Google Docs](https://support.google.com/docs/answer/18289341)
- [Workspace Updates, 2026-10-05: Preview, edit and collaborate on Markdown files natively across Drive and Docs](https://workspaceupdates.googleblog.com/2026/10/preview-edit-and-collaborate-on-Markdown-files-natively-across-Drive-and-Docs.html)
- [Google Drive API: Manage file uploads](https://developers.google.com/workspace/drive/api/guides/manage-uploads)
