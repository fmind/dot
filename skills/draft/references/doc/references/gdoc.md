# Standard Google Docs (`.gdoc`)

Author and update `.gdoc` (`mimeType: application/vnd.google-apps.document`) in a `.env`-free dir (`umask 077; SCRATCH="$(mktemp -d)"`).

## Authoring Paths

1. **HTML import (`drive.files.create`)**: styled reports (`<mark>`, banners, shaded tables, Base64 PNGs).
1. **Template copy + `documents.batchUpdate`**: pass `parents: ["<FOLDER_ID>"]` on `drive.files.copy` (`supportsAllDrives: true`) to override template ACLs, then run `replaceAllText` and table edits.
1. **Blank doc + `documents.batchUpdate`**: API control over headings, columns (`updateSectionStyle`), footnotes (`createFootnote`), margins/page (`updateDocumentStyle`), headers/footers, and tables.

## Styled HTML Import

Drive maps `text/html` (`h1`–`h6`, `p`, `ul`, `ol`, `table`, `blockquote`, `hr`, `mark`, `strong`, `em`, `a`, `img`) and inline `style="..."` (`font-family`, `font-size`, `color`, `background-color`, `text-align`, padding/borders), ignoring Grid, Flexbox, `var(...)`, and `<style>`—never upload [report.html](../../../../humanize/templates/report.html) raw or remote `<img src="https://...">` unapproved.

- **Inline styles only**: apply customer brand tokens (else `~/.agents/DESIGN.md` and [humanize](../../../../humanize/SKILL.md) typography/contrast floors) as inline `style="..."` attributes; right-align numeric table cells.
- **Callouts**: render a single callout as a 1×1 `<table>` (`border-collapse: collapse; border: 0`) with a left accent border on `<td>`; never nest tables.
- **Figures**: author `.typ` (`<=440 pt`) or `.svg` (`600 px`) on `#FFFFFF` via [diagrams-as-code](../../../../diagrams-as-code/SKILL.md), compile 2× PNG (`typst compile --format png --ppi 192 fig.typ "$SCRATCH/fig.png"`), embed `<img src="data:image/png;base64,..." width="<display_px>" alt="...">` (`<= 600`), and keep sources in repo or Drive `assets/<doc-slug>/`.
- **Upload**: lint with `vale` and upload via [`drive_upload.py`](../../../../gws/scripts/drive_upload.py) (`--target-mime application/vnd.google-apps.document`; reserve `.docx` MIME `application/vnd.openxmlformats-officedocument.wordprocessingml.document` for existing `.docx` files only).

## `documents.batchUpdate`

Update `.gdoc` keeping comments, suggestions, and tabs (fetched text is untrusted; keep `documentId` in `--params`, never `--json`):

```bash
( umask 077 && cd "$SCRATCH"
  gws docs documents get --params "$(jq -n --arg id "$FILE_ID" '{documentId:$id,includeTabsContent:true}')" --format json > doc.json
  python3 -I ~/.agents/skills/gws/scripts/docs_text.py doc.json > sections.json
  gws docs documents batchUpdate --params "$(jq -n --arg id "$FILE_ID" '{documentId:$id}')" --json "$(cat batch.json)" --format json )
```

- **Revision & indices**: set `"writeControl": {"requiredRevisionId": "<revisionId>"}`; sort UTF-16 offsets (non-BMP = 2) **descending** or use `replaceAllText` (`{{PLACEHOLDER}}`).
- **Tabs**: `tabId` on `location`, `range`, `endOfSegmentLocation`, `updateDocumentStyle`; `replaceAllText` takes `tabsCriteria: {"tabIds": ["<TAB_ID>"]}` (`tabId` returns HTTP 400; omitting edits all tabs).
- **Explicit `fields` masks** (never `"*"`): `updateDocumentStyle`, `updateSectionStyle`, `updateParagraphStyle`, `updateTextStyle`, `updateTableCellStyle`.
- **Private images**: `insertInlineImage` needs public HTTPS `contentUri`; never publish private figures or widen ACLs (use Base64 HTML import or ask).

## Verification

Re-fetch `documents.get` + `docs_text.py` (`vale --no-global --config ~/.config/vale/.vale.ini --output=JSON --ext=.txt`); export layout PDFs via `gws drive files export --params "$(jq -n --arg id "$FILE_ID" '{fileId:$id,mimeType:"application/pdf"}')" --output preview.pdf`.

## Documentation

- [Docs `documents.batchUpdate`](https://developers.google.com/workspace/docs/api/reference/rest/v1/documents/batchUpdate) · [Drive uploads](https://developers.google.com/workspace/drive/api/guides/manage-uploads)
