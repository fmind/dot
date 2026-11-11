---
name: daily-workflows
description: "Run workstation doctor, repo status/pull, folder trust, session sync/stats, cache prune, and completions."
---

# Daily Workflows

Use `--help` for exact flags. Examples below are local reads or previews unless noted.

## Health checks

```bash
dot doctor --json
dot doctor --headroom
dot agent doctor --agent agy
```

`dot doctor` checks tools, secret permissions (`~/.config/chezmoi/key.txt`, `~/.ssh/id_ed25519_signing` + `.pub`, `~/.private.fish` when present), disk headroom, installation, and chezmoi orphans (warning only); `--deep` adds auth probes, and `--headroom` checks only disk/memory in one line (`--json` keeps the envelope; incompatible with `--fix` or `--deep`). `dot agent doctor` checks one harness's persona/skills links (noting missing `OPENCODE_DISABLE_CLAUDE_CODE_SKILLS=1` on OpenCode without failing), user notify hooks, Claude's disable switch, `last_sync` with failed/retained counts, and archive readability (`dot.diagnostics/v1`). Static checks do not prove project/policy overrides or desktop delivery (`agy` print-mode never notifies). In `fmind/dot`, `mise run doctor` chains `dot doctor`, `chezmoi doctor`, and `mise doctor` (not the repo gate); `check:scan` audits committed npm/pypi tool locks.

## Repositories

```bash
dot status . --needs-attention
dot status --fetch --json              # refresh remote refs (fetch only, never merge) before counting
dot pull . --dry-run --json
dot pull .                              # authorized local update: fetches and fast-forwards
```

Explicit paths bypass workspace discovery. `status` reports dirty state, upstream, ahead/behind counts, and merge/rebase/cherry-pick/revert markers from cached refs unless `--fetch` runs `git fetch --prune` (120s timeout; never merges; fetch failure marks the repo failed). `--needs-attention` hides clean repos. Inspection failures emit `complete: false` JSON and exit 1.

Neither command runs Git LFS (`git lfs pull` or `mise run install` hydrates pre-LFS clones). `pull` skips dirty repos before fetching, fetches once, fast-forwards only (diverged branches are reported, never merged or rebased), disables Git credential prompts so missing auth fails fast, and exits nonzero on any fetch failure (even without an upstream). `--push` requires remote-write authority, rechecks the worktree after fetch/FF, pushes the checked-out branch only to its own upstream, and fails on separate push remotes (`remote.pushDefault`, `branch.<name>.pushRemote`) or local upstreams. `--dry-run` lists targets and push mode without fetching. Cancellation stops worker process groups; per-repo filesystem errors keep other results in incomplete JSON.

## Folder trust

```bash
dot trust --dry-run
dot trust                               # authorized trust change for this repository
dot trust all                           # authorized trust change across configured workspaces
dot trust all ~/.local/share/chezmoi    # several targets in one call, as chezmoi apply runs it
```

`dot trust [PATH...]` pre-accepts trust for the repo containing `PATH` (default `.`), or `PATH` outside a repo, across installed harnesses with existing state directories: Claude (`~/.claude.json` plus `permissions.additionalDirectories` in `~/.claude/settings.json`), agy, Copilot, and Pi (`~/.pi/agent/trust.json`); `$HOME` and its ancestors are refused. `all` trusts `pull.directories` workspaces and direct child repos whose `origin` is on `github.com` under `trust.github_owners` (default `fmind`, case-insensitive; others report skipped, while explicit `dot trust PATH` trusts any repo). `chezmoi apply` runs `dot trust all ~/.local/share/chezmoi`. Entries are add/update-only. When agy's Remote Control registry exists, trusted repos matching `trust.agy_projects` (default `["~/.local/share/chezmoi"]` → `local-fmind-dot.json` named `fmind/dot`) are added to the browser picker as `local-<slug>`. Claude and agy key trust on repo roots; Pi inherits trust and `.pi/` extensions downward, so `dot` writes only repo roots for Pi; Copilot inherits trust recursively under trusted workspaces (avoid broad home-wide `pull.directories`). Mise trust stays separate (`mise trust <path>` or `[settings].trusted_config_paths` in unmanaged `~/.config/mise/conf.d/trust.toml`).

## Sessions and statistics

```bash
dot agent session sync --agent agy --project . --dry-run --json
dot agent session sync --agent agy --project . --json
dot agent stats --prompts-only --project . --since 2026-09-01 --json
dot agent stats --tokens-only --project . --by-model --by-project --json
dot agent session show SESSION_ID --content --tail 20   # bounded transcript read
```

Sync parses only sources whose size or mtime changed (`--since` on Copilot's DB compares DB mtime, selecting all or none); `--dry-run` parses without writing. Only an unfiltered sync updates `last_sync` (stale after a parser bump). Unreadable source directories and bad source paths fail; per-session failures log to stderr, increment `failed`, and exit 1 after finishing ([JSON contract](contracts.md#json-selectors)). `dot agent stats` syncs quietly first unless `--no-sync` is passed; unknown `--agent` values exit 2 before syncing. Retired `codex` and `grok` remain selectable for `list`, `show`, and `stats`, but sync rejects them.

See [contracts](contracts.md#session-archive) for store layout, statuses, and `sync_retained` (truncated or shorter duplicate sources stay retained by design; persistent counts on unchanged files signal an unrecognized usage format). Pi's `~/.pi/agent/sessions` (`agent.sources.pi`) archives only post-fork entries on `/fork` or `/clone` files. OpenCode's `~/.local/share/opencode/opencode.db` (`agent.sources.opencode`) has no parser yet: empty stores pass, while `session_v2` or 1.x sessions fail sync (earlier bundles remain queryable).

`--prompts-only` excludes [sidechains](contracts.md#session-archive) (`sidechain_sessions`) and Claude meta turns (`injected`), emitting counts and lengths without message text; partial sessions or unparsable timestamps exit 1 with available stats. Usage queries read only manifest and usage lines ([agent-usage](agent-usage.md)). `session list`/`show` filter by `current`, `partial`, `legacy`, or `invalid` (validating transcripts on `invalid`). All dates are UTC (date-only `--since` starts at `00:00Z`; `--until` includes the full day): `session list` uses ingestion time, `sync` uses source mtime, prompt stats use conversation timestamps, and usage uses request timestamps (falling back to session measurement, latest transcript timestamp, then newest source mtime — never capture time).

## Cleanup and recovery

```bash
dot cache                               # read-only: disk used by the Docker, Hugging Face, and uv caches
dot cache docker
dot prune --dry-run                     # preview the default cleanup
dot prune                               # stale entries across prune.providers; no prompt
dot prune --aggressive --dry-run
dot prune --aggressive --yes            # authorized: empty whole caches; they rebuild on next use
dot prune docker                        # Docker builder cache runs only when named or configured
```

`dot cache` prints native read-only reports for `cache.providers` (Docker, HF, uv), skipping uninstalled tools and stopped Docker under default `all` (explicitly named providers must exist) and exiting 1 if any probe fails.

`dot prune` cleans `prune.providers` (dprint, HF, mise, npm, Trivy, uv) or one named provider (missing tools fail up front; `--dry-run` prints commands, not bytes). Default prune removes stale entries without prompting: dangling Docker build cache, detached/incomplete HF downloads, mise cache files older than `cache_prune_age` and broken/temp tracked-config links, unreachable npm entries, Trivy scan results, and unused uv entries (dprint is a no-op). `--aggressive` empties whole caches (unused Docker build cache, dprint plugins, mise/npm/uv caches, Trivy DBs), prompts once on stderr (`--yes` non-interactively), and keeps HF on its default tier so models survive. `uv` waits 10s (`UV_LOCK_TIMEOUT`) for active `uv run` locks and fails instead of forcing; every provider runs before exiting 1 on failures.

Prune never touches repos, installed tool versions, credentials, sessions, Docker images/containers/volumes, Dot archives, or project docs; login, setup, and prune never run as hooks ([authentication](authentication.md)). `dot orphan` reports unmanaged chezmoi leftovers (folding orphaned directories in text, listing every path in `--json`) without deleting; see [orphans](orphans.md).

## Fish completions

`mise run completions` (hidden `dot completion`; `--check` runs in temp dirs) refreshes Fish completions and the Atuin init cache, keeping previous scripts and exiting 1 on generator failure. It deletes other regular `*.fish` files in `completions.path` (symlinks survive), so place custom completions elsewhere; [dot-development](https://github.com/fmind/dot/blob/main/.agents/skills/dot-development/SKILL.md) owns the generator list.
