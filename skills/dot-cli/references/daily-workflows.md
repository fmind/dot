---
name: daily-workflows
description: "Diagnose workstation health; run repository status and pull, folder trust, session sync and statistics, cleanup, and Fish completions."
---

# Daily Workflows

Use command help for exact options. Examples below are local reads or previews unless identified otherwise.

## Health checks

```bash
dot doctor --json
dot doctor --headroom
dot agent doctor --agent agy
```

`dot doctor` checks local tools, secret permissions (`~/.config/chezmoi/key.txt`, `~/.ssh/id_ed25519_signing` with its `.pub` companion, and `~/.private.fish` when present), disk headroom, installation, and a chezmoi orphan count (a warning that never fails); `--deep` also probes authentication. `--headroom` checks only disk and memory headroom in one line (`--json` keeps the envelope) and cannot be combined with `--fix` or `--deep`. `dot agent doctor` checks one agent's discovery (its deployed persona and skills link resolve to the shared sources; for OpenCode, a non-failing note flags a caller environment without `OPENCODE_DISABLE_CLAUDE_CODE_SKILLS=1`), user-level notify hook events, command types, Claude's explicit disable switch, last sync with its failed and retained counts, and archive readability. This static check does not prove project/policy overrides or desktop delivery (agy print-mode runs never notify); use the harness's native hook inspection for effective session behavior. Diagnostics share the `dot.diagnostics/v1` envelope with scope, passed, and checks.

In the dotfiles repository, `mise run doctor` runs the installed `dot doctor`, then `chezmoi doctor` and `mise doctor`; it does not replace the repository gate. `check:scan` audits the committed npm and pipx tool locks that `--locked` installs follow.

## Repositories

```bash
dot status . --needs-attention
dot status --fetch --json              # refresh remote refs (fetch only, never merge) before counting
dot pull . --dry-run --json
dot pull .                              # authorized local update: fetches and fast-forwards
```

Explicit repository paths bypass configured workspace discovery. Status includes dirty state, upstream, ahead/behind counts, and merge/rebase/cherry-pick/revert markers. Counts use cached remote-tracking refs unless `--fetch` first runs `git fetch --prune` (never a merge) within pull's 120-second allowance; a fetch failure marks that repository failed. `--needs-attention` hides clean repositories and prints an all-clear line when none remains. Repository inspection failures produce `complete: false` JSON and a nonzero exit. Docker health belongs to `dot doctor`.

Pull fetches once and fast-forwards the fetched upstream without a second fetch; fetch failures always produce a nonzero exit, including on branches without an upstream; dirty repositories are always skipped before fetching. A branch both ahead of and behind its upstream is reported as diverged and left unchanged, never merged or rebased. Git runs with terminal and askpass credential prompts disabled, so a missing credential fails that repository instead of blocking its worker. `--push` also pushes clean repositories that are ahead and requires authority for those remote writes; it rechecks the worktree after fetch/merge before pushing. Dry-run reports selected targets and the push setting without fetching or predicting remote changes. Pull and status cancellation stop worker subprocess groups and block subsequent worker commands; filesystem failures in one repository preserve the other results in incomplete JSON reports.

## Folder trust

```bash
dot trust --dry-run
dot trust                               # authorized trust change for this repository
dot trust all                           # authorized trust change across configured workspaces
dot trust all ~/.local/share/chezmoi    # several targets in one call, as chezmoi apply runs it
```

`dot trust [PATH...]` pre-accepts folder trust for the repository containing each `PATH` (default `.`), or `PATH` itself outside a repository, in every installed harness: Claude (`~/.claude.json`), agy, and Copilot; it refuses the home directory and its ancestors. `all` covers each `pull.directories` workspace and the repositories directly inside it whose `origin` is a github.com repository of a `trust.github_owners` owner (default `fmind`; compared case-insensitively); other repositories are listed as skipped, and an explicit `dot trust PATH` still trusts any repository. `chezmoi apply` runs it once for `all` and the chezmoi source. Entries are added or updated to trusted, never removed; unrelated host settings are preserved, and harnesses without a state directory are skipped; when none has one, the run reports that nothing was trusted. Once agy has created its Remote Control registry, each trusted repository matching `trust.agy_projects` (default `["~/.local/share/chezmoi"]`, named `fmind/dot` under `local-fmind-dot.json`) that it does not list is added to the browser project picker using an alphabetical `local-<slug>` ID; unlisted repositories stay trusted and other picker entries are curated per machine. Claude and agy key trust on the repository root, so a new clone needs `dot trust` (or the next apply). Copilot trusts every descendant of a trusted workspace: the owner allowlist filters individual repository entries, not that inherited trust. Mise trust is separate and machine-local: use `mise trust /path/to/mise.toml`, or set `[settings].trusted_config_paths` in unmanaged `~/.config/mise/conf.d/trust.toml` for selected directory trees. `dot trust` does not configure mise.

## Sessions and statistics

```bash
dot agent session sync --agent agy --project . --dry-run --json
dot agent session sync --agent agy --project . --json
dot agent stats --prompts-only --project . --since 2026-09-01 --json
dot agent stats --tokens-only --project . --by-model --by-project --json
dot agent session show SESSION_ID --content --tail 20   # bounded transcript read
```

Sync is incremental: it parses only new or changed sources, skipping one whose size and modification time match the archived copy. For the Copilot and OpenCode databases, `--since` compares the database's modification time, so it selects all or none of their sessions. Dry-run parses changed candidates but writes nothing. Only an unfiltered pass (no `--session`, `--project`, `--since`, or `--dry-run`) records the `last_sync` that `dot agent doctor` reports; after a parser bump, doctor reports `last_sync=stale` and asks for one. Unreadable source directories fail the scan instead of being silently skipped. A failed session or source scan writes one stderr line, increments `failed`, and sync continues, exiting 1 at the end; a misconfigured source path still fails fast. `--json` emits [`dot.agent.session.sync/v2`](contracts.md#json-selectors); stderr prints one summary per agent and each retained session, and `--verbose` also lists every ingested session (a parser bump recaptures thousands). `dot agent stats` (including `--sessions`) runs the same sync quietly first: failures appear on stderr and the report still prints. Pass `--no-sync` to report the archive as stored; an unknown `--agent` fails before any sync, and `--agent` lists the valid names in `--help`. Codex and Grok are retired: `--agent codex` or `grok` still selects their archived sessions for `list`, `show`, and `stats`, while sync rejects them.

[Contracts](contracts.md#session-archive) owns the store layout, retention and failure rules, and parser versions. Retained sessions are re-parsed on every sync until the cause clears; `dot agent doctor` reports how many the last complete sync retained (`sync_retained`) without failing, since truncated sources and the shorter copy of a session duplicated across source files are retained by design; otherwise, a persistent count on unchanged sources usually means a parser no longer recognizes the provider's usage format.

OpenCode reads `~/.local/share/opencode/opencode.db` (override with `agent.sources.opencode`); its transcript adapter excludes tool parts and synthetic text.

Prompt statistics exclude [subagent sidechains](contracts.md#session-archive) (reported as `sidechain_sessions`) and read validated latest transcripts but emit only counts and length summaries, never message text. A prompt means an archived user message, possibly including injected context, not necessarily one human-authored turn. Dates use conversation timestamps in UTC, reading one without an offset as UTC like usage accounting; bounded queries exclude unparseable timestamps. Excluded or partial sessions and bounded timestamp gaps report incomplete coverage with a nonzero exit while retaining the available statistics. They do not measure productivity or answer quality.

Usage queries read one measurement per session from its usage line, without decoding transcripts; `--since` and `--until` skip sessions whose recorded usage span lies outside the window. Unknown costs remain unknown, and unlike measurement kinds remain separate.

`session list` and `show` select sessions by session ID; add `--agent` when two agents share one. Status is `current`, `partial`, `legacy`, or `invalid` (with `--status invalid`, transcripts are validated). `--project .` resolves the current directory. Session list date filters use ingestion timestamps, source-sync filters use source modification time, prompt statistics use conversation timestamps, and usage filters use request timestamps when reliable samples exist, otherwise whole sessions by measurement timestamp. Undated usage falls back to the latest valid transcript timestamp, then the newest source-file modification time; capture time is never used. Dates are interpreted in UTC; date-only `--since` begins at midnight and date-only `--until` includes the whole day. Explicit timestamps retain their exact boundary.

For quick token totals and coverage dates, use `dot agent stats --tokens-only`; add `--monthly` for UTC calendar months. The [usage guide](../../agent-usage/SKILL.md) owns accounting and pricing completeness.

## Cleanup and recovery

Use the Dot CLI for cache inspection and cleanup:

```bash
dot cache                               # read-only: disk used by the Docker, Hugging Face, and uv caches
dot cache docker
dot prune --dry-run                     # preview the default cleanup
dot prune                               # stale entries across prune.providers; no prompt
dot prune --aggressive --dry-run
dot prune --aggressive --yes            # authorized: empty whole caches; they rebuild on next use
dot prune docker                        # Docker builder cache runs only when named or configured
```

`dot cache` is read-only: it prints the native report of each `cache.providers` entry (Docker, Hugging Face, uv by default), skips providers that are not installed, and exits 1 after reporting when one fails; an explicitly named provider must be installed. Several reports are labelled with their provider name.

`dot prune` cleans `prune.providers` (dprint, Hugging Face, mise, npm, Trivy, uv by default) or one named provider. The default tier removes only stale entries and runs without a prompt: dangling Docker build cache, detached Hugging Face revisions and incomplete downloads, mise metadata, download caches, and broken or temporary tracked-config links, unreachable npm entries, Trivy scan results, and unused uv entries; dprint has no default step. `--aggressive` empties whole caches (all unused Docker build cache, dprint plugins, the npm cache, Trivy databases, the uv cache), asks once on stderr naming those caches, and needs `--yes` without a terminal; Hugging Face and mise keep their default step and need no confirmation, because anything deeper deletes models or installed versions. Every provider runs even after another fails, and the command then exits 1 naming the failures. uv waits at most 10 seconds (`UV_LOCK_TIMEOUT`) for a running `uv run` process to release its cache, then fails rather than forcing. Missing tools fail before any cleanup. `--dry-run` prints commands, not reclaimable bytes.

Prune never touches repositories, installed tool versions, credentials, provider sessions, Docker images, containers, volumes, or Dot archives. Login, setup, and cleanup run only when invoked; they are not installation hooks. Bare `dot login` reconciles the configured providers; bare `dot setup` displays help. See [authentication](authentication.md) for login order, scope checks, `--force`, and project precedence.

`dot orphan` lists files an earlier `chezmoi apply` deployed that the source no longer manages, with whether each still holds chezmoi's last write; text output folds targets inside an orphaned directory into one line with their count, while `--json` lists every target. It never deletes. Follow the [orphans guide](orphans.md) to decide per path.

Dot keeps one copy per session, so the archive needs no compaction. Project prompts, proposals, and reports are retained documents; Dot does not delete these directories.

## Fish completions

`dot completion` (hidden from `dot --help`; `mise run completions` runs it) refreshes native Fish completions and the Atuin initialization cache (without its AI `?` binding). The tool list is `COMPLETION_SOURCES` in `dot/src/fmind_dot/config.py`; only the output directory (`completions.path`) is configurable. Each entry selects a native generator (`binary` and `args`) or a mise package containing a bundled `<tool>.fish` script (`package`); entries with neither use `<tool> completion fish`. Tools without a working generator need another source: `agy` keeps a chezmoi-managed script in `dot_config/fish/completions/`; acli (1.3.39 removed `acli completion`) has none since Carapace was dropped.

Run `dot completion --check` to exercise the same generators and syntax validation entirely in temporary directories before installing or releasing. Missing executables and inactive mise shims are skipped. A failed generator or invalid Fish syntax preserves the previous script and both modes exit 1 naming each failure; a plain `dot completion` still installs every script that succeeded, replaced atomically. Tools without native Fish generators rely on Fish's own completions where available. The command deletes other regular `*.fish` files in `completions.path` (symlinks survive), so keep hand-installed completions in another Fish completion directory.
