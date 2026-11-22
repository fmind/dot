# Google Docs Native Markdown (`.md`) Dialect and Figures

Dialect and figure rules for Drive Markdown (`mimeType: text/markdown`) opened in Docs (`https://docs.google.com/document/d/<FILE_ID>/edit`).

## Live Rendering Results (2026-10-28)

Verified via Drive upload (`text/markdown`), `gws docs documents get`, and PDF export of a `.gdoc` copy (native `.md` opens pageless).

| Construct                       | Status      | Evidence and rule                                                          |
| ------------------------------- | ----------- | -------------------------------------------------------------------------- |
| `#`, `##`                       | Verified    | `HEADING_1`, `HEADING_2`.                                                  |
| `\` break, `1.`, `- [ ]`/`[x]`  | Verified    | Line breaks, `DECIMAL` lists, checkboxes (visible in `.gdoc` copy only).   |
| GFM table, footnote `[^1]`      | Verified    | Table alignment preserved; `footnoteReference` + body.                     |
| Equations `$x^2$`, `$$...$$`    | Verified    | `equation` elements (unexposed in API; `.gdoc` flattens to `$...$`).       |
| Base64 PNG `![alt][fig-N]`      | Verified    | `inlineObjects` with alt at pixels × 0.75 pt (`pHYs` ignored; 600 px cap). |
| `---` after blank line/list     | Verified    | CommonMark `horizontalRule`.                                               |
| HTML `<!-- ... -->`             | Unsupported | Literal text paragraph in native `.md`; omit.                              |
| Setext `---`/`===`, frontmatter | Rejected    | Parses as Setext heading; YAML `---` breaks title.                         |
| Raw HTML tags, GitHub alerts    | Rejected    | Unportable in native Docs `.md`.                                           |
| `mermaid` blocks, `.typ`/`.svg` | Pre-render  | Compile to Base64 PNG references before upload.                            |
| `drive.files.export` on `.md`   | Unsupported | Fails on native `.md`; download via `alt=media`.                           |

## Figures

Render `.typ`, `.svg`, or `.mmd` sources to PNG (`<= 600 px` wide, `#FFFFFF` canvas) via [diagrams-as-code](../../../../diagrams-as-code/SKILL.md), then embed as Base64 reference links at EOF:

<!-- dprint-ignore -->
```markdown
![Figure 1: Nightly batch execution flow on spot virtual machines][fig-1]

_Figure 1. Automatic retries keep reclaimed spot machines within the 07:00 window._

[fig-1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...>
```

Keep `.typ`/`.svg`/`.mmd` sources in the repo or upload alongside the doc via [`drive_upload.py`](../../../../gws/scripts/drive_upload.py).

## Official Google Documentation

- [Docs Help: View and edit Markdown (.md) files in Google Docs](https://support.google.com/docs/answer/18289341)
- [Workspace Updates, 2026-10-05: Preview, edit and collaborate on Markdown files natively across Drive and Docs](https://workspaceupdates.googleblog.com/2026/10/preview-edit-and-collaborate-on-Markdown-files-natively-across-Drive-and-Docs.html)
- [Google Drive API: Manage file uploads](https://developers.google.com/workspace/drive/api/guides/manage-uploads)
