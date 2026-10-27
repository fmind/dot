---
name: draft-doc
description: "Create and update Google Docs with gws using native Drive Markdown (.md) and @2x Mermaid/SVG figures by default, or .gdoc when requested."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/draft-doc
  created: "2026-10-27"
  updated: "2026-10-27"
---

# Draft Doc

Create and update Google Docs deliverables in Google Drive with `gws`, following [stakeholder-writing](../stakeholder-writing/SKILL.md) ([outlines](../stakeholder-writing/references/outlines.md), [style](../stakeholder-writing/references/style.md), [checklist](../stakeholder-writing/references/checklist.md)). [gws](../gws/SKILL.md) owns authentication, Drive queries, and request mechanics.

## Format Choice

1. **Default — Native Drive Markdown (`.md`, `mimeType: text/markdown`)**: by default use `.md`, except if the user says to use `.gdoc` format. Native `.md` files open directly in Google Docs Editor (`https://docs.google.com/document/d/<FILE_ID>/edit`) with the left Document Outline, inline comments, suggestions, and revision history, and update atomically via `drive.files.update --upload` without `batchUpdate` UTF-16 index math.
1. **Exception — Converted Google Doc (`.gdoc`, `mimeType: application/vnd.google-apps.document`)**: use only when the user asks to use `.gdoc` format, or when a document requires multiple **Document Tabs** or Docs-native smart chips (`docs.documents.batchUpdate` is rejected on native `text/markdown` files).

## Branding (`~/.agents/DESIGN.md` or Customer Brand)

Style every SVG card and Mermaid diagram consistently (full token table and templates in [references/dialect.md](references/dialect.md#branding-and-mermaid-styling)):

- **Default (`~/.agents/DESIGN.md` — Fmind Theme)**: use a light `#FFFFFF` canvas, `#F1F3F4` secondary panel, `#9AA0A6` structural border, `#202124` primary ink, `#595D62` muted caption text, `#174EA6` primary accent with `#D2E3FC` surface fill, semantic status pairs (Positive `#0D652D`/`#CEEAD6`, Warning `#934900`/`#FEEFC3`, Danger `#A50E0E`/`#FAD2CF`), and `Google Sans` / `Google Sans Code` typography.
- **Customer branding (when available)**: apply the customer's palette (primary accent, light tint surface, text ink, neutral border), typography, and logo across all SVG `<style>` blocks and Mermaid frontmatter (`themeVariables` and `classDef` rules), keeping an opaque `#FFFFFF` canvas so figures stay legible in Google Docs light and dark modes. Ask for the customer's brand guide if missing; never invent colors or mix Fmind and customer brands in the same deliverable.

## Google Docs `.md` Dialect Rules

Google Docs parses native `.md` files with the rules detailed in [references/dialect.md](references/dialect.md) and validated by [`scripts/compile_markdown_doc.py`](scripts/compile_markdown_doc.py):

1. **No YAML frontmatter (`---`) or Setext underlines**: a closing `---` at the top of the file or `---` directly under a text line without a blank line triggers Setext `HEADING_2`. Place metadata lines (`Type:`, `Status:`, `Audience:`, `Author:`, `Date:`) below `# Title`, and always leave a blank line before a horizontal rule (`---`).
1. **No GitHub alerts (`> [!IMPORTANT]`)**: alert tokens render as literal text. Use a bold blockquote instead: `> **Important — Decision needed by YYYY-MM-DD:** ...`
1. **No raw HTML (`<details>`, `<summary>`, `<mark>`, `<u>`, `<br>`)**: HTML tags render as literal text. Put annexes under standard `## Annex` headings at the bottom of the file and use `\` for hard line breaks.
1. **Mermaid (`.mmd`) and SVG (`.svg`) figures compiled to `@2x` Base64 PNG references**: Google Docs renders fenced `mermaid` blocks as literal code and ignores `data:image/svg+xml` URIs. Author fenced ` ```mermaid ` blocks or link local 960px `.svg` cards (`![Caption](figure.svg)`) in `.src.md`, then run [`scripts/compile_markdown_doc.py`](scripts/compile_markdown_doc.py). The compiler replaces each figure with `![Caption][fig-N]`, appends `[fig-N]: <data:image/png;base64,...>` at the bottom of the `.md` file, and exports editable sources and `@2x` PNGs into `--assets-dir`.
1. **Supported natively**: `#`–`######` headings, bold/italic/strikethrough/inline code, inline and reference links, nested lists, interactive checklists (`- [ ]` / `- [x]`), GFM pipe tables, language-tagged fenced code blocks, LaTeX equations (`$...$` and `$$...$$`), and footnotes (`[^1]`).

## Workflow

1. **Confirm account and destination**: check `gws auth status` without printing credentials, and resolve the target Drive folder ID or existing file ID with a bounded `gws drive files list` query.
1. **Author `.src.md` and `.svg` figures in `$SCRATCH`**, then compile, validate, and export the asset bundle with [`scripts/compile_markdown_doc.py`](scripts/compile_markdown_doc.py):

   ```bash
   # Compile .src.md -> .md and export editable sources (.src.md, .mmd, .svg) + @2x .png figures to --assets-dir
   uv run --no-project python ~/.agents/skills/draft-doc/scripts/compile_markdown_doc.py \
     "$SCRATCH/report.src.md" -o "$SCRATCH/report.md" --assets-dir "$SCRATCH/assets/report" --json
   ```

1. **Upload the native `.md` deliverable and its `assets/` folder to Google Drive**:

   ```bash
   # 1. Create or update the native .md document in the target folder (<FOLDER_ID>)
   gws drive files create --params '{"supportsAllDrives":true,"fields":"id,name,mimeType,webViewLink"}' \
     --json '{"name":"<Title>.md","mimeType":"text/markdown","parents":["<FOLDER_ID>"]}' \
     --upload "$SCRATCH/report.md" --upload-content-type text/markdown

   # Update an existing .md document in place (preserves File ID, URL, revisions, and open Docs comments)
   gws drive files update --params '{"fileId":"<FILE_ID>","supportsAllDrives":true,"fields":"id,name,version,modifiedTime,webViewLink"}' \
     --upload "$SCRATCH/report.md" --upload-content-type text/markdown

   # 2. Create or reuse an assets/<doc-slug>/ subfolder in Drive and upload the exported sources (.src.md, .mmd, .svg, .png)
   gws drive files create --params '{"supportsAllDrives":true,"fields":"id,name"}' \
     --json '{"name":"assets","mimeType":"application/vnd.google-apps.folder","parents":["<FOLDER_ID>"]}'
   ```

1. **Verify by reading back**: confirm `inlineObjects` and heading structure via `gws docs documents get --params '{"documentId":"<FILE_ID>"}'`, and report both the Google Docs Editor URL (`https://docs.google.com/document/d/<FILE_ID>/edit`) and the Drive `assets/` folder link.

## Gotchas

- **Keep `mimeType: text/markdown` on upload**: setting `mimeType: application/vnd.google-apps.document` converts the file into a `.gdoc` and disables atomic Markdown updates.
- **Never widen sharing without approval**: uploading or updating a file inherits its parent folder's permissions; ask the user before calling `drive.permissions.create`.
- **Upload editable assets alongside figures**: always pass `--assets-dir` and sync the exported `.src.md`, `.mmd`, `.svg`, and `@2x` `.png` files to the Drive `assets/` folder so collaborators can edit diagrams without local workspace access.

## Documentation

- [Google Developers Blog: Native Markdown in Docs and Drive](https://developers.googleblog.com/preview-edit-and-collaborate-on-markdown-md-files-natively-in-google-docs-and-drive/) · [Google Docs Help: Use Markdown](https://support.google.com/docs/answer/12014036) · [Google Workspace Updates: Markdown in Docs](https://workspaceupdates.googleblog.com/2024/07/import-and-export-markdown-in-google-docs.html) · [dialect and figure reference](references/dialect.md)
- Companion skills: [stakeholder-writing](../stakeholder-writing/SKILL.md) (structure, prose, and reader check), [diagrams-as-code](../diagrams-as-code/SKILL.md) (Mermaid and SVG authoring), [gws](../gws/SKILL.md) (Workspace CLI and multi-tab `.gdoc` `batchUpdate`), [draft-mail](../draft-mail/SKILL.md) (Gmail drafts).
