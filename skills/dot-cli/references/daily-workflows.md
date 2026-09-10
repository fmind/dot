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

Sync supports `--agent`, `--session`, `--project`/`--cwd`, and `--since`; its date filter uses source modification time. Dry-run parses candidates but writes neither archives nor usage. Without dry-run, sync publishes transcript and usage together. Failed extraction or publication aborts that generation; repeat the command after repairing the cause. Earlier successfully published sessions remain valid and retries deduplicate them. `--json` emits outcome counts after completed processing, with progress on stderr; a source scan or ingestion failure can abort before a summary is available.

Session statistics separate latest sessions from retained generations and bytes; their date filter uses latest ingestion time. They report metadata status without claiming transcript validation. Prompt statistics read validated latest transcripts but emit only counts and length summaries, never message text. A prompt means an archived user message, possibly including injected context, not necessarily one human-authored turn. Dates use conversation timestamps in UTC; bounded queries exclude unparseable timestamps. Excluded, partial, or legacy sessions and bounded timestamp gaps report incomplete coverage with a nonzero exit while retaining the available statistics. Neither command measures productivity or answer quality.

Parser generation 3 keeps LF-only JSONL framing and publishes manifest schema 2 with `transcript.jsonl` and `usage.json`. Usage is `available` or `unsupported`; failed extraction is reported and never published as a complete generation. Copilot reads transcript and usage in one database read transaction. Grok fingerprints both transcript and signals snapshots, including signals-only sessions. A changed source creates a new immutable generation. Legacy parser 1/2 archives remain readable and marked legacy; migration cannot reconstruct missing raw sources.

Usage queries select one latest supported bundle per session and fall back to legacy standalone usage only when no bundle exists. They count a session once across generations. A selected bundle with unsupported usage does not silently reuse an older measurement. Use `dot agent session sync` for migration and backfills; the former standalone usage-sync writer is removed. Unknown costs remain unknown, and unlike measurement kinds remain separate.

`session list` includes a generation ID accepted by `show`; `--project .` resolves the current directory. Session list/statistics date filters use ingestion timestamps, source-sync filters use source modification time, prompt statistics use conversation timestamps, and usage filters include whole sessions by the measurement timestamp (capture time when the source has no timestamp). Dates are interpreted in UTC. Explicit generation identities can select historical data.

## Cleanup and recovery

```bash
dot agent session compact
dot agent session compact --agent codex --apply
dot agent clean
```

Compaction validates the complete selection before deletion, retains divergent transcripts and distinct usage evidence, and groups by parser version. Legacy generations remain available through migration. `dot agent clean --apply` removes only generated `.agents/prompts`, `.agents/proposals`, and `.agents/reports` in the selected Git project. Provider sessions, private skills, and tool caches are outside both cleanup commands.

## Repository publication

Commit and PR authoring belong to their skills, which use staged Git changes, explicit repository/base selection, privacy checks, and reviewed publication artifacts. In fmind/dot, `mise run release -- --wait` runs the repository release service. It preserves version/lock rollback, exact commit/tag reconciliation, and bounded publication checks; it requires explicit release authority. A local dispatch is not hosted publication evidence.
