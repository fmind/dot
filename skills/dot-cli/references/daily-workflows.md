---
name: daily-workflows
description: "Run workstation doctor, repo status/pull, folder trust, session sync/stats, cache prune, and completions."
---

# Daily Workflows

Installed `--help` owns exact flags. Examples below are local reads or previews unless marked authorized.

## Health checks

```bash
dot doctor --json
dot doctor --headroom
dot agent doctor --agent agy
```

`dot doctor` checks tools, secret file modes (`key.txt`, signing keypair, `~/.private.fish`), disk headroom, installation, and chezmoi orphans (warning only); `--deep` probes provider auth, and `--headroom` prints one-line disk/memory headroom. `dot agent doctor` checks persona/skills links (noting missing `OPENCODE_DISABLE_CLAUDE_CODE_SKILLS=1` on OpenCode without failing), `last_sync` (`failed`/`retained`), and archive readability (`dot.diagnostics/v1`). In `fmind/dot`, `mise run doctor` chains `dot doctor`, `chezmoi doctor`, and `mise doctor`.

## Repositories

```bash
dot status . --needs-attention
dot status --fetch --json              # fetch-only ref refresh before counting
dot pull . --dry-run --json
dot pull .                              # authorized: fast-forward clean repo
```

Explicit paths bypass workspace discovery. `status` inspects cached refs unless `--fetch` runs `git fetch --prune` (no Git LFS); inspection failures set `complete: false` and exit `1`. `pull` skips dirty repos before fetching, fast-forwards only (never merging/rebasing), disables credential prompts, and exits nonzero on any fetch failure; `--push` requires remote-write authority and pushes only to the branch's own upstream (refusing separate `pushDefault`/`pushRemote` or local upstreams).

## Folder trust

```bash
dot trust --dry-run
dot trust                               # authorized: trust current repo
dot trust all ~/.local/share/chezmoi    # authorized: workspaces + dot checkout (run by chezmoi apply)
```

`dot trust [PATH...]` additively trusts repo roots (refusing `$HOME` and ancestors) across existing harness state dirs: Claude (`~/.claude.json` + `permissions.additionalDirectories`), agy (adding `trust.agy_projects` to Remote Control as `local-<slug>`), Copilot (inherits downward — keep untrusted clones outside `pull.directories`), and Pi (`~/.pi/agent/trust.json`, inherited downward). `all` trusts `pull.directories` and direct child repos on `github.com` under `trust.github_owners` (default `fmind`; explicit `dot trust PATH` trusts any repo). Mise trust stays separate (`mise trust` or unmanaged `~/.config/mise/conf.d/trust.toml`).

## Sessions and statistics

```bash
dot agent session sync --agent agy --project . --dry-run --json
dot agent stats --tokens-only --project . --by-model --by-project --json
dot agent session show SESSION_ID --content --tail 20
```

Sync parses changed sources (`--dry-run` skips writes; only unfiltered sync updates `last_sync`; retired `codex`/`grok` remain queryable only, and non-empty OpenCode `opencode.db` fails sync until supported; Pi archives post-fork entries on `/fork` or `/clone`). `dot agent stats` syncs first unless `--no-sync` is passed ([JSON selectors](contracts.md#json-selectors), [archive rules](contracts.md#session-archive), [agent-usage](agent-usage.md)). `--prompts-only` excludes [sidechains](contracts.md#session-archive) and Claude meta turns (`injected`) without exposing text. All `--since`/`--until` filters are UTC (`session list` = ingestion time, `sync` = source mtime, prompts = turn time, usage = request/session/transcript/mtime, never capture time).

## Cleanup and recovery

```bash
dot cache                               # read-only Docker, HF, and uv cache sizes
dot prune --dry-run                     # preview stale-entry cleanup (dprint, HF, mise, npm, Trivy, uv)
dot prune --aggressive --yes            # authorized: empty whole caches (HF keeps downloaded models)
```

`dot cache` skips uninstalled tools and stopped Docker under default `all`. Default `dot prune` removes stale entries without prompting (Docker builder cache runs only when named or configured); `--aggressive` empties caches with confirmation (`--yes` non-interactively) while keeping repos, installed tool versions, credentials, sessions, Docker images/containers/volumes, and HF models intact ([authentication](authentication.md), [orphans](orphans.md)).

## Fish completions

`mise run completions` (`dot completion`; `--check` uses temp dirs) refreshes Fish completions and the Atuin init cache, replacing regular `*.fish` files in `completions.path` while keeping symlinks ([dot-development](https://github.com/fmind/dot/blob/main/.agents/skills/dot-development/SKILL.md)).
