---
name: chezmoi
description: "Manage chezmoi source names, templates, secrets, diffs, and deployment in fmind/dot."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/.agents/skills/chezmoi
  created: "2026-07-12"
  updated: "2026-10-05"
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

1. **Preview**: `mise run diff` (`chezmoi diff --force`; restrict to affected non-secret targets).
1. **Validate rendering**: `mise run check:chezmoi` uses temporary configuration and destination with a dry run excluding encrypted files. It checks the current platform; exercise changed Linux/macOS branches separately and report unexercised branches or encrypted targets.
1. **Check repeatability**: for Bash/profile modifier changes, add existing-target and second-pass cases under `dot/tests/`, using the isolated rendering approach in `test_shell_modifiers.py`. Their blocks go through `.chezmoitemplates/managed-block.tmpl`, which rewrites the block between its begin and end markers in place, so a body change needs no migration code. JSON/TOML modifier changes need the same cases in `test_harness_config.py`. Inspect affected `run_*` hooks: ordinary hooks run on each apply; once/onchange hooks can rerun when their content changes.
1. **Apply within scope**: `mise run apply` (`chezmoi apply --force`); `mise run apply:externals` (`chezmoi apply --force --refresh-externals`) forces re-fetching the commit-pinned themes and font archives; `mise run upgrade` advances the theme pin (`dot_tasks.theme_pin`) only while every copied theme block registered in its `COPIED` map matches the new revision, and a checksum mismatch fails apply instead of deploying changed content. `--force` is mandatory in scripts and hooks so a diverged target never blocks on a prompt, `--dry-run` previews without writing. Applying also executes eligible hooks; `--force` does not expand authorized targets or side effects.
1. **Pull target edits back**: `chezmoi re-add` folds manual changes to a managed file (a regenerated lockfile, for example) into the source.
1. **Diagnose**: `mise run doctor` (`chezmoi doctor` and `mise doctor`); `chezmoi managed` and `chezmoi unmanaged` list coverage; the [installed-link recovery guide](../dot-skills/references/installed-links.md) previews former managed targets; approved cleanup moves them to recoverable backups. Use command help and [dot-cli](../../../skills/dot-cli/SKILL.md) for cleanup flags.

## Gotchas

- **Attribute order is fixed**: `encrypted_` before `private_` before `dot_`; a wrong order yields a literally named file instead of the effect.
- **Keep the modify-template convention**: chezmoi supports `modify_*.tmpl` scripts. This repository instead uses `# chezmoi:modify-template` and `.chezmoi.stdin` for every modifier (shell blocks via `managed-block.tmpl`, JSON/TOML via `json-merge.tmpl`/`toml-merge.tmpl`); preserve that convention unless intentionally changing the execution model.
- **Escape other tools' template delimiters**: emit another tool's `{{ ... }}` as ``{{`{{ .Destination }}`}}`` (backticks inside an action); `.chezmoi.toml.tmpl` needs this too.
- **Templates fail closed**: one template error aborts the whole apply; debug with `chezmoi execute-template < file` or `chezmoi apply --dry-run` before committing.
- **Seed native logins create-only**: use `create_encrypted_private_*` for native login seeds so account switches survive apply; scoped keys remain managed under `~/.config/dot/secrets/`. Never restore global shell exports. Follow [secret setup](../../../README.md#secret-management) and [credential precedence](../../../skills/dot-cli/references/authentication.md); preview secret targets with status/metadata, never a plaintext diff.
- **Commit only encrypted `*.age` secrets**: chezmoi decrypts them into intended targets during an authorized apply. Keep plaintext out of previews, logs, and repository files; rotate a leaked secret (see [code-security](../../../skills/code-security/references/code-review/GUIDE.md)).
- **`.chezmoiignore`** (templated doublestar patterns, not gitignore syntax) keeps repo-only files (`dot/`, `skills/`, `AGENTS.md`, CI) out of apply and skips key-dependent files without the age key.
- **Ignore patterns match target paths**: a leading `!` excludes a match from ignoring and takes priority over every other pattern, whatever the order.
- **`.chezmoi.toml.tmpl`** seeds `~/.config/chezmoi/chezmoi.toml` on `chezmoi init`, prompting per-host data with `promptStringOnce . "key" "question" "default"`.
- **Config keys**: `encryption = "age"`, the `[age]` identity and recipient, `[add] secrets = "error"` so `chezmoi add` refuses unencrypted files that contain secrets, and `[edit] apply = true` so `chezmoi edit` applies after the editor exits (`--watch` applies on save).

## Documentation

- [chezmoi reference](https://www.chezmoi.io/reference/) · [source-state attributes](https://www.chezmoi.io/reference/source-state-attributes/)
- [templating](https://www.chezmoi.io/user-guide/templating/) · [age encryption](https://www.chezmoi.io/user-guide/encryption/age/)
- Releases: [chezmoi](https://github.com/twpayne/chezmoi/releases)
- Companion skills: [mise](../../../skills/mise/SKILL.md) (pins chezmoi, wraps apply, diff, doctor), [dprint](../../../skills/dprint/SKILL.md) (formats source configurations).
- Also: [code-security](../../../skills/code-security/references/code-review/GUIDE.md) (leak scanning around `*.age` files), [dot-cli](../../../skills/dot-cli/SKILL.md) (workstation and archive commands).
