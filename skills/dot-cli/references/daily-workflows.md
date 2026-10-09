# Daily Workflows

Use command help for exact options. Examples below are local reads or previews unless identified otherwise.

## Repositories

```bash
dot status . --needs-attention
dot status --fetch --json              # refresh remote refs (fetch only, never merge) before counting
dot pull . --dry-run --json
dot pull .                              # authorized local update: fetches and fast-forwards
```

Explicit repository paths bypass configured workspace discovery. Status includes dirty state, upstream, ahead/behind counts, and merge/rebase/cherry-pick/revert markers. Counts use cached remote-tracking refs unless `--fetch` first runs `git fetch --prune` (never a merge) within the `pull.timeout_seconds` allowance; a fetch failure marks that repository failed. `--needs-attention` hides clean repositories and prints an all-clear line when none remains. Repository inspection failures produce `complete: false` JSON and a nonzero exit. Docker health belongs to `dot doctor`.

Pull fetches once and fast-forwards the fetched upstream without a second fetch; fetch failures always produce a nonzero exit, including on branches without an upstream; dirty repositories are skipped before fetching by default. Git runs with terminal and askpass credential prompts disabled, so a missing credential fails that repository instead of blocking its worker. `--dirty allow` explicitly permits a fast-forward attempt with local changes but never pushes a dirty checkout. `--push` also pushes clean repositories that are ahead and requires authority for those remote writes; it rechecks the worktree after fetch/merge before pushing. Dry-run reports selected targets and policy without fetching or predicting remote changes. Pull and status cancellation stop worker subprocess groups and block subsequent worker commands; filesystem failures in one repository preserve the other results in incomplete JSON reports.

## Folder trust

```bash
dot trust --dry-run
dot trust                               # authorized trust change for this repository
dot trust all                           # authorized trust change across configured workspaces
```

`dot trust [PATH]` pre-accepts folder trust for the repository containing `PATH` (default `.`) in every installed harness: Claude (`~/.claude.json`), Codex, Grok, agy, and Copilot. `all` covers each `pull.directories` workspace and the repositories directly inside it whose `origin` is a github.com repository of a `trust.github_owners` owner (default `fmind`, `fmind-ai`, `mlops-courses`; compared case-insensitively); other repositories are listed as skipped, and an explicit `dot trust PATH` still trusts any repository. `chezmoi apply` runs it. Entries are added or updated to trusted, never removed; unrelated host settings are preserved, and harnesses without a state directory are skipped; when none has one, the run reports that nothing was trusted. Claude, Codex, Grok, and agy key trust on the repository root, so a new clone needs `dot trust` (or the next apply). Copilot trusts every descendant of a trusted workspace: the owner allowlist filters individual repository entries, not that inherited trust. Mise trust is separate and machine-local: use `mise trust /path/to/mise.toml`, or set `[settings].trusted_config_paths` in unmanaged `~/.config/mise/conf.d/trust.toml` for selected directory trees. `dot trust` does not configure mise.

## Sessions and statistics

```bash
dot agent session sync --agent codex --project . --dry-run --json
dot agent session sync --agent codex --project . --json
dot agent stats --prompts-only --project . --since 2026-09-01 --json
dot agent stats --tokens-only --project . --by-model --by-project --json
```

Sync is incremental: it parses only new or changed sources, skipping one whose size and modification time match the archived copy. For the Copilot and OpenCode databases, `--since` compares the database's modification time, so it selects all or none of their sessions. Dry-run parses changed candidates but writes nothing. Unreadable source directories fail the scan instead of being silently skipped. A failed session or source scan writes one stderr line, increments `failed`, and sync continues, exiting 1 at the end; a misconfigured source path still fails fast. `--json` emits [`dot.agent.session.sync/v2`](contracts.md#json-selectors) with progress on stderr. `dot agent stats` (including `--sessions`) runs the same sync quietly first: failures appear on stderr and the report still prints. Pass `--no-sync` to report the archive as stored; an unknown `--agent` fails before any sync, and `--agent` lists the valid names in `--help`.

Sync never replaces an archived copy with a shorter transcript or an unavailable measurement, and failed parses retry on the next sync; [contracts](contracts.md#session-archive) owns the store layout, retention and failure rules, and parser versions. Retained sessions are re-parsed on every sync until the cause clears; `dot agent doctor` reports how many the last complete sync retained (`sync_retained`) without failing, since truncated sources and the shorter copy of a session duplicated across source files are retained by design; otherwise, a persistent count on unchanged sources usually means a parser no longer recognizes the provider's usage format. Doctor reports `last_sync=stale` and asks for a sync when another parser wrote that state. A `--since` pass without `--session`, `--project` or `--dry-run` records `.sync-window.json` instead of the complete-pass state; when it is newer, `last_sync` shows its time and `sync_failures`/`sync_retained` the larger count of both passes, while `never` and `stale` still ask for a complete sync.

OpenCode reads `~/.local/share/opencode/opencode.db` (override with `agent.sources.opencode`); its transcript adapter excludes tool parts and synthetic text. Codex sync also scans the sibling `~/.codex/archived_sessions` so archived threads keep their final turns (`sessions/` wins on duplicates).

Prompt statistics exclude [subagent sidechains](contracts.md#session-archive) (reported as `sidechain_sessions`) and read validated latest transcripts but emit only counts and length summaries, never message text. A prompt means an archived user message, possibly including injected context, not necessarily one human-authored turn. Dates use conversation timestamps in UTC, reading one without an offset as UTC like usage accounting; bounded queries exclude unparseable timestamps. Excluded or partial sessions and bounded timestamp gaps report incomplete coverage with a nonzero exit while retaining the available statistics. They do not measure productivity or answer quality.

Usage queries read one measurement per session from the manifest, without decoding transcripts. Unknown costs remain unknown, and unlike measurement kinds remain separate.

`session list` and `show` select sessions by session ID; add `--agent` when two agents share one. Status is `current`, `partial`, `legacy`, or `invalid` (with `--status invalid`, transcripts are validated). `--project .` resolves the current directory. Session list date filters use ingestion timestamps, source-sync filters use source modification time, prompt statistics use conversation timestamps, and usage filters use request timestamps when reliable samples exist, otherwise whole sessions by measurement timestamp. Undated usage falls back to the latest valid transcript timestamp, then the newest source-file modification time; capture time is never used. Dates are interpreted in UTC; date-only `--since` begins at midnight and date-only `--until` includes the whole day. Explicit timestamps retain their exact boundary.

For quick token totals and coverage dates, use `dot agent stats --tokens-only`; add `--monthly` for calendar months or `--billing --agent codex` for configured subscription cycles. The [usage guide](../../agent-usage/SKILL.md) owns accounting, pricing completeness, and renewal settings.

## Cleanup and recovery

Use the Dot CLI for cache inspection and cleanup:

```bash
dot cache
dot cache docker
dot prune all --dry-run
dot prune all --yes                     # authorized cache cleanup across configured providers
dot prune docker --yes                  # authorized Docker builder-cache cleanup
```

`dot cache` inspects the configured `cache.providers` (Docker, Hugging Face, uv by default). `dot prune` displays help; `dot prune all` cleans `prune.providers` (dprint, Hugging Face, mise, npm, Trivy, uv by default); Docker builder cleanup requires explicit selection or inclusion in that configuration. The command confirms the selected providers once before any cleanup and needs `--yes` without a terminal. `--dry-run` displays commands, not reclaimable bytes, and executes no providers. `dot prune` preflights required tools and stops on the first command failure; earlier successful operations are not rolled back. `dot cache all` skips providers that are not installed and reports every provider before exiting 1 on any failure; an explicitly named provider must be installed. Each provider can be selected independently. Native tools retain caller directory, profile, environment, and output; inspecting several providers labels each report with its provider name. The cleanup confirmation prompt goes to stderr.

Installed tools, credentials, provider sessions, and Dot archives are outside the default cleanup aggregate. Login, setup, and cleanup run only when invoked; they are not installation hooks. `dot login` and `dot setup` display help without a provider. See [authentication](authentication.md) for login order, scope checks, `--force`, and project precedence.

`dot orphan` lists files an earlier `chezmoi apply` deployed that the source no longer manages, with whether each still holds chezmoi's last write; text output folds targets inside an orphaned directory into one line with their count, while `--json` lists every target. It never deletes. Follow the [orphans guide](orphans.md) to decide per path.

Dot keeps one copy per session, so the archive needs no compaction. Project prompts, proposals, and reports are retained documents; Dot does not delete these directories.

## Repository publication

Commit and PR authoring belong to their skills, which use staged Git changes, explicit repository/base selection, privacy checks, and reviewed publication artifacts. In fmind/dot, `mise run release` prepares, tags, and atomically pushes the next release, and CD publishes it; it requires explicit release authority. A local push is not hosted publication evidence.

## Fish completions

`dot completion` (hidden from `dot --help`; `mise run completions` runs it) refreshes native Fish completions and the Atuin (without its AI `?` binding) and Carapace initialization caches. `completions.tools` is unset by default, which selects every `completions.custom_commands` entry (`dot config show` lists them, including `dot` and `bf`), so adding an entry needs no second edit; set `tools` to narrow the selection or add tools that use the default generator. Each entry in `completions.custom_commands` selects a native generator (`binary` and `args`) or a mise package containing a bundled `<tool>.fish` script (`package`). These source types are mutually exclusive. Unlisted custom tools use `<tool> completion fish`. Tools without a working generator need another source: `agy` keeps a chezmoi-managed script in `dot_config/fish/completions/`, and acli (1.3.39 removed `acli completion`) completes through the Carapace spec `dot_config/carapace/specs/acli.yaml`, which bridges the still-supported `acli __complete`; run `dot completion` after applying it so the Carapace cache includes acli.

Run `dot completion --check` to exercise the same generators and syntax validation entirely in temporary directories before installing or releasing. Missing executables and inactive mise shims are skipped. A failed generator or invalid Fish syntax preserves the previous script and both modes exit 1 naming each failure; a plain `dot completion` still installs every script that succeeded, replaced atomically. Native completions take precedence over Carapace, whose `dot` completer otherwise targets Graphviz. Tools without native Fish generators rely on Fish or Carapace support where available. The command does not delete independently installed completion files.
