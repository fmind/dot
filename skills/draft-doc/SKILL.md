---
name: draft-doc
description: "Create and update Google Docs with gws: native Markdown with Mermaid/SVG figures, or styled .gdoc."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/draft-doc
  created: "2026-10-27"
  updated: "2026-10-29"
---

# Draft Doc

Create and update Google Docs deliverables in Google Drive with `gws`, following [stakeholder-writing](../stakeholder-writing/SKILL.md) ([outlines](../stakeholder-writing/references/outlines.md), [style](../stakeholder-writing/references/style.md), [checklist](../stakeholder-writing/references/checklist.md)). [gws](../gws/SKILL.md) owns authentication, Drive queries, and request mechanics.

## Format Choice

1. **Native Drive Markdown (`.md`, `mimeType: text/markdown`) for living docs**: use it for agent-maintained, frequently updated, or working documents. It opens in the Docs editor (`https://docs.google.com/document/d/<FILE_ID>/edit`) without conversion and updates in place with `drive.files.update --upload`, without `batchUpdate` index math.
1. **Converted Google Doc (`.gdoc`, `mimeType: application/vnd.google-apps.document`) for polished deliverables**: use it for client or stakeholder documents that need styling, and for multi-tab documents. Editing a `.md` file in Docs turns smart chips into text or links and removes font colors, highlights, and text alignment ([Docs Help 18289341](https://support.google.com/docs/answer/18289341)). Build it through [gws Docs recipes](../gws/references/services.md#docs).

## Branding

Style SVG cards and Mermaid diagrams with `~/.agents/DESIGN.md` (Fmind Theme) and the Mermaid frontmatter in [fmind-visuals renderers](../fmind-visuals/references/renderers.md#mermaid), or with the customer's brand guide when the deliverable is theirs. Ask for a missing guide; never invent customer colors or mix brands. Keep an opaque white canvas so figures stay legible in dark mode.

## Native `.md` Dialect Rules

[references/dialect.md](references/dialect.md) records what Docs renders, verified live on 2026-10-28; [`scripts/compile_markdown_doc.py`](scripts/compile_markdown_doc.py) enforces these rules:

1. **No YAML frontmatter or Setext underlines**: `---` or `===` directly under a paragraph line makes it a heading. Put metadata lines below `# Title` and leave a blank line before a horizontal rule.
1. **No GitHub alerts, raw HTML, or HTML comments**: they render as literal text. Use a bold blockquote (`> **Important — Decision needed by YYYY-MM-DD:** ...`), `## Annex` headings, and `\` for hard line breaks.
1. **Compile figures to PNG references**: Docs shows fenced `mermaid` blocks as code. Author fenced `mermaid` blocks or local `![Caption](figure.svg)` links to 600 px wide SVGs in `.src.md`; the compiler renders each one to a PNG at most 600 px wide, because Docs displays PNG pixels at 0.75 pt each and ignores DPI metadata. It then writes `![Caption][fig-N]` in the body, appends `[fig-N]: <data:image/png;base64,...>` definitions, and exports editable sources to `--assets-dir`. Mermaid runs through a pinned `mise exec` Mermaid CLI, so no global install is needed.
1. **Verified natively**: ATX headings, ordered lists, checklists, GFM tables, footnotes, `$...$` and `$$...$$` equations, and Base64 PNG reference images.

## Workflow

1. **Confirm account and destination**: check `gws auth status` without printing credentials, and resolve the target Drive folder ID or existing file ID with a bounded `gws drive files list` query.
1. **Author `.src.md` and `.svg` figures in a scratch folder (`SCRATCH`: the host's scratchpad, else `SCRATCH="$(mktemp -d)"`), then compile, validate, and upload** with [`scripts/compile_markdown_doc.py`](scripts/compile_markdown_doc.py):

   ```bash
   # Create or upsert <Title>.md and assets/<doc-slug>/ in a Drive folder
   uv run --no-project python ~/.agents/skills/draft-doc/scripts/compile_markdown_doc.py \
     "$SCRATCH/report.src.md" -o "$SCRATCH/report.md" \
     --drive-folder "<FOLDER_ID>" --doc-name "<Title>.md" --json

   # Update an existing .md in place: keeps its name, URL, revisions, and assets/<slug of its Drive name>/
   uv run --no-project python ~/.agents/skills/draft-doc/scripts/compile_markdown_doc.py \
     "$SCRATCH/report.src.md" -o "$SCRATCH/report.md" \
     --file-id "<FILE_ID>" --json
   ```

   Add `--doc-name` to an update only to rename the document. To compile without uploading, omit the Drive flags and pass `--assets-dir "$SCRATCH/assets/<doc-slug>"`; `--check-only` validates without rendering.

1. **Verify by reading back**: `gws docs documents get --params '{"documentId":"<FILE_ID>","includeTabsContent":true}'` works on native `.md` files; confirm headings, `inlineObjects`, footnotes, and tables. Report `drive.docs_url` and `drive.assets_folder_url`.

## Gotchas

- **Keep `mimeType: text/markdown` on upload**: `application/vnd.google-apps.document` converts the file into a `.gdoc`, which drops equations to literal `$...$` text.
- **Never widen sharing without approval**: uploads inherit the parent folder's permissions; ask before calling `drive.permissions.create`.
- **Download `.md` instead of exporting it**: `drive.files.export` rejects native `.md` files ("Export only supports Docs Editors files"); fetch the source with `drive.files.get` and `alt=media`.

## Documentation

- [Docs Help: View and edit Markdown files in Google Docs](https://support.google.com/docs/answer/18289341) · [Workspace Updates, 2026-10-05: Markdown files natively across Drive and Docs](https://workspaceupdates.googleblog.com/2026/10/preview-edit-and-collaborate-on-Markdown-files-natively-across-Drive-and-Docs.html) · [dialect and figure reference](references/dialect.md)
- Companion skills: [stakeholder-writing](../stakeholder-writing/SKILL.md) (structure, prose, and reader check), [diagrams-as-code](../diagrams-as-code/SKILL.md) (Mermaid and SVG authoring), [gws](../gws/SKILL.md) (Workspace CLI and `.gdoc` `batchUpdate`), [draft-mail](../draft-mail/SKILL.md) (Gmail drafts).
