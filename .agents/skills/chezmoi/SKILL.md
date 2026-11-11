---
name: chezmoi
description: "Manage chezmoi sources, templates, age secrets, diffs, and apply in fmind/dot."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/.agents/skills/chezmoi
  created: "2026-07-12"
  updated: "2026-11-10"
---

# Chezmoi Source Standard

Edit sources here per `AGENTS.md`; edits under `~/.config` or `~/.gemini` are overwritten on the next apply. [mise](../../../skills/mise/SKILL.md) tasks wrap chezmoi commands.

## Naming

Pick the target type first, then attributes in [source-state reference](https://www.chezmoi.io/reference/source-state-attributes/) order (`encrypted_` → `private_` → `dot_`; wrong order yields a literal filename). Repo conventions: global skill links use `dot_agents/skills/symlink_<name>.tmpl` ([dot-skills](../dot-skills/SKILL.md)), modifiers use `# chezmoi:modify-template`, and native login seeds use `create_encrypted_private_*`.

## Workflow

1. **Import an existing file**: `chezmoi add <target>` infers attributes; `chmod 0600` before `chezmoi add --encrypt` so secrets import as `encrypted_private_*.age`, and keep `[add] secrets = "error"` so plain `add` rejects unencrypted secrets.
1. **Preview**: `mise run diff` (`chezmoi diff --force --no-pager --exclude encrypted`; narrow with `mise run diff -- <target>`). Diffs exclude encrypted files to keep plaintext out of transcripts; `chezmoi status` still shows their drift.
1. **Validate rendering**: `mise run check:chezmoi` dry-runs against a temporary config and destination excluding encrypted files on the host OS. Exercise changed Linux/macOS branches separately and report unexercised branches or encrypted targets.
1. **Check repeatability**: add existing-target and second-pass tests under `dot/tests/` — Bash/profile modifiers (`managed-block.tmpl`, rewritten in place between markers) in `test_shell_modifiers.py`, JSON/TOML modifiers (`config-merge.tmpl`) in `test_harness_config.py`. Check affected `run_*` hooks: plain hooks run every apply; `once_`/`onchange_` rerun when content changes.
1. **Apply in scope**: `mise run apply` (`chezmoi apply --force` avoids interactive prompts on diverged targets without expanding scope). Themes (`fmind/theme` commit) and fonts (release URLs) are SHA-256-pinned externals; checksum mismatches fail apply. `mise run upgrade` advances the theme pin only when every `COPIED` block in `dot/dot_tasks/theme_pin.py` matches; font upgrades require bumping URL and checksum together.
1. **Fold target edits back**: `chezmoi re-add` imports manual edits to managed files (e.g., Neovim `lazy-lock.json`); regenerate `mise.lock` via `mise run lock`, never `re-add`.
1. **Diagnose**: `mise run doctor`; `chezmoi managed` / `chezmoi unmanaged` for coverage; `dot orphan` for former managed targets ([orphans](../../../skills/dot-cli/references/orphans.md)); [installed-link recovery](../dot-skills/references/installed-links.md) for retired skill links; [dot-cli](../../../skills/dot-cli/SKILL.md) for cleanup flags.

## Gotchas

- **Use `# chezmoi:modify-template`, not script modifiers**: modifiers read `.chezmoi.stdin` via `managed-block.tmpl` or `config-merge.tmpl` instead of `modify_*.tmpl` scripts.
- **Keep secrets encrypted (`*.age`)**: never expose plaintext in the repo, diffs, or logs (check status/metadata only); rotate leaked secrets per [code-security](../../../skills/code-security/references/code-review/GUIDE.md). Native seeds use `create_encrypted_private_*` so account switches survive apply; scoped keys live in `~/.config/dot/secrets/`, never shell exports ([secret setup](../../../README.md#secret-management), [credential precedence](../../../skills/dot-cli/references/authentication.md)).
- **Escape foreign `{{ ... }}` delimiters**: write ``{{`{{ .Destination }}`}}`` (including in `.chezmoi.toml.tmpl`); test with `chezmoi execute-template < file`.
- **`.chezmoiignore`** uses templated doublestar patterns on target paths (not gitignore): skips repo-only paths (`dot/`, `skills/`, `AGENTS.md`) and age-dependent targets when the key is absent (dot-prefixed sources like `.github/` are skipped automatically). Leading `!` negates ignoring and wins regardless of order.
- **Retire targets via `.chezmoiremove`**: deleting a source leaves its deployed target; list retired target globs in `.chezmoiremove` so apply deletes them recursively without prompting. Guard shared-directory entries (like skill links) with `lstat`/`readlink` checks to this checkout so third-party same-name packages survive; prune entries once retired everywhere.
- **`.chezmoi.toml.tmpl`** seeds `~/.config/chezmoi/chezmoi.toml` on `chezmoi init` (`promptStringOnce` host data, `[add] secrets = "error"`, `[edit] apply = true`).

## Documentation

- [chezmoi reference](https://www.chezmoi.io/reference/) · [source-state attributes](https://www.chezmoi.io/reference/source-state-attributes/) · [templating](https://www.chezmoi.io/user-guide/templating/) · [age encryption](https://www.chezmoi.io/user-guide/encryption/age/) · [releases](https://github.com/twpayne/chezmoi/releases)
