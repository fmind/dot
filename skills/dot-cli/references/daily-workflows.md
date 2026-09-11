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

Session statistics separate latest sessions from retained generations and bytes; their date filter uses latest ingestion time. They report metadata status without claiming transcript validation. Prompt statistics read validated latest transcripts but emit only counts and length summaries, never message text. A prompt means an archived user message, possibly including injected context, not necessarily one human-authored turn. Dates use conversation timestamps in UTC; bounded queries exclude unparseable timestamps. Excluded or partial sessions and bounded timestamp gaps report incomplete coverage with a nonzero exit while retaining the available statistics. Neither command measures productivity or answer quality.

Parser generation 4 keeps LF-only JSONL framing and publishes manifest schema 2 with `transcript.jsonl` and `usage.json`. Usage is `available` or `unsupported`; failed extraction is reported and never published as a complete generation. Copilot reads transcript and usage in one database read transaction. Grok fingerprints both transcript and signals snapshots, including signals-only sessions. A changed source creates a new immutable generation. The active `sessions/v2` store reads parser 3 and 4 bundles; parser 3 remains legacy evidence, while recapture creates parser 4 without rewriting history. Earlier stores remain untouched and are not queried.

Usage queries select one bundle per session from the active store, preferring the newest admitted parser, then latest ingestion. They count a session once across generations. A selected bundle with unsupported usage does not silently reuse an older measurement. Use `dot agent session sync` for explicit recapture of available provider sources. Unknown costs remain unknown, and unlike measurement kinds remain separate.

`session list` includes a generation ID accepted by `show`; `--project .` resolves the current directory. Session list/statistics date filters use ingestion timestamps, source-sync filters use source modification time, prompt statistics use conversation timestamps, and usage filters use request timestamps when reliable samples exist, otherwise whole sessions by measurement timestamp (capture time when the source has no timestamp). Dates are interpreted in UTC. Explicit generation identities can select historical data.

For quick token totals and coverage dates, use `dot agent stats --tokens-only`; add `--monthly` for calendar months or `--billing --harness codex` for configured subscription cycles. The [usage guide](../../agent-usage/SKILL.md) owns accounting, pricing completeness, and renewal settings.

## Cleanup and recovery

Use the Dot CLI for cache inspection and cleanup:

```bash
dot cache
dot cache docker
dot prune all --dry-run
dot prune all --yes
dot prune docker --yes
```

`dot cache` inspects the configured `cache.providers` (Docker, Hugging Face, uv by default). `dot prune` displays help; `dot prune all` cleans `prune.providers` (dprint, Hugging Face, mise, npm, Trivy, uv by default); Docker builder cleanup requires explicit selection or inclusion in that configuration. The command confirms the selected providers once before any cleanup and needs `--yes` without a terminal. `--dry-run` displays commands, not reclaimable bytes, and executes no providers. Both aggregates preflight required tools and stop on command failure; earlier successful operations are not rolled back. Each provider can be selected independently. Native tools retain caller directory, profile, environment, and output.

Installed tools, credentials, provider sessions, and Dot archives are outside the default cleanup aggregate. Login, setup, and cleanup run only when invoked; they are not installation hooks. `dot login` and `dot setup` display help without a provider. `dot login all` runs Workspace followed by Google Cloud and ADC, stopping on failure; GitHub remains explicit. Authentication checks are bounded by `auth.probe_timeout_seconds`, require usable credentials, and compare requested OAuth scopes where reported. Additional granted scopes do not force login. `dot setup github` also reconciles `auth.github.remove_scopes`. GCP checks CLI and ADC credentials separately; it does not assert they represent the same identity. No Dot credential cache is maintained.

Workspace setup enables only missing configured APIs and skips OAuth client setup when the selected project already has a readable client configuration. Project selection is argument, `GWS_PROJECT`, then `auth.workspace.project`; GitHub host selection is `--host`, `GH_HOST`, then `auth.github.host`. API access and role grants remain provider-owned. `--force` on login explicitly repeats authentication; it cannot bypass an environment credential override that makes OAuth changes ineffective. Unknown or failed probes stop without printing captured tokens or provider payloads.

```bash
dot agent session compact
dot agent session compact --agent codex --apply
dot agent clean
```

Compaction validates the complete selection before deletion, retains divergent transcripts and distinct usage evidence, and groups by parser version. Unsupported formats stop the operation before any deletion. `dot agent clean --apply` removes only generated `.agents/prompts`, `.agents/proposals`, and `.agents/reports` in the selected Git project. Provider sessions, private skills, and tool caches are outside both cleanup commands.

## Repository publication

Commit and PR authoring belong to their skills, which use staged Git changes, explicit repository/base selection, privacy checks, and reviewed publication artifacts. In fmind/dot, `mise run release -- --wait` runs the repository release service. It preserves version/lock rollback, exact commit/tag reconciliation, and bounded publication checks; it requires explicit release authority. A local dispatch is not hosted publication evidence.

## Fish completions

`dot completion` refreshes native Fish completions and the Atuin/Carapace initialization caches. `completions.tools` is the explicit selection; `dot config show` lists its defaults, including `dot` and `fkf`. Each entry in `completions.custom_commands` selects a native generator (`binary` and `args`) or a mise package containing a bundled `<tool>.fish` script (`package`). These source types are mutually exclusive. Unlisted custom tools use `<tool> completion fish`.

Missing executables are skipped. Failed generators or invalid Fish syntax produce a nonzero exit and preserve the previous script; successful scripts are replaced atomically. Native completions take precedence over Carapace, whose `dot` completer otherwise targets Graphviz. Tools without native Fish generators rely on Fish or Carapace support where available. The command does not delete independently installed completion files.
