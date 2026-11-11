---
name: gws
description: "Use gws for Google Workspace: Gmail, Drive, Docs, Sheets, Calendar, Chat."
license: MIT
metadata:
  kind: connector
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/gws
  created: "2026-08-30"
  updated: "2026-11-11"
---

# Google Workspace CLI

Automate Drive, Docs, Sheets, Gmail, Calendar, and Chat via `gws` (use connected apps only when native document context requires them).

## Workflow

1. **Verify active profile**: inspect `gws auth status` without printing secrets (`GOOGLE_WORKSPACE_CLI_CONFIG_DIR` isolates profiles; `GOOGLE_WORKSPACE_CLI_TOKEN` / `GOOGLE_WORKSPACE_CLI_CREDENTIALS_FILE` override stored logins). Because `gws` auto-loads ancestor `.env` files, run calls from a `.env`-free scratch directory and confirm `user` before writing (`draft-doc` and `draft-mail` isolate `gws` in a private temp dir).
1. **Check command help and schema** (`--help` for flags, unexpanded `schema` for payloads):

   ```bash
   gws schema <service.resource.method>
   gws schema <service.TypeName>
   ```

1. **Start with bounded reads**: constrain filters, date windows, and `fields` in `--params`. Add `--page-all --page-limit <n>` (emits one JSON page per NDJSON line) only when needed, retaining `nextPageToken` and Drive `incompleteSearch` to detect truncation:

   ```bash
   gws drive files list --params '{"pageSize":10,"q":"trashed = false","fields":"nextPageToken,incompleteSearch,files(id,name,mimeType)"}' --format json
   ```

1. **Select the service path**: follow [service recipes](references/services.md) (or matching `gws <service> --help` `+helper` commands) for Docs tabs, Sheets ranges, Gmail MIME, Calendar times, Slides, and Drive exports.
1. **Serialize and dry-run writes**: follow [file-based requests](references/requests.md) to separate `--params` from `--json` and inspect `--dry-run` (validates local serialization only); follow [Chat formatting and threads](references/chat.md) for Chat messages.
1. **Gate consequential writes**: reuse user authority for requested edits, asking before sending mail/Chat, destructive writes, permission changes, or one-off scope grants ([dot-cli authentication](../dot-cli/references/authentication.md)). Keep mutations minimal and idempotent (`requestId` or read-before-write guards).
1. **Verify by reading back**: fetch the mutated resource and compare fields (API acceptance does not prove external delivery).

## Task guides

<!-- guides:start -->

- [cli-details](references/cli-details.md): Use local Workspace helpers and diagnose CLI authentication, schema, pagination, or request failures.

<!-- guides:end -->

## Official Skills

Upstream: [googleworkspace/cli skills](https://github.com/googleworkspace/cli/tree/main/skills) (`DISABLE_TELEMETRY=1 skills add googleworkspace/cli --list`); install selected service skills plus their shared base skill under [vendor-skill policy](../agent-project/references/vendor-skills.md).

## Documentation

- [Google Workspace CLI](https://github.com/googleworkspace/cli) · [Workspace API reference](https://developers.google.com/workspace)
- Releases: [Workspace CLI](https://github.com/googleworkspace/cli/releases) · [changelog](https://github.com/googleworkspace/cli/blob/main/CHANGELOG.md)
- Companions: [draft-doc](../draft-doc/SKILL.md) (Google Docs: native `.md` for living docs, `.gdoc` for styled deliverables), [draft-mail](../draft-mail/SKILL.md) (draft-only email and replies), [acli](../acli/SKILL.md) (same authority rules for Atlassian), [gcloud](../gcloud/SKILL.md) (Google Cloud), [mcp-setup](../agent-harnesses/references/mcp-setup.md) (connected apps).
