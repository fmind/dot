---
name: chezmoi
description: "Manage chezmoi sources, templates, age secrets, diffs, and apply in fmind/dot."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/.agents/skills/chezmoi
  created: "2026-07-12"
  updated: "2026-11-14"
---

# Chezmoi Source Standard

Edit sources here per `AGENTS.md`; edits under `~/.config` or `~/.gemini` are overwritten on the next apply. [mise](../../../skills/mise/SKILL.md) tasks wrap chezmoi commands.

## Naming

Pick the target type first, then attributes in [source-state reference](https://www.chezmoi.io/reference/source-state-attributes/) order (`encrypted_` → `private_` → `dot_`; wrong order yields a literal filename). Repo conventions: global skill links use `dot_agents/skills/symlink_<name>.tmpl` ([dot-skills](../dot-skills/SKILL.md)), modifiers use `# chezmoi:modify-template`, and native login seeds use `create_encrypted_private_*`.

## Workflow

1. **Import an existing file**: `chezmoi add <target>` infers attributes; `chmod 0600` before `chezmoi add --encrypt` so secrets import as `encrypted_private_*.age`, and keep `[add] secrets = "error"` so plain `add` rejects unencrypted secrets.
1. **Preview**: `mise run diff` (`chezmoi diff --force --no-pager --exclude encrypted`; narrow with `mise run diff -- <target>`). Diffs exclude encrypted files to keep plaintext out of transcripts; `chezmoi status` still shows their drift.
1. **Validate rendering**: `mise run check:chezmoi` dry-runs against a temporary config and destination excluding encrypted files on the host OS. Exercise changed Linux/macOS branches separately and report unexercised branches or encrypted targets.
1. **Check repeatability & hooks**: verify existing-target/second-pass modifier behavior (`test_shell_modifiers.py`, `test_harness_config.py`) and `run_*`/`systemd/user` hooks per [lifecycle](references/lifecycle.md).
1. **Apply & fold target edits**: run `mise run apply` (`chezmoi apply --force`, syncing SHA-pinned theme/font externals per [lifecycle](references/lifecycle.md)); fold manual target edits such as `~/.config/nvim/lazy-lock.json` back via `chezmoi re-add --source "$(pwd -P)"` (never `mise.lock`, which `mise run lock` owns).
1. **Diagnose**: `mise run doctor`; `chezmoi managed` / `chezmoi unmanaged`; `dot orphan` ([orphans](../../../skills/dot-cli/references/orphans.md)); [installed-link recovery](../dot-skills/references/installed-links.md); [dot-cli](../../../skills/dot-cli/SKILL.md).

## Gotchas

- **Use `# chezmoi:modify-template`, not script modifiers**: modifiers read `.chezmoi.stdin` via `managed-block.tmpl` or `config-merge.tmpl` instead of `modify_*.tmpl` scripts.
- **Keep secrets encrypted (`*.age`)**: never expose plaintext in sources, diffs, or logs; `~/.config/dot/secrets/` holds scoped secrets ([secret setup](../../../README.md#secret-management), [code-security](../../../skills/code-security/references/code-review/GUIDE.md)).
- **Escape foreign `{{ ... }}` delimiters**: write ``{{`{{ .Destination }}`}}`` (including in `.chezmoi.toml.tmpl`); test with `chezmoi execute-template < file`.
- **`.chezmoiignore`** uses templated doublestar patterns on target paths (not gitignore): skips repo-only paths (`dot/`, `skills/`, `AGENTS.md`) and age-dependent targets when the key is absent (dot-prefixed sources like `.github/` are skipped automatically). Leading `!` negates ignoring and wins regardless of order.
- **Retire targets via `.chezmoiremove`**: deleting a source leaves its deployed target; list retired target globs in `.chezmoiremove` so apply deletes them recursively without prompting. Guard shared-directory entries (like skill links) with `lstat`/`readlink` checks to this checkout so third-party same-name packages survive; prune entries once retired everywhere.
- **`.chezmoi.toml.tmpl`** seeds `~/.config/chezmoi/chezmoi.toml` on `chezmoi init` (`promptStringOnce` host data, `[add] secrets = "error"`, `[edit] apply = true`).

## Documentation

- [chezmoi reference](https://www.chezmoi.io/reference/) · [source-state attributes](https://www.chezmoi.io/reference/source-state-attributes/) · [templating](https://www.chezmoi.io/user-guide/templating/) · [age encryption](https://www.chezmoi.io/user-guide/encryption/age/) · [releases](https://github.com/twpayne/chezmoi/releases)
