# Google Docs Native Markdown (`.md`) Dialect, Figures, and Drive Assets

Dialect and asset rules for native Drive Markdown (`mimeType: text/markdown`) opened in Docs (`https://docs.google.com/document/d/<FILE_ID>/edit`).

## Live Rendering Results (2026-10-28)

Verified via [`scripts/compile_markdown_doc.py`](../scripts/compile_markdown_doc.py) upload, `gws docs documents get` read-back, and PDF export of a `.gdoc` copy (Docs opens native `.md` in pageless mode).

| Construct                            | Status      | Evidence and rule                                                                       |
| ------------------------------------ | ----------- | --------------------------------------------------------------------------------------- |
| `#`, `##`                            | Verified    | `HEADING_1`, `HEADING_2`.                                                               |
| `\` line break, `1.`, `- [ ]`/`[x]`  | Verified    | Line breaks, `DECIMAL` lists, checkboxes (checkbox state visible in `.gdoc` copy only). |
| GFM table, footnote `[^1]`           | Verified    | Table alignment preserved; `footnoteReference` + footnote body.                         |
| Equations `$x^2$`, `$$...$$`         | Verified    | `equation` elements (unexposed in API; `.gdoc` flattens to literal `$...$`).            |
| Base64 PNG ref `![alt][fig-N]`       | Verified    | `inlineObjects` with alt text at pixels × 0.75 pt (`pHYs` ignored; 600 px cap).         |
| `---` after blank line/list          | Verified    | CommonMark `horizontalRule`.                                                            |
| HTML `<!-- ... -->`                  | Unsupported | Literal text paragraph in native `.md`; rejected.                                       |
| Setext `---`/`===`, YAML frontmatter | Rejected    | Parses as Setext heading; YAML closing `---` breaks title.                              |
| Raw HTML tags, GitHub alerts         | Rejected    | Avoid unportable constructs in native Docs `.md`.                                       |
| `mermaid` blocks, `.typ`/`.svg`      | Compiled    | Pre-rendered to Base64 PNG refs.                                                        |
| `drive.files.export` on `.md`        | Unsupported | Fails on native `.md`; download via `alt=media`.                                        |

## Figures and Drive Assets

The compiler replaces each `mermaid` fence and local `![alt](path.typ)` / `![alt](path.svg)` with a compact reference in the body and appends Base64 definitions at EOF:

<!-- dprint-ignore -->
```markdown
![Figure 1 — Nightly batch execution flow on spot virtual machines][fig-1]

_Figure 1. Automatic retries keep reclaimed spot machines within the 07:00 window._

[fig-1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...>
```

- **Column-0 fences and local `.typ`/`.svg` sources**: indented `mermaid` fences and remote `.typ`/`.svg` URLs are rejected; unindent fences and save `.typ`/`.svg` files locally (or use PNG).
- **Mermaid alt text**: `%% alt: <description>` inside the block, else the adjacent italic caption line, else `Figure N — Architecture diagram`.
- **Sizing and rasterization**: [Typst](../../diagrams-as-code/references/typst.md) compiles via `typst compile` with automatic Google Sans font discovery (no browser required; keep KPI cards and figure layouts under 440 pt wide so text stays crisp); Mermaid runs via pinned `mise exec` CLI + system Chrome; SVGs pass the [diagrams-as-code SVG checker](../../diagrams-as-code/references/svg/GUIDE.md) and render in isolated headless Chrome (JS and network off). All render at `--scale` (1–4, default 2) capped at 600 px wide (450 pt, fitting Letter/A4). Author SVGs on a 600 px canvas (`--svg-width`, default 600) so 12 px labels render cleanly at 9 pt instead of shrinking; prefer vertical flowcharts in Mermaid.
- **Drive asset bundle**: `--drive-folder` or `--file-id` writes `.src.md`, `.typ` (plus imported `fmind.typ`), `fig-N.mmd`, `.svg`, and `fig-N.png` to `--assets-dir` (default `assets/<doc-slug>/` beside `--output`), upserts `assets/<doc-slug>/` in Drive, and returns `drive.docs_url`, `drive.assets_folder_url`, and `drive.uploaded_assets`.
- **In-place `--file-id` updates**: preserves Drive name and parent folder (`--doc-name` renames). If Drive returns no parent folder, the `.md` still updates and `drive.warning` (and stderr) lists skipped assets; rerun with `--drive-folder` to sync them.

## Official Google Documentation

- [Docs Help: View and edit Markdown (.md) files in Google Docs](https://support.google.com/docs/answer/18289341)
- [Workspace Updates, 2026-10-05: Preview, edit and collaborate on Markdown files natively across Drive and Docs](https://workspaceupdates.googleblog.com/2026/10/preview-edit-and-collaborate-on-Markdown-files-natively-across-Drive-and-Docs.html)
- [Google Drive API: Manage file uploads](https://developers.google.com/workspace/drive/api/guides/manage-uploads)
