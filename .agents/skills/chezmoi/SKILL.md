---
name: chezmoi
description: "Manage chezmoi source names, templates, secrets, diffs, and deployment in fmind/dot."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/.agents/skills/chezmoi
  created: "2026-07-12"
  updated: "2026-11-07"
---

# Chezmoi Source Standard

Edit the source per the project `AGENTS.md` house rule; a change made under `~/.config` or `~/.gemini` is overwritten on the next apply. [mise](../../../skills/mise/SKILL.md) tasks wrap the chezmoi commands.

## Naming

Choose the target type first, then its allowed attributes in the [source-state reference](https://www.chezmoi.io/reference/source-state-attributes/) order (`encrypted_` before `private_` before `dot_`; a wrong order yields a literally named file). Repository conventions: global skill links are `dot_agents/skills/symlink_<name>.tmpl` ([dot-skills](../dot-skills/SKILL.md)), modifiers use the modify-template marker (see Gotchas), and native login seeds use `create_encrypted_private_*`.

## Workflow

1. **Manage an existing file**: `chezmoi add <target>` infers the attributes; set a secret to `0600` before `chezmoi add --encrypt` so it imports as `encrypted_private_*.age`, and keep `[add] secrets = "error"` so plain `add` refuses unencrypted secrets.
1. **Preview**: `mise run diff` (`chezmoi diff --force --no-pager --exclude encrypted`; restrict with `mise run diff -- <target>`). Diffs exclude encrypted targets so plaintext secrets never reach transcripts; `chezmoi status` still lists their drift.
1. **Validate rendering**: `mise run check:chezmoi` uses temporary configuration and destination with a dry run excluding encrypted files. It checks the current platform; exercise changed Linux/macOS branches separately and report unexercised branches or encrypted targets.
1. **Check repeatability**: for Bash/profile modifier changes, add existing-target and second-pass cases under `dot/tests/`, using the isolated rendering approach in `test_shell_modifiers.py`. Their blocks go through `.chezmoitemplates/managed-block.tmpl`, which rewrites the block between its begin and end markers in place, so a body change needs no migration code. JSON/TOML modifier changes need the same cases in `test_harness_config.py`. Inspect affected `run_*` hooks: ordinary hooks run on each apply; once/onchange hooks can rerun when their content changes.
1. **Apply within scope**: `mise run apply` (`chezmoi apply --force`, so a diverged target never blocks scripts on a prompt; `--force` does not expand authorized targets or side effects). Themes (one fmind/theme commit) and fonts (release URLs) are checksum-pinned externals that refetch when their URL changes; a checksum mismatch fails apply instead of deploying changed content, and `mise run upgrade` advances the theme pin only while every copied block in the `COPIED` map of `dot/dot_tasks/theme_pin.py` matches. The Google Sans, Google Sans Code, and Nerd Fonts releases have no upgrade task: when a newer release exists, bump each URL and its checksum together.
1. **Pull target edits back**: `chezmoi re-add` folds manual changes to a managed file (such as the regenerated Neovim `lazy-lock.json`) into the source; the mise lock is regenerated with `mise run lock`, never re-added.
1. **Diagnose**: `mise run doctor` (`dot doctor`, `chezmoi doctor`, and `mise doctor`); `chezmoi managed` and `chezmoi unmanaged` list coverage; `dot orphan` lists former managed targets ([orphans](../../../skills/dot-cli/references/orphans.md)); the [installed-link recovery guide](../dot-skills/references/installed-links.md) covers retired skill links, and approved cleanup moves them to recoverable backups. Use command help and [dot-cli](../../../skills/dot-cli/SKILL.md) for cleanup flags.

## Gotchas

- **Keep the modify-template convention**: chezmoi supports `modify_*.tmpl` scripts. This repository instead uses `# chezmoi:modify-template` and `.chezmoi.stdin` for every modifier (shell blocks via `managed-block.tmpl`, JSON/TOML via `config-merge.tmpl`); preserve that convention unless intentionally changing the execution model.
- **Commit only encrypted `*.age` secrets**: keep plaintext out of the repository, previews, and logs (inspect secret targets by status/metadata, never a plaintext diff); rotate a leaked secret (see [code-security](../../../skills/code-security/references/code-review/GUIDE.md)). Native login seeds use `create_encrypted_private_*` so account switches survive apply; scoped keys stay under `~/.config/dot/secrets/`, never in global shell exports. Follow [secret setup](../../../README.md#secret-management) and [credential precedence](../../../skills/dot-cli/references/authentication.md).
- **Escape other tools' template delimiters**: emit another tool's `{{ ... }}` as ``{{`{{ .Destination }}`}}`` (backticks inside an action); `.chezmoi.toml.tmpl` needs this too. Debug a template with `chezmoi execute-template < file`.
- **`.chezmoiignore`** (templated doublestar patterns, not gitignore syntax) keeps repo-only files (`dot/`, `skills/`, `AGENTS.md`) out of apply and skips key-dependent files without the age key; chezmoi already skips dot-prefixed sources such as `.github/`. Ignore patterns match target paths, and a leading `!` excludes a match from ignoring and wins over every other pattern, whatever the order.
- **Retire targets with `.chezmoiremove`**: removing a source never deletes its target, so list retired targets (glob patterns) in `.chezmoiremove` and apply deletes them on every machine, recursively and without asking. The file is a template: emit a shared-directory target such as a skill link only while `lstat` and `readlink` prove it is still this checkout's link, so a same-named package another tool installed survives. Delete each entry, and the file once empty, when no machine can still hold the target.
- **`.chezmoi.toml.tmpl`** seeds `~/.config/chezmoi/chezmoi.toml` on `chezmoi init` (`promptStringOnce` per-host data), including `[add] secrets = "error"` and `[edit] apply = true` (apply after `chezmoi edit`, `--watch` on save).

## Documentation

- [chezmoi reference](https://www.chezmoi.io/reference/) · [source-state attributes](https://www.chezmoi.io/reference/source-state-attributes/)
- [templating](https://www.chezmoi.io/user-guide/templating/) · [age encryption](https://www.chezmoi.io/user-guide/encryption/age/)
- Releases: [chezmoi](https://github.com/twpayne/chezmoi/releases)
