---
name: draft-doc
description: "Create and update Google Docs with gws using native Drive Markdown (.md) and @2x Mermaid/SVG figures by default, or multi-tab Docs when needed."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/draft-doc
  created: "2026-10-27"
  updated: "2026-10-27"
---

# Draft Doc

Create and update Google Docs deliverables in Google Drive with `gws`, following [stakeholder-writing](../stakeholder-writing/SKILL.md) ([outlines](../stakeholder-writing/references/outlines.md), [style](../stakeholder-writing/references/style.md), [checklist](../stakeholder-writing/references/checklist.md)) and `~/.agents/DESIGN.md` for Fmind work (or the client's brand guide for client work). [gws](../gws/SKILL.md) owns authentication, Drive queries, and request mechanics.

## Format Choice (80/20 Rule)

1. **Default (80%) — Native Drive Markdown (`.md`, `mimeType: text/markdown`)**: use for single-file reports, proposals, decision memos, cost estimates, architecture notes, and runbooks. Files stay `text/markdown` in Drive, open natively in Google Docs Editor (`https://docs.google.com/document/d/<FILE_ID>/edit`) with inline comments, suggestions, and revision history, and update atomically via `drive.files.update --upload` without `batchUpdate` UTF-16 index math.
1. **Exception (20%) — Converted Google Doc (`.gdoc`, `mimeType: application/vnd.google-apps.document`)**: use only when a deliverable requires multiple **Document Tabs** (such as bilingual tabs or multi-tab governance docs) or Docs-native smart chips. `docs.documents.batchUpdate` is rejected on native `text/markdown` files.

## Google Docs `.md` Dialect Rules

Google Docs parses native `.md` files with specific rules detailed in the [dialect and figure reference](references/dialect.md) and validated by [`scripts/compile_markdown_doc.py`](scripts/compile_markdown_doc.py):

1. **No YAML frontmatter (`---`)**: the closing `---` triggers Setext `HEADING_2` on the metadata block. Place metadata lines (`Type:`, `Status:`, `Audience:`, `Author:`, `Date:`) or a bold subtitle line right below `# Title` instead.
1. **No GitHub alerts (`> [!IMPORTANT]`)**: alert tags render as literal text. Use a bold blockquote instead: `> **Important — Decision needed by YYYY-MM-DD:** ...`
1. **No raw HTML (`<details>`, `<summary>`, `<mark>`, `<u>`)**: HTML tags render as literal text. Put annexes under standard `## Annex` headings at the bottom of the file.
1. **Mermaid (`.mmd`) and SVG (`.svg`) figures compiled to `@2x` Base64 PNG references**: Google Docs renders fenced `mermaid` blocks as literal code and ignores `data:image/svg+xml` URIs. Write fenced ` ```mermaid ` blocks or link local 960px `.svg` cards (`![Caption](figure.svg)` with `viewBox="0 0 960 H"`, `role="img"`, `<title>`, `<desc>`, `aria-labelledby`, and `font-size >= 12px`) in a `.src.md` file, then run [`scripts/compile_markdown_doc.py`](scripts/compile_markdown_doc.py). The compiler replaces each figure in the body with `![Caption][fig-N]` and appends `[fig-N]: <data:image/png;base64,...>` at the bottom of the output `.md` file so Google Docs ingests them as native inline images while keeping the prose clean.
1. **Supported natively**: `#`–`######` headings, bold/italic/strikethrough/inline code, inline and reference links, GFM tables, interactive checklists (`- [ ]` / `- [x]`), language-tagged fenced code blocks, LaTeX equations (`$...$` and `$$...$$`), and footnotes (`[^1]`).

## Workflow

1. **Confirm account and destination**: check `gws auth status` without printing credentials, and resolve the target Drive folder ID or existing file ID with a bounded `gws drive files list` query.
1. **Author `.src.md` and optional `.svg` figures in `$SCRATCH`**, then compile and validate with [`scripts/compile_markdown_doc.py`](scripts/compile_markdown_doc.py):

   ```bash
   # Validate and rasterize a standalone SVG figure (auto-detects viewBox WxH and renders @2x PNG)
   uv run --no-project python ~/.agents/skills/draft-doc/scripts/compile_markdown_doc.py "$SCRATCH/figure.svg" -o "$SCRATCH/figure.png" --json

   # Compile .src.md (fenced mermaid + linked .svg -> @2x Base64 PNG refs) and validate dialect
   uv run --no-project python ~/.agents/skills/draft-doc/scripts/compile_markdown_doc.py "$SCRATCH/report.src.md" -o "$SCRATCH/report.md" --json
   ```

1. **Create or update the native `.md` file in Google Drive**:

   ```bash
   # Create a new native .md document (optionally inside a folder via "parents": ["<FOLDER_ID>"])
   gws drive files create --params '{"supportsAllDrives":true,"fields":"id,name,mimeType,webViewLink"}' \
     --json '{"name":"<Title>.md","mimeType":"text/markdown"}' \
     --upload "$SCRATCH/report.md" --upload-content-type text/markdown

   # Update an existing .md document in place (preserves File ID, URL, revision history, and open Docs comments)
   gws drive files update --params '{"fileId":"<FILE_ID>","supportsAllDrives":true,"fields":"id,name,version,modifiedTime,webViewLink"}' \
     --upload "$SCRATCH/report.md" --upload-content-type text/markdown
   ```

1. **Verify by reading back**: confirm `inlineObjects` and heading structure via `gws docs documents get --params '{"documentId":"<FILE_ID>"}'`, and report the Google Docs Editor URL (`https://docs.google.com/document/d/<FILE_ID>/edit`).

## Gotchas

- **Keep `mimeType: text/markdown` on upload**: setting `mimeType: application/vnd.google-apps.document` converts the file into a legacy `.gdoc` and breaks atomic Markdown file updates.
- **Never widen sharing without approval**: uploading or updating a file keeps its folder's permissions; ask the user before calling `drive.permissions.create`.
- **Keep `.src.md` beside `.md` during edits**: edit the `.src.md` source (with editable `mermaid` blocks and `.svg` files) and re-run `compile_markdown_doc.py` before uploading.

## Documentation

- [Google Docs native Markdown announcement](https://developers.google.com/workspace) · [dialect and figure reference](references/dialect.md)
- Companion skills: [stakeholder-writing](../stakeholder-writing/SKILL.md) (structure, prose, and reader check), [diagrams-as-code](../diagrams-as-code/SKILL.md) (Mermaid and SVG authoring), [gws](../gws/SKILL.md) (Workspace CLI and multi-tab `docs.documents.batchUpdate`), [draft-mail](../draft-mail/SKILL.md) (Gmail drafts).
