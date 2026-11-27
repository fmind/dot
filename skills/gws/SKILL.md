---
name: gws
description: "Read, search, export, upload, and admin Google Workspace (Gmail, Drive, Docs, Slides, Sheets, Calendar, Chat) via gws; use draft for authoring."
license: MIT
metadata:
  kind: connector
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/gws
  created: "2026-08-30"
  updated: "2026-11-24"
---

# Google Workspace CLI

Read, search, export, upload, and administer Drive, Docs, Slides, Sheets, Gmail, Calendar, and Chat via `gws` (use [draft](../draft/SKILL.md) for drafting deliverables and connected apps only when native document context requires them).

## Workflow

1. **Verify active profile**: inspect `gws auth status` without printing secrets (`GOOGLE_WORKSPACE_CLI_CONFIG_DIR` isolates profiles; `GOOGLE_WORKSPACE_CLI_TOKEN` / `GOOGLE_WORKSPACE_CLI_CREDENTIALS_FILE` override logins). Because `gws` auto-loads ancestor `.env` files, run from a `.env`-free temp dir and confirm `user` before writing (`drive_upload.py` and `draft_*.py` isolate `gws` automatically).
1. **Check command help and schema** (`--help` for flags, unexpanded `schema` for payloads; see [CLI details and helpers](references/cli-details.md)):

   ```bash
   gws schema <service.resource.method>
   gws schema <service.TypeName>
   ```

1. **Start with bounded reads**: constrain filters, date windows, and `fields` in `--params`. Add `--page-all --page-limit <n>` (emits one JSON page per NDJSON line) only when needed, retaining `nextPageToken` and Drive `incompleteSearch` to detect truncation:

   ```bash
   gws drive files list --params '{"pageSize":10,"q":"trashed = false","fields":"nextPageToken,incompleteSearch,files(id,name,mimeType)"}' --format json
   ```

1. **Select the service path**: follow [service recipes](references/services.md) (or matching `gws <service> --help` `+helper` commands) for Docs tabs, Sheets ranges, Gmail MIME, Calendar times, Slides, and Drive exports/uploads.
1. **Serialize and dry-run writes**: follow [file-based requests](references/requests.md) to separate `--params` from `--json` and inspect `--dry-run` (validates local serialization only); follow [Chat formatting and threads](references/chat.md) for Chat messages.
1. **Gate consequential writes**: reuse authority for requested edits; ask before sending mail/Chat, destructive writes, permission changes, or one-off scope grants ([dot-cli authentication](../dot-cli/references/authentication.md)). Keep mutations minimal and idempotent (`requestId` or read-before-write).
1. **Verify by reading back**: fetch the mutated resource and compare fields (API acceptance ≠ external delivery).

## References

- [services.md](references/services.md): Drive, Docs, Sheets, Gmail, Calendar, and Slides recipes.
- [requests.md](references/requests.md): File-based request serialization, dry-run checks, and failure decisions.
- [chat.md](references/chat.md): Google Chat markup modes, thread replies, and verification.
- [cli-details.md](references/cli-details.md): Local Workspace helpers and `gws` CLI diagnostics.

## Official Skills

Upstream: [googleworkspace/cli skills](https://github.com/googleworkspace/cli/tree/main/skills); audit before installing under [vendor-skill policy](../agent-harnesses/references/vendor-skills.md).

## Documentation

- [Google Workspace CLI](https://github.com/googleworkspace/cli) · [Workspace API reference](https://developers.google.com/workspace)
- Releases: [Workspace CLI](https://github.com/googleworkspace/cli/releases) · [changelog](https://github.com/googleworkspace/cli/blob/main/CHANGELOG.md)
- Companions: [draft](../draft/SKILL.md) (Docs, Typst/Google Slides, Sheets, Gmail drafts), [acli](../cloud-ops/references/acli.md), [gcloud](../gcloud/SKILL.md), [mcp-setup](../agent-harnesses/references/mcp-setup.md).
