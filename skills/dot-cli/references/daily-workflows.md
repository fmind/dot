---
name: daily-workflows
description: "Run workstation doctor, repo status/pull, folder trust, session stats, and completions."
---

# Daily Workflows

Installed `--help` owns exact flags. Examples below are local reads or previews unless marked authorized.

## Health checks

```bash
dot doctor --json
dot doctor --headroom
```

`dot doctor` checks secret file modes (`~/.config/chezmoi/key.txt` and `~/.ssh/id_ed25519_signing`; `--fix` repairs permissions), Docker, disk headroom, core CLI tools, installation freshness, and agent harnesses (persona/skill links plus live `agy`/`claude`/`pi` sync state and archive readability under `dot.diagnostics/v1`); `--deep` also probes configured `auth.login` providers, and `--headroom` prints one-line disk/memory headroom. In `fmind/dot`, `mise run doctor` chains `dot doctor`, `chezmoi doctor`, and `mise doctor`.

## Repositories

```bash
dot status . --needs-attention
dot status --fetch --json              # fetch-only ref refresh before counting
dot pull .                              # authorized: fast-forward clean repo
```

Explicit paths bypass workspace discovery. `status` inspects cached refs unless `--fetch` runs `git fetch --prune` (no Git LFS); inspection failures set `complete: false` and exit `1`. `pull` skips dirty repos and branches without an upstream, fast-forwards only (never merging or rebasing), disables credential prompts, and exits `1` on any fetch failure or diverged branch.

## Folder trust

```bash
dot trust                               # authorized: trust current repo
dot trust all ~/.local/share/chezmoi    # authorized: workspaces + dot checkout (run by chezmoi apply)
```

`dot trust [PATH...]` additively trusts repo roots (refusing `$HOME` and ancestors) across existing harness state dirs: Claude (`~/.claude.json` + `permissions.additionalDirectories`), agy (adding `trust.agy_projects` to Remote Control as `local-<slug>`), and Pi (`~/.pi/agent/trust.json`, inherited downward). `all` trusts `pull.directories` and direct child repos on `github.com` under `trust.github_owners` (default `fmind`; explicit `dot trust PATH` trusts any repo). Mise trust stays separate (`mise trust` or unmanaged `~/.config/mise/conf.d/trust.toml`).

## Sessions and statistics

```bash
dot stats --project . --by-model --by-project --json
```

`dot stats` incrementally captures changed live sources (`agy`, `claude`, `pi`) before querying unless `--no-sync` is passed; retired `codex`, `copilot`, `grok`, and `opencode` archives stay queryable via `stats` ([JSON selectors](contracts.md#json-selectors), [archive rules](contracts.md#session-archive), [agent-usage](agent-usage.md)). All `--since`/`--until` filters are UTC (usage timestamps, never capture time).

## Fish completions

`mise run completions` (`uv run --frozen --directory dot python -m dot_tasks.completions`; `--check` uses temp dirs) refreshes Fish completions and the Atuin init cache, replacing regular `*.fish` files in `~/.config/fish/completions` while keeping symlinks and Chezmoi-managed completions ([dot-development](https://github.com/fmind/dot/blob/main/.agents/skills/dot-development/SKILL.md)).
