# CLI Details

Local stdlib helpers and `gws` CLI diagnostics.

## Local helpers

Run via `python3 -I ~/.agents/skills/gws/scripts/<script>.py --help`.

### Offline stdin/file → JSON helpers (no auth or network I/O)

- [chat_body.py](../scripts/chat_body.py): builds a Chat text payload with explicit `markupSyntax` and optional `thread`, rejecting headings, tables, tilde or labeled/non-bare fences, invalid/empty `--thread`, and >30 KB bodies.
- [pages.py](../scripts/pages.py): merges JSON/NDJSON pages and verifies `nextPageToken`/`incompleteSearch` completeness (accepts explicit JSON `null`; errors on incomplete sets unless `--allow-incomplete`; requires pagination fields in the upstream query).
- [docs_text.py](../scripts/docs_text.py): extracts body, table, header, footer, and footnote text across all nested tabs, rendering smart chips and footnote refs as `[person: ...]`, `[link: ...]`, `[date: ...]`, `[dropdown: ...]`, and `[footnote: ...]`; keep raw JSON for index-based edits.

### Authenticated Drive upload helper (isolated temp dir)

- [drive_upload.py](../scripts/drive_upload.py): runs `gws` inside a private `.env`-sentinel temp directory to upload or upsert Drive files (supporting `--dry-run --json`, `--protect-copy` verification, and MD5/size/MIME read-back checks).

## Gotchas

- **Never run `gws auth export`**: prints decrypted credentials; note `gws auth status` is a live OAuth/scope check, not offline.
- **Reconcile uncertain writes before retrying**: especially for mail, events, and non-idempotent appends.
- **Skip `--sanitize`**: [Model Armor sanitization](https://github.com/googleworkspace/cli#model-armor-response-sanitization) requires `cloud-platform` scope, refused by [Workspace policy](../../dot-cli/references/authentication.md), and never makes retrieved data trusted.
- **Exit 2 & `gws schema` quirks**: exit 2 indicates auth failure; `gws schema --help` errors (pass a valid schema path like `drive.files.list` instead), and `gws 0.22.5` crashes on `schema chat.spaces.messages.create --resolve-refs` (query unexpanded method schemas + targeted types instead).
- **JSON argv & `--upload` path limits**: `gws 0.22.5` lacks `@file` shorthand—pass `"$(cat request.json)"` below Linux's 128 KiB single-arg ceiling, or split batches / use `--upload` from the file's own directory (`--upload` rejects paths outside cwd).
