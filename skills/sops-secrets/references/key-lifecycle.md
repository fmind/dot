---
name: key-lifecycle
description: "Resolve, generate, distribute, back up, and rotate age keys and sops recipients."
---

# Age Key Lifecycle

Create or change the keys behind encrypted files; the parent [skill](../SKILL.md) owns the model, daily commands, and gotchas.

## Workflow

1. **Resolve the key file**: preserve an existing `SOPS_AGE_KEY_FILE` or key. Otherwise use `$XDG_CONFIG_HOME/sops/age/keys.txt` when configured, `~/.config/sops/age/keys.txt` on Linux, or `~/Library/Application Support/sops/age/keys.txt` on macOS. Set `SOPS_AGE_KEY_FILE` explicitly when choosing another location; see the [age key lookup implementation](https://github.com/getsops/sops/blob/main/age/keysource.go).
1. **Generate** only when the key file is absent: create its parent directory with mode `0700`, then run `age-keygen -o "<key-file>"`. It creates a private file and refuses to overwrite an existing one. Print only the public half with `age-keygen -y "<key-file>"`.
1. **Distribute** only the public key, as the `age:` recipient in each repo's `.sops.yaml`.
1. **Back up** the private key in a password manager; never commit it to any dotfiles repo.
1. **Rotate**: add the new recipient to `.sops.yaml`, review the recipient diff, and run `sops updatekeys --yes <file>` on every encrypted file. Verify decryption through the replacement key before retiring the old one. After removing the old recipient, run `sops updatekeys --yes <file>` followed by `sops rotate -i <file>` so its previously recoverable data key cannot decrypt future values. Complete this sequence before storing replacement application credentials; urgent provider-side revocation follows the authorized incident response and need not wait for file re-encryption.
