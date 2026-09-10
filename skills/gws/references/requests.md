# File-based requests and recovery

Check `gws --version`, the exact method's `--help`, and `gws schema service.resource.method`. Version 0.22.5's executor parses `--params` and `--json` as JSON strings. `--params` contains URL/query values; `--json` contains only the request body. Do not put a resource ID in the body when the schema requires it in the path, or pass output-only fields back to the API.

For content, author a UTF-8 file using the editor or a quoted heredoc. Serialize with Python or `jq --rawfile`; never hand-escape JSON, use `echo -e`, interpolate content into Python/shell source, or decode escapes twice. A quoted command substitution returns data without executing the contents of the file. `jq --rawfile` preserves its final newline; shell substitution on raw text removes final newlines.

```bash
umask 077
request_dir=$(mktemp -d)
cat > "$request_dir/message.txt" <<'TEXT'
*Review ready*
- Check the proposed change.
- Keep `$(example)` as literal text.
TEXT
uv run --no-project python ~/.agents/skills/gws/scripts/chat_body.py \
  "$request_dir/message.txt" > "$request_dir/body.json"
# Set SPACE from a previously resolved, authorized destination.
jq -n --arg parent "$SPACE" '{parent: $parent}' > "$request_dir/params.json"
gws chat spaces messages create \
  --params "$(cat "$request_dir/params.json")" \
  --json "$(cat "$request_dir/body.json")" --dry-run
```

Inspect the dry-run method, URL, query and body privately. Remove `--dry-run` only under the user's existing authority for that exact operation. Local serialization is not permission checking, delivery, or visual verification. Keep sensitive request/output files outside Git, do not echo credentials or enable verbose HTTP logs, and remove only the scratch directory owned by this operation when its evidence is no longer needed.

For an authorized write, save stdout to a response file and inspect its exit status before parsing. Read back the returned stable resource name and compare the fields that matter. Distinguish an absent optional field from an empty value, and preserve explicit field masks and revision guards on edits.

## Failure decisions

| Failure | Next action |
| --- | --- |
| Exit 2, 401, wrong effective identity | Inspect auth status/profile and environment override presence without values; repair the intended profile once |
| 403 | Inspect returned reason, scope, API enablement and resource permissions; changing accounts or enabling an API needs the applicable authority |
| Exit 3 or 400 | Recheck help/schema, JSON types, resource names, query syntax and field mask; no identical retry |
| Exit 4 or schema crash | Retry a bounded discovery read or inspect an unexpanded schema and referenced type; report persistent failure |
| 429 or transient 5xx on a read | Honor Retry-After when provided and use bounded backoff within the task window |
| Timeout/transport error on a write | Record unknown outcome and reconcile remote state before retry; retain the same idempotency ID/body/account when supported |

Chat supports a `requestId` query value for idempotency; generate it once per intended message, save it with the params, and reuse it only for an identical retry. `messageId` is a separate optional custom resource identifier with a `client-` prefix and documented constraints. Gmail send, Sheets append and Docs append must not be blindly repeated after an uncertain reply. A newly generated UUID does not deduplicate the previous write.

Sources: [CLI 0.22.5 executor](https://github.com/googleworkspace/cli/blob/v0.22.5/crates/google-workspace-cli/src/executor.rs), [Chat create](https://developers.google.com/workspace/chat/api/reference/rest/v1/spaces.messages/create).
