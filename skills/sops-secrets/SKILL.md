---
name: sops-secrets
description: "Manage encrypted secrets with sops and age, including Git storage and runtime delivery."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/sops-secrets
  created: "2026-08-07"
  updated: "2026-09-26"
---

# Secrets with sops and age

Encrypted secrets live in git next to their configuration. Use environment variables or FIFOs for runtime delivery; interactive editing can write temporary plaintext. [gitleaks](../security-review/references/gitleaks.md) scans for leaked credentials, and [cloud-run](../cloud-run/SKILL.md) owns runtime Secret Manager integration.

## Model

- **age** provides the key pair: one private key per machine or human, public recipients everywhere; prefer it for solo use. Choose cloud KMS when centrally managed access is required; adding a KMS recipient alongside age does not revoke the independent age decryption path.
- **sops** encrypts the values of YAML, JSON, and ENV files; keys stay readable, so diffs review cleanly and `git log` tells which secret changed, never what it is.
- **Naming**: encrypted files are committed as `*.enc.yaml`, `*.enc.json`, or `*.enc.env`; [sops.yaml](references/sops.yaml) keys its rules off that suffix and plaintext siblings stay gitignored.
- **Policy as file**: `.sops.yaml` at the repo root ([sops.yaml](references/sops.yaml)) declares which paths get encrypted and for which recipients, so no ad-hoc flags are needed.

## Keys

1. **Resolve the key file**: preserve an existing `SOPS_AGE_KEY_FILE` or key. Otherwise use `$XDG_CONFIG_HOME/sops/age/keys.txt` when configured, `~/.config/sops/age/keys.txt` on Linux, or `~/Library/Application Support/sops/age/keys.txt` on macOS. Set `SOPS_AGE_KEY_FILE` explicitly when choosing another location; see the [age key lookup implementation](https://github.com/getsops/sops/blob/main/age/keysource.go).
1. **Generate** only when the key file is absent: create its parent directory with mode `0700`, then run `age-keygen -o "<key-file>"`. It creates a private file and refuses to overwrite an existing one. Print only the public half with `age-keygen -y "<key-file>"`.
1. **Distribute** only the public key, as the `age:` recipient in each repo's `.sops.yaml`.
1. **Back up** the private key in a password manager; never commit it to any dotfiles repo.
1. **Rotate**: add the new recipient to `.sops.yaml`, review the recipient diff, and run `sops updatekeys --yes <file>` on every encrypted file. Verify decryption through the replacement key before retiring the old one. After removing the old recipient, run `sops updatekeys --yes <file>` followed by `sops rotate -i <file>` so its previously recoverable data key cannot decrypt future values. Complete this sequence before storing replacement application credentials; urgent provider-side revocation follows the authorized incident response and need not wait for file re-encryption.

## Commands

```bash
sops edit secrets.enc.yaml                          # create or edit: decrypts to $EDITOR, re-encrypts on save
sops encrypt --filename-override config.enc.yaml config.yaml > config.enc.yaml  # suffix selects the creation rule; protect the existing plaintext input
sops decrypt secrets.enc.yaml                       # decrypt to stdout for piping, never redirect to a file
sops exec-env secrets.enc.env 'mise run watch'      # inject as env vars, memory-only (preferred)
sops exec-file secrets.enc.json 'tool --config {}'  # Unix tools get a FIFO by default, not a tmpfs guarantee
```

- **Prefer `exec-env` and `exec-file`** for runtime delivery; keep values out of logs and inspect how child processes handle them. `--no-fifo` writes a regular temporary file.
- **CI**: store the private key as the single `SOPS_AGE_KEY` GitHub Actions secret; every other secret rides encrypted in the repo and jobs wrap commands in `sops exec-env`.
- **Integrations**: Flux, OpenTofu, and runtime-manager wiring lives in [integrations.md](references/integrations.md).

## Gotchas

- **Editor plaintext**: `sops edit` writes a temporary plaintext file for the editor. When disk plaintext is forbidden, use an explicitly configured memory-backed temporary directory and compatible editor settings, or avoid the editor workflow.
- **Existing plaintext and old recipients**: encryption does not erase the input, editor backups, shell history, or past commits. Removing a recipient and rotating the SOPS data key protects the new file, but cannot revoke copies or older Git revisions that recipient could decrypt. Rotate exposed application credentials at their provider within the authorized scope.

- **Key names still leak**: sops encrypts values, not keys, so `stripe_production_key:` in a public repo is information; name keys neutrally when the repo is public.
- **Never edit ciphertext by hand**: sops stores a MAC over the file and out-of-band edits fail decryption; go through `sops edit` or `sops set`.
- **Rule match is positional**: `sops edit` picks the first `creation_rules` entry whose `path_regex` matches the path relative to `.sops.yaml`, so run sops from the repo root, and run `updatekeys` after any recipient change.
- **gitleaks coexists**: inspect the redacted rule and location for every finding, including `*.enc.*` files; the suffix does not prove that comments, keys, or excluded fields are encrypted. Confirm whether plaintext was exposed before rotating credentials per [gitleaks](../security-review/references/gitleaks.md).
- **Staged hook**: the [lefthook](../github-actions/references/lefthook.md) pre-commit runs gitleaks on staged content, catching a staged plaintext sibling of an `*.enc.*` file.

## Documentation

- [sops](https://getsops.io/docs/) · [key management](https://getsops.io/docs/usage/key-management/) · [age](https://age-encryption.org)
- Releases: [sops](https://github.com/getsops/sops/releases) · [age](https://github.com/FiloSottile/age/releases)
- Companion skills: [gitleaks](../security-review/references/gitleaks.md), [lefthook](../github-actions/references/lefthook.md), [cloud-run](../cloud-run/SKILL.md) (runtime secrets), [infra-as-code](../infra-as-code/SKILL.md), [security-review](../security-review/references/code-review/GUIDE.md).
