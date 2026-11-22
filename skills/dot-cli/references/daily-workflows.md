---
name: daily-workflows
description: "Run workstation doctor, repo privacy/status/pull, folder trust, and completions."
---

# Daily Workflows

Installed `--help` owns exact flags. Examples below are local reads or previews unless marked authorized.

## Health checks

```bash
dot doctor --json
dot doctor --headroom
```

`dot doctor` emits `dot.diagnostics/v1` across secret file modes (`~/.config/chezmoi/key.txt`, `~/.ssh/id_ed25519_signing`), Docker, disk headroom, core CLI tools, installation freshness, and agent harnesses (persona, skills, and reviewer wiring).

- `--fix`: repair local secret-file permissions (`0600`).
- `-q`/`--quiet`: show only `fail`/`warn` items and a verdict (`--json -q` filters `.checks[]`).
- `--deep`: also probe `auth.login` providers.
- `--headroom`: check disk and memory headroom in one line (cannot combine with `--fix` or `--deep`).

In `fmind/dot`, `mise run doctor` chains `dot doctor`, `chezmoi doctor`, and `mise doctor`.

## Repositories

```bash
dot status . --needs-attention
dot status --fetch --json              # fetch-only ref refresh before counting
dot privacy .                          # scan files and commits for private emails, SSH comments, or host tokens
dot privacy --staged -q                # scan staged Git index blobs and commits (for pre-commit hooks)
dot pull .                             # authorized: fast-forward clean repo
```

Explicit paths bypass workspace discovery. `status` inspects cached refs unless `--fetch` runs `git fetch --prune` (no Git LFS); inspection failures set `complete: false` and exit `1`. `privacy [PATH...]` scans working files (or staged index blobs with `--staged`) and Git commit emails against allowed public domains (`fmind.dev`, `fmind.ai`, `github.com`, RFC 2606) plus dynamic workstation/client tokens loaded from untracked `~/.config/dot*.yaml` and `~/.config/git/config.*` (`--json` emits `dot.privacy/v1`; `-q` suppresses clean targets). Keep `dot privacy` workstation-local; other repositories must not depend on `dot`. `pull` skips dirty repos and branches without an upstream, fast-forwards only (never merging or rebasing), disables credential prompts, and exits `1` on any fetch failure or diverged branch.

## Folder trust

```bash
dot trust                               # authorized: trust current repo
dot trust all ~/.local/share/chezmoi    # authorized: allowlisted workspace repos + dot checkout (run by chezmoi apply)
```

`dot trust [PATH...]` additively trusts repo roots (refusing `$HOME` and ancestors) in Antigravity (adding `trust.agy_projects` to Remote Control as `local-<slug>`). `all` trusts direct Git repos under `pull.directories` whose `github.com` origin matches `trust.github_owners` (default `fmind`; explicit `dot trust PATH` trusts any folder or repo). Mise trust stays separate (`mise trust` or unmanaged `~/.config/mise/conf.d/trust.toml`).

## Fish completions

`mise run completions` (`uv run --frozen --directory dot python -m dot_tasks.completions`; `--check` uses temp dirs) refreshes Fish completions, replacing regular `*.fish` files in `~/.config/fish/completions` while keeping symlinks ([dot-development](https://github.com/fmind/dot/blob/main/.agents/skills/dot-development/SKILL.md)).
