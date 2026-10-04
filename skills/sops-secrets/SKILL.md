---
name: sops-secrets
description: "Encrypt, rotate, and inject Git secrets with sops and age."
license: MIT
metadata:
  kind: task
  author: Médéric HURIER (Fmind)
  source: github.com/fmind/dot/tree/main/skills/sops-secrets
  created: "2026-08-07"
  updated: "2026-10-04"
---

# Secrets with sops and age

Encrypted secrets live in git next to their configuration. Use environment variables or FIFOs for runtime delivery; interactive editing can write temporary plaintext. [gitleaks](../code-security/references/gitleaks.md) scans for leaked credentials, and [cloud-run](../cloud-run/SKILL.md) owns runtime Secret Manager integration.

## Model

- **age** provides the key pair: one private key per machine or human, public recipients everywhere; prefer it for solo use. Choose cloud KMS when centrally managed access is required; adding a KMS recipient alongside age does not revoke the independent age decryption path.
- **sops** encrypts the values of YAML, JSON, and ENV files; keys stay readable, so diffs review cleanly and `git log` tells which secret changed, never what it is.
- **Naming**: encrypted files are committed as `*.enc.yaml`, `*.enc.json`, or `*.enc.env`; [sops.yaml](templates/sops.yaml) keys its rules off that suffix and plaintext siblings stay gitignored.
- **Policy as file**: `.sops.yaml` at the repo root ([sops.yaml](templates/sops.yaml)) declares which paths get encrypted and for which recipients, so no ad-hoc flags are needed.

## Keys

Before the first encryption on a machine, and for any recipient change, follow [key-lifecycle](references/key-lifecycle.md): preserve an existing `SOPS_AGE_KEY_FILE` or key, generate only when absent, distribute only public recipients, back up the private key outside Git, and rotate through `updatekeys` plus `rotate`.

## Commands

```bash
sops edit secrets.enc.yaml                          # create or edit: decrypts to $EDITOR, re-encrypts on save
sops encrypt --filename-override config.enc.yaml config.yaml > config.enc.yaml  # suffix selects the creation rule; protect the existing plaintext input
sops decrypt secrets.enc.yaml                       # decrypt to stdout for piping, never redirect to a file
sops exec-env secrets.enc.env 'mise run watch'      # inject as env vars, memory-only (preferred)
sops exec-file secrets.enc.json 'tool --config {}'  # Unix tools get a FIFO by default, not a tmpfs guarantee
```

- **Prefer `exec-env` and `exec-file`** for runtime delivery; keep values out of logs and inspect how child processes handle them. `--no-fifo` writes a regular temporary file.
- **Integrations**: read [integrations.md](references/integrations.md) before wiring CI decryption (age key versus `gcp_kms` through Workload Identity Federation), Flux, OpenTofu, or a runtime secret manager.

## Gotchas

- **Editor plaintext**: `sops edit` writes a temporary plaintext file for the editor. When disk plaintext is forbidden, use an explicitly configured memory-backed temporary directory and compatible editor settings, or avoid the editor workflow.
- **Existing plaintext and old recipients**: encryption does not erase the input, editor backups, shell history, or past commits. Removing a recipient and rotating the SOPS data key protects the new file, but cannot revoke copies or older Git revisions that recipient could decrypt. Rotate exposed application credentials at their provider within the authorized scope.
- **Key names still leak**: sops encrypts values, not keys, so `stripe_production_key:` in a public repo is information; name keys neutrally when the repo is public.
- **Never edit ciphertext by hand**: sops stores a MAC over the file and out-of-band edits fail decryption; go through `sops edit` or `sops set`.
- **Rule match is positional**: `sops edit` picks the first `creation_rules` entry whose `path_regex` matches the path relative to `.sops.yaml`, so run sops from the repo root, and run `updatekeys` after any recipient change.
- **gitleaks coexists**: the [lefthook](../github-actions/references/lefthook.md) pre-commit scans the working tree, catching a plaintext sibling of an `*.enc.*` file. Inspect the redacted rule and location for every finding, including `*.enc.*` files; the suffix does not prove that comments, keys, or excluded fields are encrypted. Confirm whether plaintext was exposed before rotating credentials per [gitleaks](../code-security/references/gitleaks.md).

## Task guides

<!-- guides:start -->

- [key-lifecycle](references/key-lifecycle.md): Resolve, generate, distribute, back up, and rotate age keys and sops recipients.

<!-- guides:end -->

## Documentation

- [sops](https://getsops.io/docs/) · [key management](https://getsops.io/docs/usage/key-management/) · [age](https://age-encryption.org)
- Releases: [sops](https://github.com/getsops/sops/releases) · [age](https://github.com/FiloSottile/age/releases)
- Companion skills: [gitleaks](../code-security/references/gitleaks.md), [lefthook](../github-actions/references/lefthook.md), [cloud-run](../cloud-run/SKILL.md) (runtime secrets), [infra-as-code](../infra-as-code/SKILL.md), [code-security](../code-security/references/code-review/GUIDE.md).
