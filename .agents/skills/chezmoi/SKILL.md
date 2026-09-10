---
name: chezmoi
description: "Manage the chezmoi source tree of this repository: source-name attributes, templates, age secrets, diff and apply. Use when editing anything dot deploys into $HOME."
license: MIT
metadata:
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/.agents/skills/chezmoi
  created: "2026-07-12"
  updated: "2026-09-09"
---

# Chezmoi Source Standard

The source tree (`~/.local/share/chezmoi`) is the only thing to edit; `chezmoi apply` renders it into `$HOME`, so a change made under `~/.config` or `~/.gemini` is overwritten on the next apply. File names encode target path, mode, encryption, and rendering; [mise](../../../skills/mise/SKILL.md) wraps the commands as tasks.

## Naming

Choose the target type first, then use its allowed attributes in order from the [source-state reference](https://www.chezmoi.io/reference/source-state-attributes/). Files, directories, symlinks, modification scripts, and run scripts accept different combinations; there is no single prefix formula for all targets.

| Attribute                                          | Effect on the target                                                                                                                                  |
| -------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| `dot_foo`                                          | `~/.foo`; never write a literal leading dot in a source path.                                                                                         |
| `private_` / `executable_` / `readonly_`           | remove group/world permissions / add executable permissions / remove write permissions.                                                               |
| `empty_`                                           | keep the file even when its content is empty; chezmoi removes empty targets by default.                                                               |
| `encrypted_` + `.age`                              | decrypted on apply with the age identity; the order is `encrypted_private_dot_foo.age`.                                                               |
| `<name>.tmpl`                                      | Go `text/template` plus sprig, rendered with chezmoi data (`.chezmoi.os`, `.chezmoi.arch`, `.chezmoi.homeDir`, `[data]` keys).                        |
| `symlink_<name>.tmpl`                              | a symlink whose rendered content is the link destination, e.g. `{{ .chezmoi.homeDir }}/.agents/skills`.                                               |
| `modify_<name>`                                    | a script that rewrites the existing target; with the `# chezmoi:modify-template` marker it renders as a template with the target on `.chezmoi.stdin`. |
| `create_` / `remove_`                              | write only when absent / remove a file, symlink, or empty directory.                                                                                  |
| `run_[once_\|onchange_][before_\|after_]<name>.sh` | hook run during apply: `once_` per unique content hash (bootstrap), `onchange_` whenever the body changes (derived state).                            |

## Workflow

1. **Edit the source**, never the deployed copy; `chezmoi cd` opens a shell in the source root.
1. **Manage an existing file**: `chezmoi add <target>` infers the attributes; `--template` templatizes, `--encrypt` imports a secret as `encrypted_private_dot_<name>.age`:

   ```bash
   chezmoi add --encrypt ~/.config/<tool>/secret   # import and encrypt into the source
   chezmoi edit ~/.config/<tool>/secret            # edit the plaintext, re-encrypt on save
   ```

1. **Preview**: `mise run diff` (`chezmoi diff`; add `--force` in automation to skip prompts).
1. **Validate rendering**: `mise run check:chezmoi` uses temporary configuration and destination with a dry run excluding encrypted files. It checks the current platform; exercise changed Linux/macOS branches separately and report unexercised branches or encrypted targets.
1. **Check repeatability**: for Bash/profile modifier changes, add existing-target and second-pass cases under `dot/tests/`, using the isolated rendering approach in `test_harness_config.py`. Inspect affected `run_once_*` and `run_onchange_*` hooks: changing their content can trigger installation or other commands.
1. **Apply within scope**: `mise run apply` (`chezmoi apply --force`); `--force` is mandatory in scripts and hooks so a diverged target never blocks on a prompt, `--dry-run` previews without writing. Applying also executes eligible hooks; `--force` does not expand authorized targets or side effects.
1. **Pull target edits back**: `chezmoi re-add` folds manual changes to a managed file (a regenerated lockfile, for example) into the source.
1. **Diagnose**: `mise run doctor` (`chezmoi doctor` and `mise doctor`); `chezmoi managed` and `chezmoi unmanaged` list coverage; the [installed-link recovery guide](../dot-skills/references/installed-links.md) previews former managed targets; approved cleanup moves them to recoverable backups. Use command help and [dot-cli](../../../skills/dot-cli/SKILL.md) for cleanup flags.

## Gotchas

- **Attribute order is fixed**: `encrypted_` before `private_` before `dot_`; a wrong order yields a literally named file instead of the effect.
- **Modification conventions**: chezmoi supports `modify_*.tmpl` scripts. This repository instead uses `# chezmoi:modify-template` and `.chezmoi.stdin` for its Bash/profile modifiers; preserve that convention unless intentionally changing the execution model.
- **Literal delimiters**: emit another tool's `{{ ... }}` as ``{{`{{ .Destination }}`}}`` (backticks inside an action); `.chezmoi.toml.tmpl` needs this too.
- **Templates fail closed**: one template error aborts the whole apply; debug with `chezmoi execute-template < file` or `chezmoi apply --dry-run` before committing.
- **Secrets**: keep only encrypted `*.age` sources in Git; chezmoi decrypts them into intended targets during an authorized apply. Keep plaintext out of previews, logs, and repository files; rotate a leaked secret (see [secure](../../../skills/secure/SKILL.md)).
- **`.chezmoiignore`** (templated, gitignore syntax) keeps repo-only files (`dot/`, `skills/`, `AGENTS.md`, CI) out of apply and skips key-dependent files without the age key.
- **Ignore patterns** match target paths; later patterns win and a leading `!` re-includes.
- **`.chezmoi.toml.tmpl`** seeds `~/.config/chezmoi/chezmoi.toml` on `chezmoi init`, prompting per-host data with `promptStringOnce . "key" "question" "default"`.
- **Config keys**: `encryption = "age"`, the `[age]` identity and recipient, and `[edit] apply = true` so `chezmoi edit` applies on save.

## Documentation

- [chezmoi reference](https://www.chezmoi.io/reference/) · [source-state attributes](https://www.chezmoi.io/reference/source-state-attributes/)
- [templating](https://www.chezmoi.io/user-guide/templating/) · [age encryption](https://www.chezmoi.io/user-guide/encryption/age/)
- Companion skills: [mise](../../../skills/mise/SKILL.md) (pins chezmoi, wraps apply, diff, doctor), [dprint](../../../skills/dprint/SKILL.md) (formats source configurations).
- Also: [secure](../../../skills/secure/SKILL.md) (leak scanning around `*.age` files), [dot-cli](../../../skills/dot-cli/SKILL.md) (workstation and archive commands).
