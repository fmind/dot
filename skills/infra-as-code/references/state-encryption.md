---
name: state-encryption
description: "Configure OpenTofu client-side state and plan encryption with GCP KMS and migrate plaintext state."
---

# OpenTofu State Encryption

Encrypt state and `.tfplan` files client-side with GCP KMS as sketched in [versions.tf](../templates/versions.tf). Provision the KMS key and verify IAM access for every operator and CI principal before enforcing encryption.

## Workflow

1. **Back up state and key config**: lost KMS access makes encrypted state permanently unreadable.
1. **Enable on fresh state**: uncomment `encryption` with `enforced = true` on `state` and `plan`, then run `tofu init` and a reviewed `plan`.
1. **Migrate existing plaintext state**: add `method "unencrypted" "migrate" {}`, temporarily swap `state` `enforced` for `fallback { method = method.unencrypted.migrate }`, run one authorized `apply`, then remove both fallback and `migrate` and restore `enforced = true`.
1. **Verify**: confirm the stored GCS object is ciphertext and `tofu plan` succeeds for operators and CI.

## Gotchas

- **Never rename `key_provider` or `method` labels** after encrypting data, or OpenTofu cannot locate the decryption key.
- **OpenTofu-only**: HashiCorp `terraform` cannot parse `encryption` blocks or encrypted state.

## Documentation

- [State encryption](https://opentofu.org/docs/language/state/encryption/)
