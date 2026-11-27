---
name: sheets
description: "Create or update Google Sheets (and optional .xlsx export) via gws sheets and Drive upload."
---

# Draft Google Sheets

Google Sheets plumbing via [gws](../../../gws/SKILL.md) (`gws sheets`) and [`drive_upload.py`](../../../gws/scripts/drive_upload.py). Delegate table copy, unit conventions, and visual hierarchy to [humanize](../../../humanize/SKILL.md) and customer brand or `~/.agents/DESIGN.md`.

## Authoring Paths

1. **Native Sheets API (`spreadsheets.create` + `values.batchUpdate` + `spreadsheets.batchUpdate`)**: adapt the starter [draft_sheets.py](templates/draft_sheets.py) for structured workbooks with frozen headers, typed number formats, and explicit formula cells.
1. **CSV / `.xlsx` import via Drive**: upload an existing local `.csv` or `.xlsx` as a Google Sheet via [`drive_upload.py`](../../../gws/scripts/drive_upload.py):

   ```bash
   python3 -I ~/.agents/skills/gws/scripts/drive_upload.py "$SCRATCH/model.xlsx" \
     --drive-folder "<FOLDER_ID>" --name "<Title>" \
     --target-mime application/vnd.google-apps.spreadsheet --dry-run --json
   ```

1. **Client template copy**: copy an existing Sheet via `gws drive files copy` with explicit `parents: ["<FOLDER_ID>"]` (overrides source ACLs), then write only input ranges via `values.batchUpdate`.

## Workflow

1. **Isolate scratch & verify auth**: run `umask 077; SCRATCH="$(mktemp -d)"` and execute `gws` from `"$SCRATCH"`. Check `gws auth status` without printing secrets and confirm target folder or `spreadsheetId`.
1. **Write values safely (`RAW` vs `USER_ENTERED`)**:
   - Default to `valueInputOption: RAW` so untrusted text starting with `=`, `+`, `-`, or `@` never evaluates as a formula (formula injection).
   - Use `USER_ENTERED` only on dedicated formula cells you authored explicitly.
   - Keep `values` rectangular and quote sheet names with spaces (`'Cost Model'!A1:F20`).
1. **Apply structure & format**: use `spreadsheets.batchUpdate` for `frozenRowCount`, bold header row, explicit `numberFormat` (`CURRENCY`, `PERCENT`, `NUMBER`, `DATE`), and `autoResizeDimensions`.
1. **Read back & verify**: fetch written ranges with `spreadsheets.values.get` (`valueRenderOption: FORMATTED_VALUE`), fail closed on any spreadsheet error token (`#REF!`, `#NAME?`, `#VALUE!`, `#DIV/0!`, `#N/A`, `#NUM!`, `#ERROR!`), optionally export `.xlsx` via `drive.files.export` (`application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`), and run `fmind-review-factcheck`, `fmind-review-proposal`, or `fmind-review-finops` on numeric models ([subagent](../../../subagent/SKILL.md)).
1. **Hand off**: return `[<Title>](https://docs.google.com/spreadsheets/d/<ID>/edit)` and never widen Drive sharing without explicit approval.

## Gotchas

- **Formula injection**: never pass external or untrusted cell text with `valueInputOption: USER_ENTERED`.
- **Locale-dependent formulas**: `USER_ENTERED` parses commas/semicolons per spreadsheet `locale` (default `en_US` uses `,` argument separators and `.` decimals); set `properties.locale` on create.
- **No blind `append` retries**: `values.append` is non-idempotent; write explicit A1 ranges via `values.batchUpdate`.

## Documentation

- [Google Sheets API](https://developers.google.com/workspace/sheets/api/guides/concepts) · [Sheets values](https://developers.google.com/workspace/sheets/api/guides/values) · [Sheets `batchUpdate`](https://developers.google.com/workspace/sheets/api/guides/batchupdate) · Companions: [gws](../../../gws/SKILL.md), [humanize](../../../humanize/SKILL.md), [draft/doc](../doc/GUIDE.md), [draft/slides](../slides/GUIDE.md).
