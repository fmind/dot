# Chezmoi Source Names

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
