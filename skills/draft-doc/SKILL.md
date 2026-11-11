---
name: draft-doc
description: "Create and update Google Docs with gws: Markdown with Mermaid/SVG figures or .gdoc."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/draft-doc
  created: "2026-10-27"
  updated: "2026-11-11"
---

# Draft Doc

Create and update Google Docs deliverables in Drive with `gws`, following [stakeholder-writing](../stakeholder-writing/SKILL.md) ([outlines](../stakeholder-writing/references/outlines.md), [style](../stakeholder-writing/references/style.md), [checklist](../stakeholder-writing/references/checklist.md)). [gws](../gws/SKILL.md) owns auth, Drive queries, and request mechanics.

## Format Choice

1. **Native Drive Markdown (`.md`, `mimeType: text/markdown`) for living docs**: agent-maintained, frequently updated, or working documents. Opens directly in Docs (`https://docs.google.com/document/d/<FILE_ID>/edit`) and updates in place via `drive.files.update --upload` without `batchUpdate` index math.
1. **Converted Google Doc (`.gdoc`, `mimeType: application/vnd.google-apps.document`) for polished deliverables**: client/stakeholder docs needing rich styling or multiple tabs. Editing `.md` in Docs strips font colors, highlights, alignment, and smart chips ([Docs Help 18289341](https://support.google.com/docs/answer/18289341)); build `.gdoc` files with [gws Docs recipes](../gws/references/services.md#docs).

## Branding

Style SVG cards and Mermaid diagrams with `~/.agents/DESIGN.md` (Fmind Theme) and [Mermaid frontmatter](../diagrams-as-code/references/mermaid.md), or the customer's brand guide (ask if missing; never invent colors or mix brands). Keep an opaque white canvas for dark-mode legibility.

## Native `.md` Dialect Rules

Verified live on 2026-10-28 ([references/dialect.md](references/dialect.md)) and enforced by [`scripts/compile_markdown_doc.py`](scripts/compile_markdown_doc.py):

1. **No YAML frontmatter or Setext underlines**: `---` or `===` directly under a paragraph turns it into a heading. Put metadata lines below `# Title` and leave a blank line before horizontal rules.
1. **No GitHub alerts, raw HTML, or HTML comments**: all render as literal text. Use bold blockquotes (`> **Important — Decision needed by YYYY-MM-DD:** ...`), `## Annex` headings, and trailing `\` for hard breaks.
1. **Compile figures to PNG references**: write column-0 `mermaid` fences or local 600 px `![Caption](figure.svg)` links in `.src.md`. [`scripts/compile_markdown_doc.py`](scripts/compile_markdown_doc.py) rasterizes each at ≤600 px wide, emits `![Caption][fig-N]` Base64 PNG references, and exports editable sources to `--assets-dir` ([details](references/dialect.md)).
1. **Verified natively**: ATX headings, ordered lists, checklists, GFM tables, footnotes, `$...$` / `$$...$$` equations, and Base64 PNG reference images.

## Workflow

1. **Confirm account and destination**: check `gws auth status` without printing credentials, then resolve the target Drive folder ID or file ID via bounded `gws drive files list`.
1. **Author in scratch (`SCRATCH`: host scratchpad, else `SCRATCH="$(mktemp -d)"`), then compile and upload** with [`scripts/compile_markdown_doc.py`](scripts/compile_markdown_doc.py):

   ```bash
   # Create or upsert <Title>.md and assets/<doc-slug>/ in a Drive folder
   python3 -I ~/.agents/skills/draft-doc/scripts/compile_markdown_doc.py \
     "$SCRATCH/report.src.md" -o "$SCRATCH/report.md" \
     --drive-folder "<FOLDER_ID>" --doc-name "<Title>.md" --json

   # Update an existing .md in place (preserves name, URL, revisions, and assets/<slug>/)
   python3 -I ~/.agents/skills/draft-doc/scripts/compile_markdown_doc.py \
     "$SCRATCH/report.src.md" -o "$SCRATCH/report.md" \
     --file-id "<FILE_ID>" --json
   ```

   Pass `--doc-name` with `--file-id` only to rename. Omit Drive flags and pass `--assets-dir "$SCRATCH/assets/<doc-slug>"` for local builds; `--check-only` validates an already compiled `.md` or single `.svg` (rejecting uncompiled `.src.md` figures).

1. **Verify by reading back**: run `gws docs documents get --params '{"documentId":"<FILE_ID>","includeTabsContent":true}'` on the native `.md` file; confirm headings, `inlineObjects`, footnotes, and tables, then report `drive.docs_url` and `drive.assets_folder_url`.

## Gotchas

- **Keep `mimeType: text/markdown` on upload**: `application/vnd.google-apps.document` converts to `.gdoc` and flattens equations into literal `$...$` text.
- **Never widen sharing unasked**: uploads inherit parent folder permissions; ask before `drive.permissions.create`.
- **Download `.md` with `alt=media`**: `drive.files.export` fails on native `.md` ("Export only supports Docs Editors files"); use `drive.files.get` with `alt=media`.

## Documentation

- [Docs Help: View and edit Markdown files in Google Docs](https://support.google.com/docs/answer/18289341) · [Workspace Updates, 2026-10-05: Markdown files natively across Drive and Docs](https://workspaceupdates.googleblog.com/2026/10/preview-edit-and-collaborate-on-Markdown-files-natively-across-Drive-and-Docs.html) · [dialect and figure reference](references/dialect.md)
- Companions: [stakeholder-writing](../stakeholder-writing/SKILL.md) (structure, prose, and reader check), [diagrams-as-code](../diagrams-as-code/SKILL.md) (Mermaid and SVG authoring), [gws](../gws/SKILL.md) (Workspace CLI and `.gdoc` `batchUpdate`), [draft-mail](../draft-mail/SKILL.md) (Gmail drafts).
