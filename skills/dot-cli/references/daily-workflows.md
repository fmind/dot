# Daily Workflows

Use command help for exact options. Examples below are local reads or previews unless identified otherwise.

## Repositories

```bash
dot status . --needs-attention
dot status . --stats --json
dot pull . --dry-run --json
dot pull .
```

Explicit repository paths bypass configured workspace discovery. Status includes dirty state, upstream, ahead/behind counts, and merge/rebase/cherry-pick/revert markers. Counts use cached remote-tracking refs: status never fetches. Repository inspection failures produce `complete: false` JSON and a nonzero exit; an unavailable optional Docker daemon is reported separately. Statistics count repositories, not commits.

Pull fetches and fast-forwards; dirty repositories are skipped before fetching by default. `--dirty allow` explicitly permits a fast-forward attempt with local changes but never pushes a dirty checkout. `--push` also pushes clean repositories that are ahead and requires authority for those remote writes. Dry-run reports selected targets and policy without fetching or predicting remote changes. Cancellation stops worker subprocess groups and blocks subsequent worker commands.

## Sessions and statistics

```bash
dot agent session sync --agent codex --project . --dry-run --json
dot agent session sync --agent codex --project . --json
dot agent session stats --project . --json
dot agent prompts stats --project . --since 2026-09-01 --json
dot agent usage stats --project . --by-model --by-project --json
```

Sync supports `--agent`, `--session`, `--project`/`--cwd`, and `--since`; its date filter uses source modification time. Dry-run parses candidates but writes neither archives nor usage. Without dry-run, sync writes local archives and derived usage; usage failures remain nonzero even if conversation ingestion succeeded. `--json` emits outcome counts after completed processing, with progress on stderr; a source scan or ingestion failure can abort before a summary is available.

Session statistics separate latest sessions from retained generations and bytes; their date filter uses latest ingestion time. They report metadata status without claiming transcript validation. Prompt statistics read validated latest transcripts but emit only counts and length summaries, never message text. A prompt means an archived user message, possibly including injected context, not necessarily one human-authored turn. Dates use conversation timestamps in UTC; bounded queries exclude unparseable timestamps. Excluded, partial, or legacy sessions and bounded timestamp gaps report incomplete coverage with a nonzero exit while retaining the available statistics. Neither command measures productivity or answer quality.

Parser generation 2 uses LF-only JSONL framing, preserving valid Unicode line separators inside text. Syncing available raw sources creates new immutable generation IDs and retains generation 1 unchanged. Existing generation 1 archives remain readable and marked legacy; missing raw sources cannot be reconstructed by migration. `session list` includes a generation ID that `show` accepts directly. `--project .` resolves the current directory. Compaction and raw-source pruning remain separate, explicitly authorized operations; migration does not delete either.

## Pull requests and releases

```bash
dot pr --print
dot pr --title 'Describe the change'
dot pr --body-file ./reviewed-body.md
dot release --wait
```

`pr --print` generates a draft without contacting GitHub for publication, but still invokes the configured AI generator and its privacy gates. Normal PR creation opens the body in `$EDITOR` even when `--title` is supplied. The edited body is scanned before `gh pr create`. Noninteractive creation requires explicit `--yes`; it bypasses editing, not secret scanning. A failed or cancelled publication retains the private temporary body and prints a retry command. A supplied body avoids regeneration. PR creation requires separate authorization for the remote write.

Release retains its existing commit, push, tag, and local installation effects and requires explicit release authority. Without `--wait`, success says publication was dispatched, not delivered. `--wait` observes CD for the exact head and tag, then checks a public GitHub release with wheel and source assets; its timeout is `release.wait_timeout` (default 30 minutes). This does not verify installed clients on other machines or artifact attestation contents. On timeout, publication may still finish; inspect hosted state before retrying.
