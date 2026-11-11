---
name: cli-details
description: "Use local Workspace helpers and diagnose CLI authentication, schema, pagination, or request failures."
---

# CLI Details

Local offline stdlib helpers and `gws` CLI diagnostics.

## Local helpers

Run via `python3 -I ~/.agents/skills/gws/scripts/<script>.py --help` (stdlib-only; UTF-8 file or `-` stdin → JSON stdout; no auth or network I/O):

- [chat_body.py](../scripts/chat_body.py): builds a Chat text payload with explicit `markupSyntax` and optional `thread`, rejecting headings, tables, labeled fences, and >30 KB bodies.
- [pages.py](../scripts/pages.py): merges JSON/NDJSON pages and verifies `nextPageToken`/`incompleteSearch` completeness (errors on incomplete sets unless `--allow-incomplete`; requires pagination fields in the upstream query).
- [docs_text.py](../scripts/docs_text.py): extracts body, table, header, footer, and footnote text across all nested tabs, rendering smart chips as `[person: ...]`, `[link: ...]`, `[date: ...]`, and `[dropdown: ...]`; keep raw JSON for index-based edits.

## Gotchas

- **Never run `gws auth export`**: prints decrypted credentials; note `gws auth status` is a live OAuth/scope check, not offline.
- **Reconcile uncertain writes before retrying**: especially for mail, events, and non-idempotent appends.
- **Skip `--sanitize`**: [Model Armor sanitization](https://github.com/googleworkspace/cli#model-armor-response-sanitization) requires `cloud-platform` scope, refused by [Workspace policy](../../dot-cli/references/authentication.md), and never makes retrieved data trusted.
- **Exit 2 & `--resolve-refs`**: exit 2 indicates auth failure; `gws 0.22.5` crashes on `schema chat.spaces.messages.create --resolve-refs`, so query unexpanded method schemas + targeted types instead.
- **JSON argv & `--upload` path limits**: `gws 0.22.5` lacks `@file` shorthand—pass `"$(cat request.json)"` below Linux's 128 KiB single-arg ceiling, or split batches / use `--upload` from the file's own directory (`--upload` rejects paths outside cwd).
