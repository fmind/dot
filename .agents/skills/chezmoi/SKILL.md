---
name: chezmoi
description: "Manage chezmoi source names, templates, secrets, diffs, and deployment in fmind/dot."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/.agents/skills/chezmoi
  created: "2026-07-12"
  updated: "2026-10-06"
---

# Chezmoi Source Standard

The source tree (`~/.local/share/chezmoi`) is the only thing to edit; `chezmoi apply` renders it into `$HOME`, so a change made under `~/.config` or `~/.gemini` is overwritten on the next apply. File names encode target path, mode, encryption, and rendering; [mise](../../../skills/mise/SKILL.md) wraps the commands as tasks.

## Naming

Read [source names](references/source-names.md) when adding or renaming a managed target; attributes depend on the target type.

## Workflow

1. **Edit the source**, never the deployed copy; `chezmoi cd` opens a shell in the source root.
1. **Manage an existing file**: `chezmoi add <target>` infers the attributes; `--template` templatizes; set a secret to `0600` before `--encrypt` imports it as `encrypted_private_<name>.age` (with `dot_` before a leading-dot name):

   ```bash
   chmod 600 ~/.config/<tool>/secret
   chezmoi add --encrypt ~/.config/<tool>/secret   # import and encrypt into the source
   chezmoi edit ~/.config/<tool>/secret            # edit the plaintext, re-encrypt on save
   ```

1. **Preview**: `mise run diff` (`chezmoi diff --force --no-pager`; restrict to affected targets). Diffs exclude encrypted targets so plaintext secrets never reach transcripts; `chezmoi status` still lists their drift.
1. **Validate rendering**: `mise run check:chezmoi` uses temporary configuration and destination with a dry run excluding encrypted files. It checks the current platform; exercise changed Linux/macOS branches separately and report unexercised branches or encrypted targets.
1. **Check repeatability**: for Bash/profile modifier changes, add existing-target and second-pass cases under `dot/tests/`, using the isolated rendering approach in `test_shell_modifiers.py`. Their blocks go through `.chezmoitemplates/managed-block.tmpl`, which rewrites the block between its begin and end markers in place, so a body change needs no migration code. JSON/TOML modifier changes need the same cases in `test_harness_config.py`. Inspect affected `run_*` hooks: ordinary hooks run on each apply; once/onchange hooks can rerun when their content changes.
1. **Apply within scope**: `mise run apply` (`chezmoi apply --force`, so a diverged target never blocks scripts on a prompt; `--force` does not expand authorized targets or side effects). `mise run apply:externals` re-fetches the commit-pinned themes and fonts; a checksum mismatch fails apply instead of deploying changed content, and `mise run upgrade` advances the theme pin only while every copied block in the `COPIED` map of `dot/dot_tasks/theme_pin.py` matches.
1. **Pull target edits back**: `chezmoi re-add` folds manual changes to a managed file (a regenerated lockfile, for example) into the source.
1. **Diagnose**: `mise run doctor` (`chezmoi doctor` and `mise doctor`); `chezmoi managed` and `chezmoi unmanaged` list coverage; the [installed-link recovery guide](../dot-skills/references/installed-links.md) previews former managed targets; approved cleanup moves them to recoverable backups. Use command help and [dot-cli](../../../skills/dot-cli/SKILL.md) for cleanup flags.

## Gotchas

- **Attribute order is fixed**: `encrypted_` before `private_` before `dot_`; a wrong order yields a literally named file instead of the effect.
- **Keep the modify-template convention**: chezmoi supports `modify_*.tmpl` scripts. This repository instead uses `# chezmoi:modify-template` and `.chezmoi.stdin` for every modifier (shell blocks via `managed-block.tmpl`, JSON/TOML via `json-merge.tmpl`/`toml-merge.tmpl`); preserve that convention unless intentionally changing the execution model.
- **Escape other tools' template delimiters**: emit another tool's `{{ ... }}` as ``{{`{{ .Destination }}`}}`` (backticks inside an action); `.chezmoi.toml.tmpl` needs this too.
- **Templates fail closed**: one template error aborts the whole apply; debug with `chezmoi execute-template < file` or `chezmoi apply --dry-run` before committing.
- **Commit only encrypted `*.age` secrets**: keep plaintext out of the repository, previews, and logs (inspect secret targets by status/metadata, never a plaintext diff); rotate a leaked secret (see [code-security](../../../skills/code-security/references/code-review/GUIDE.md)). Native login seeds use `create_encrypted_private_*` so account switches survive apply; scoped keys stay under `~/.config/dot/secrets/`, never in global shell exports. Follow [secret setup](../../../README.md#secret-management) and [credential precedence](../../../skills/dot-cli/references/authentication.md).
- **`.chezmoiignore`** (templated doublestar patterns, not gitignore syntax) keeps repo-only files (`dot/`, `skills/`, `AGENTS.md`, CI) out of apply and skips key-dependent files without the age key.
- **Ignore patterns match target paths**: a leading `!` excludes a match from ignoring and takes priority over every other pattern, whatever the order.
- **`.chezmoi.toml.tmpl`** seeds `~/.config/chezmoi/chezmoi.toml` on `chezmoi init` (`promptStringOnce` per-host data); `[add] secrets = "error"` makes `chezmoi add` refuse unencrypted secrets, and `[edit] apply = true` applies after `chezmoi edit` (`--watch` on save).

## Documentation

- [chezmoi reference](https://www.chezmoi.io/reference/) · [source-state attributes](https://www.chezmoi.io/reference/source-state-attributes/)
- [templating](https://www.chezmoi.io/user-guide/templating/) · [age encryption](https://www.chezmoi.io/user-guide/encryption/age/)
- Releases: [chezmoi](https://github.com/twpayne/chezmoi/releases)
- Companion skills: [mise](../../../skills/mise/SKILL.md) (pins chezmoi, wraps apply, diff, doctor), [dprint](../../../skills/dprint/SKILL.md) (formats source configurations).
- Also: [code-security](../../../skills/code-security/references/code-review/GUIDE.md) (leak scanning around `*.age` files), [dot-cli](../../../skills/dot-cli/SKILL.md) (workstation and archive commands).
