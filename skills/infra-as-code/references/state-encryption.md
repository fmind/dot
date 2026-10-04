---
name: state-encryption
description: "Enable OpenTofu client-side state and plan encryption with GCP KMS, including plaintext state migration."
---

# OpenTofu State Encryption

OpenTofu's `encryption` block turns state and saved plans into ciphertext, so a leaked bucket no longer leaks secrets. [versions.tf](../templates/versions.tf) sketches it with a GCP KMS key provider. The KMS key must exist and every operator and CI identity must be able to use it before encryption is enforced.

## Workflow

1. **Back up first**: copy the current state and record the key configuration; an unreadable state cannot be recovered without the key.
1. **New state**: uncomment the `encryption` block with `enforced = true` for `state` and `plan`, then run `tofu init` and a reviewed plan.
1. **Existing plaintext state**: add `method "unencrypted" "migrate" {}` and, inside `state`, replace `enforced` with `fallback { method = method.unencrypted.migrate }`. Apply once (authorized), then remove the fallback and the unencrypted method and restore `enforced = true`.
1. **Verify**: read the stored state object and confirm it is ciphertext, then run a plan to prove every operator can still decrypt it.

## Gotchas

- **Labels are permanent**: never rename `key_provider` or `method` labels once data is encrypted; OpenTofu can no longer find the key that encrypted it.
- **OpenTofu only**: HashiCorp Terraform cannot read encrypted state; a repository that pins `terraform` cannot use this block.

## Documentation

- [State encryption](https://opentofu.org/docs/language/state/encryption/)
