---
name: gws
description: "Use gws for Google Workspace: Gmail, Drive, Docs, Sheets, Calendar, and Chat."
license: MIT
metadata:
  kind: connector
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/gws
  created: "2026-08-30"
  updated: "2026-10-06"
---

# Google Workspace CLI

Use `gws` for Google Workspace automation from the shell: authentication, API discovery, bounded reads, and verified writes across Drive, Docs, Sheets, Gmail, Calendar, and Chat. Prefer the CLI for supported operations; use a connected app when the requested native editing operation needs its document context or capabilities.

## Workflow

1. **Resolve the profile**: check `gws auth status` for the account and scopes without printing credentials. Set `GOOGLE_WORKSPACE_CLI_CONFIG_DIR` before auth commands to isolate profiles; an existing `GOOGLE_WORKSPACE_CLI_TOKEN` or `GOOGLE_WORKSPACE_CLI_CREDENTIALS_FILE` can override stored credentials, so verify the effective identity without echoing those values.
1. **Inspect the installed command and live schema**: use `<command> --help` for flags and `schema` for the API contract. Start without recursive reference expansion; inspect a referenced type separately when needed.

   ```bash
   gws schema <service.resource.method>
   gws schema <service.TypeName>
   ```

1. **Start with a bounded read**: pass identifiers, filters, and only the needed fields and date range through `--params`; use `--page-all --page-limit <n>` only when every page is needed. It emits NDJSON with one object per page, not one JSON array; keep `nextPageToken` (and Drive `incompleteSearch`) in `fields`, because reaching `--page-limit` with a remaining token means the result is incomplete.

   ```bash
   gws drive files list --params '{"pageSize":10,"q":"trashed = false","fields":"nextPageToken,incompleteSearch,files(id,name,mimeType)"}' --format json
   ```

1. **Choose the content path**: read [service recipes](references/services.md) for metadata versus bodies, Docs tabs, Sheets ranges, Gmail MIME/replies, Calendar times, Slides and Drive exports. Prefer a `+helper` listed by `gws <service> --help` when its documented semantics match the request.
1. **Prepare writes exactly**: resolve the service, stable identifiers or ranges, content, recipients, and sharing effects first. Follow [file-based requests](references/requests.md) to serialize multiline content, separate `--params` from `--json`, and inspect a `--dry-run`. It validates request construction, not permissions or server acceptance. For Chat, follow [formatting and threads](references/chat.md) before composing text.
1. **Write with authority**: reuse authority already supplied by the user for the intended create or edit; ask only for missing consequential scope. Sending mail or Chat, destructive changes, and permission changes require explicit authority. Prepare the concrete request before asking for missing approval.
1. **Apply the smallest call**: no broad search followed by an unreviewed batch mutation; keep retries idempotent with stable request identifiers or a read-before-write guard where the API supports them.
1. **Verify by reading back**: fetch the changed resource and compare the requested fields; for messages and events, separate accepted API state from recipient-visible delivery.

## Task guides

<!-- guides:start -->

- [cli-details](references/cli-details.md): Use local Workspace helpers and diagnose CLI authentication, schema, pagination, or request failures.

<!-- guides:end -->

## Official Skills

Upstream: [googleworkspace/cli skills](https://github.com/googleworkspace/cli/tree/main/skills), which generates a shared base skill plus one selection per API. Discover with `skills add googleworkspace/cli --list`. Follow the shared [vendor-skill policy](../agent-project/references/vendor-skills.md) and include the base dependency required by the chosen service.

## Documentation

- [Google Workspace CLI](https://github.com/googleworkspace/cli) · [Workspace API reference](https://developers.google.com/workspace)
- Releases: [Workspace CLI](https://github.com/googleworkspace/cli/releases) · [changelog](https://github.com/googleworkspace/cli/blob/main/CHANGELOG.md)
- Companion skills: [draft-mail](../draft-mail/SKILL.md) (draft-only email and replies), [acli](../acli/SKILL.md) (same authority rules for Atlassian), [gcloud](../gcloud/SKILL.md) (Google Cloud), [mcp-setup](../mcp-setup/SKILL.md) (connected apps).
