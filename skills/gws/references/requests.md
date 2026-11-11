# File-based requests and recovery

Inspect `gws --version`, `<method> --help`, and `gws schema service.resource.method`. In `0.22.5`, `--params` holds path/query JSON and `--json` holds request-body JSON (omit path IDs and output-only fields from `--json`). Serialize UTF-8 files via Python or `jq --rawfile`—never hand-escape JSON, run `echo -e`, or interpolate text into code (`jq --rawfile` keeps trailing newlines; `"$(cat ...)"` strips them without executing contents):

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
jq -n --arg parent "$SPACE" '{parent: $parent}' > "$request_dir/params.json"
(
  cd "$request_dir"
  gws chat spaces messages create \
    --params "$(cat params.json)" \
    --json "$(cat body.json)" --dry-run
)
```

Verify dry-run method, URL, query, and body privately before dropping `--dry-run` under user authority. Keep scratch files out of Git (`umask 077`), avoid verbose HTTP logs, check exit status before parsing response JSON, preserve field masks and revision guards, and verify by reading back the returned resource ID.

## Failure decisions

| Failure                               | Next action                                                                                      |
| ------------------------------------- | ------------------------------------------------------------------------------------------------ |
| Exit 2, 401, wrong effective identity | Check `auth status` and env override presence (no values); repair the target profile once        |
| 403                                   | Check reason, scope, API enablement, and ACLs; account switches or API enablement need approval  |
| Exit 3 or 400                         | Recheck `--help`/`schema`, types, resource names, `q` escaping, and `fields`; do not blind-retry |
| Exit 4 or schema crash                | Retry bounded discovery or inspect unexpanded `schema` + referenced type                         |
| 429 or transient 5xx on a read        | Honor `Retry-After` with bounded backoff                                                         |
| Timeout/transport error on a write    | Reconcile remote state before retrying with the original idempotency key/body/account            |

Chat deduplicates retries when reusing one saved `requestId` query parameter (`messageId` is a separate `client-` custom ID); never blind-retry Gmail sends, Sheets appends, or Docs appends, or mint a fresh UUID on retry.

Sources: [CLI 0.22.5 executor](https://github.com/googleworkspace/cli/blob/v0.22.5/crates/google-workspace-cli/src/executor.rs), [Chat create](https://developers.google.com/workspace/chat/api/reference/rest/v1/spaces.messages/create).
