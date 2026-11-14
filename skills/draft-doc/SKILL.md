---
name: draft-doc
description: "Create and update Google Docs with gws: Markdown with Typst/Mermaid/SVG figures or .gdoc."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/draft-doc
  created: "2026-10-27"
  updated: "2026-11-14"
---

# Draft Doc

Create and update Google Docs deliverables in Drive with `gws`, following [humanize](../humanize/SKILL.md) ([outlines](../humanize/references/outlines.md), [primitives](../humanize/references/primitives.md)). [gws](../gws/SKILL.md) owns auth, Drive queries, and request mechanics.

## Format Choice

1. **Native Drive Markdown (`.md`, `mimeType: text/markdown`) for living docs**: agent-maintained or collaborative docs that update cleanly in place via `drive.files.update --upload` without `batchUpdate` index math. Put colored KPIs, flowcharts, and highlight callouts inside compiled Typst PNG cards (`<=440 pt` wide) because Docs ignores inline HTML styles inside `.md`.
1. **Converted Google Doc (`.gdoc`, `mimeType: application/vnd.google-apps.document`) for styled deliverables**: upload rich HTML (`--mime-type text/html` converted to `application/vnd.google-apps.document` via `gws drive files create`) to preserve `<mark>` highlights, tinted summary banners, and custom table fills, or patch existing templates via [gws Docs recipes](../gws/references/services.md#docs). Editing raw Markdown in Docs strips highlights and colors ([Docs Help 18289341](https://support.google.com/docs/answer/18289341)).

## Branding

Style [Typst](../diagrams-as-code/references/typst.md) cards (`~/.agents/themes/typst/fmind.typ`), [Mermaid](../diagrams-as-code/references/mermaid.md) frontmatter, and SVG figures with `~/.agents/DESIGN.md` (Fmind Theme), or the customer's brand guide (ask if missing; never invent colors or mix brands). Keep an opaque white canvas for dark-mode legibility.

## Native `.md` Dialect Rules

Verified live on 2026-10-28 ([references/dialect.md](references/dialect.md)) and enforced by [`scripts/compile_markdown_doc.py`](scripts/compile_markdown_doc.py):

1. **No YAML frontmatter or Setext underlines**: `---` or `===` directly under a paragraph turns it into a heading. Put metadata lines below `# Title` and leave a blank line before horizontal rules.
1. **No GitHub alerts, raw HTML, or HTML comments**: all render as literal text. Use bold blockquotes (`> **Important — Decision needed by YYYY-MM-DD:** ...`), `## Annex` headings, and trailing `\` for hard breaks.
1. **Compile figures to PNG references**: write local `![Caption](figure.typ)` links (best for KPI strips, decision cards, and charts; zero browser needed), column-0 `mermaid` fences, or local 600 px `![Caption](figure.svg)` links in `.src.md`. [`scripts/compile_markdown_doc.py`](scripts/compile_markdown_doc.py) rasterizes each at up to 600 px wide (with automatic Google Sans font discovery for Typst), emits Base64 PNG references, and exports editable sources to `--assets-dir` ([details](references/dialect.md)).
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

   Pass `--doc-name` with `--file-id` only to rename. Omit Drive flags and pass `--assets-dir "$SCRATCH/assets/<doc-slug>"` for local builds; `--check-only` validates an already compiled `.md` or single `.typ`/`.svg` (rejecting uncompiled `.src.md` figures).

1. **Verify by reading back**: run `gws docs documents get --params '{"documentId":"<FILE_ID>","includeTabsContent":true}'` on the native `.md` file; confirm headings, `inlineObjects`, footnotes, and tables, then report `drive.docs_url` and `drive.assets_folder_url`.

## Gotchas

- **Keep `mimeType: text/markdown` on upload**: `application/vnd.google-apps.document` converts to `.gdoc` and flattens equations into literal `$...$` text.
- **Never widen sharing unasked**: uploads inherit parent folder permissions; ask before `drive.permissions.create`.
- **Download `.md` with `alt=media`**: `drive.files.export` fails on native `.md` ("Export only supports Docs Editors files"); use `drive.files.get` with `alt=media`.

## Documentation

- [Docs Help: View and edit Markdown files in Google Docs](https://support.google.com/docs/answer/18289341) · [Workspace Updates, 2026-10-05: Markdown files natively across Drive and Docs](https://workspaceupdates.googleblog.com/2026/10/preview-edit-and-collaborate-on-Markdown-files-natively-across-Drive-and-Docs.html) · [dialect and figure reference](references/dialect.md)
- Companions: [humanize](../humanize/SKILL.md) (signal curation, visual hierarchy, and reader check), [diagrams-as-code](../diagrams-as-code/SKILL.md) (Typst, Mermaid, and SVG authoring), [gws](../gws/SKILL.md) (Workspace CLI and `.gdoc` `batchUpdate`), [draft-mail](../draft-mail/SKILL.md) (Gmail drafts).
